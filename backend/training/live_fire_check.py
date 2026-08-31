# -*- coding: utf-8 -*-
"""
LIVE FIRE CHECK:
1. Fetch today's real fire events directly from NASA FIRMS
2. Hit the local backend /fires endpoint
3. Compare: what FIRMS reports vs what your backend shows
4. Pinpoint the exact failure point
"""
import os, sys, csv, io, json, requests
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

FIRMS_KEY = os.getenv("FIRMS_API_KEY") or "public"
BACKEND_URL = "http://localhost:8000"

SEP = "=" * 65

# ── STEP 1: CHECK BACKEND IS ALIVE ──────────────────────────────
print(f"\n{SEP}")
print("  STEP 1: IS YOUR BACKEND RUNNING?")
print(SEP)
try:
    r = requests.get(f"{BACKEND_URL}/", timeout=5)
    print(f"  Backend status: HTTP {r.status_code}")
    print(f"  Response: {r.json()}")
    backend_alive = True
except Exception as e:
    print(f"  BACKEND DOWN: {e}")
    backend_alive = False

# ── STEP 2: WHAT DOES /fires RETURN RIGHT NOW? ──────────────────
print(f"\n{SEP}")
print("  STEP 2: WHAT DOES YOUR BACKEND /fires RETURN TODAY?")
print(SEP)
if backend_alive:
    try:
        r = requests.get(f"{BACKEND_URL}/fires", timeout=10)
        print(f"  HTTP Status: {r.status_code}")
        fires = r.json()
        if isinstance(fires, list):
            print(f"  Total events in /fires: {len(fires)}")
            if fires:
                print(f"\n  Events stored:")
                for i, f in enumerate(fires, 1):
                    ts = f.get("timestamp", f.get("created_at", "?"))
                    print(f"  {i}. Lat={f.get('lat')} Lon={f.get('lon')} "
                          f"Sev={f.get('severity')} CNN={f.get('cnn_probability','?')} "
                          f"Time={ts}")
            else:
                print("  >>> RESULT: 0 fire events in your database.")
        elif isinstance(fires, dict):
            items = fires.get("fires", fires.get("data", fires.get("events", [])))
            print(f"  Total events: {len(items)}")
            for i, f in enumerate(items, 1):
                print(f"  {i}. {f}")
        else:
            print(f"  Raw: {fires}")
    except Exception as e:
        print(f"  /fires endpoint failed: {e}")

# ── STEP 3: WHAT DOES NASA FIRMS ACTUALLY SEE TODAY? ─────────────
print(f"\n{SEP}")
print("  STEP 3: NASA FIRMS REAL DATA RIGHT NOW (TODAY ONLY)")
print(SEP)

sources = ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "MODIS_C6_1_NRT"]
bbox = "-180,-90,180,90"
raw = []
used_source = ""

for src in sources:
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_KEY}/{src}/{bbox}/1"
    print(f"\n  Trying {src}...")
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "SatSen-Diagnostic/1.0"})
        print(f"  HTTP {r.status_code}  |  Response size: {len(r.text)} bytes")
        if r.status_code == 200 and "html" not in r.text.lower() and len(r.text) > 100:
            reader = csv.DictReader(io.StringIO(r.text))
            data = list(reader)
            if data:
                print(f"  SUCCESS: {len(data)} fire hotspots detected globally today")
                raw = data
                used_source = src
                break
            else:
                print(f"  Empty response from {src}")
        else:
            print(f"  Bad response from {src}")
    except Exception as e:
        print(f"  Error: {e}")

if not raw:
    print("\n  FIRMS returned 0 data from all sources.")
    print("  This is a NASA API issue, not a bug in your code.")
    sys.exit()

# ── STEP 4: NORMALIZE + FILTER EXACTLY AS YOUR PIPELINE DOES ────
print(f"\n{SEP}")
print(f"  STEP 4: YOUR PIPELINE FILTER RESULTS (using {used_source})")
print(SEP)

def normalize_conf(v):
    if v == 'h': return 90
    if v == 'n': return 60
    if v == 'l': return 20
    try: return int(v)
    except: return 50

today_str = datetime.now().strftime("%Y-%m-%d")
today_events = [r for r in raw if r.get("acq_date","") == today_str]
all_events   = raw

print(f"\n  Total hotspots from FIRMS (any date):    {len(all_events)}")
print(f"  Hotspots with acq_date == {today_str}:  {len(today_events)}")

# Normalize confidence
for row in all_events:
    row["confidence"] = normalize_conf(row.get("confidence","50"))

# Sort by FRP descending
all_events.sort(key=lambda x: float(x.get("frp") or x.get("brightness",0)), reverse=True)

# Apply pipeline filters
top50         = all_events[:50]
zero_coords   = [f for f in top50 if float(f.get("latitude",0))==0 or float(f.get("longitude",0))==0]
valid_coords  = [f for f in top50 if float(f.get("latitude",0))!=0 and float(f.get("longitude",0))!=0]
low_conf_drop = [f for f in valid_coords if int(f.get("confidence",50)) < 30]
after_conf    = [f for f in valid_coords if int(f.get("confidence",50)) >= 30]
low_frp_drop  = [f for f in after_conf if float(f.get("frp",0) or 0) < 5]
passed_filter = [f for f in after_conf if float(f.get("frp",0) or 0) >= 5]

print(f"\n  Pipeline simulation:")
print(f"  A. Top-50 by FRP selected:              {len(top50)}")
print(f"  B. Dropped (zero coords):               {len(zero_coords)}")
print(f"  C. Dropped (confidence < 30):           {len(low_conf_drop)}")
print(f"  D. Dropped (FRP < 5):                   {len(low_frp_drop)}")
print(f"  E. >>> PASSED ALL FILTERS:              {len(passed_filter)}")

print(f"\n  {'#':<4} {'Lat':>9} {'Lon':>9} {'FRP':>8} {'Conf':>6} {'Sev':<8} {'Date':<12}")
print(f"  {'-'*60}")
for i, f in enumerate(passed_filter[:15], 1):
    frp  = float(f.get("frp",0))
    conf = int(f.get("confidence",50))
    sev  = "HIGH" if frp>50 else ("MEDIUM" if frp>20 else "LOW")
    print(f"  {i:<4} {f.get('latitude','?'):>9} {f.get('longitude','?'):>9} {frp:>8.1f} {conf:>6} {sev:<8} {f.get('acq_date','?'):<12}")

# ── STEP 5: CNN GATE TEST on #1 event ───────────────────────────
print(f"\n{SEP}")
print("  STEP 5: CNN GATE - LIVE TEST ON TOP FIRE EVENT")
print(SEP)
if passed_filter:
    top = passed_filter[0]
    lat = float(top.get("latitude",0))
    lon = float(top.get("longitude",0))
    print(f"\n  Testing CNN on top event: ({lat}, {lon})")
    print(f"  FRP={top.get('frp')}  Conf={top.get('confidence')}")
    if backend_alive:
        try:
            r = requests.get(f"{BACKEND_URL}/lookup?lat={lat}&lon={lon}", timeout=10)
            print(f"  /lookup response: HTTP {r.status_code}")
            print(f"  {r.json()}")
        except:
            pass
    # Check if GIBS tile is reachable
    import math
    from datetime import timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    zoom = 9
    n = 2**zoom
    tx = int((lon+180)/360*n)
    lat_rad = math.radians(lat)
    ty = int((1 - math.log(math.tan(lat_rad)+1/math.cos(lat_rad))/math.pi)/2*n)
    gibs_url = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/{yesterday}/GoogleMapsCompatible_Level9/{zoom}/{ty}/{tx}.jpg"
    print(f"\n  Testing GIBS tile reachability for ({lat}, {lon})...")
    print(f"  URL: {gibs_url}")
    try:
        gr = requests.get(gibs_url, timeout=8, headers={"User-Agent":"SatSen-Test/1.0"})
        print(f"  GIBS tile HTTP status: {gr.status_code}")
        print(f"  Response size: {len(gr.content)} bytes")
        if len(gr.content) < 500:
            print(f"  >>> WARNING: Tile is {len(gr.content)} bytes - likely blank/empty tile (not a real image)")
        else:
            print(f"  >>> GIBS tile OK - real image data received")
    except Exception as e:
        print(f"  GIBS tile ERROR: {e}")

# ── STEP 6: FINAL VERDICT ───────────────────────────────────────
print(f"\n{SEP}")
print("  FINAL VERDICT")
print(SEP)
if not backend_alive:
    print("\n  ISSUE: Backend is NOT running at localhost:8000")
    print("  FIX:   uvicorn app:app --host 0.0.0.0 --port 8000")
elif len(passed_filter) == 0:
    print("\n  ISSUE: FIRMS has no data matching your severity thresholds today.")
    print("  FIRMS returned events but all are filtered out by FRP < 5 or conf < 30.")
else:
    print(f"\n  NASA FIRMS has {len(passed_filter)} qualifying fire events today.")
    print(f"  Your backend shows {len(fires) if backend_alive else '?'} events in /fires.")
    if backend_alive and isinstance(fires, list) and len(fires) == 0:
        print("\n  ROOT CAUSE: The 0 events in DB means fire_pipeline() was never triggered")
        print("  or the scheduler has not run yet since the last restart.")
        print("\n  IMMEDIATE FIX: Hit this endpoint to force the pipeline now:")
        print(f"  GET {BACKEND_URL}/refresh-fires")
        print(f"  GET {BACKEND_URL}/run-pipeline  (check which route exists)")
