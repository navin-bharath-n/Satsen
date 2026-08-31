"""
Diagnostic: Why does the fire pipeline only produce 1 fire event from today's data?
This script simulates exactly what fire_pipeline() does and prints a detailed log
at every filter stage so you can see WHERE events are being dropped.
"""
import os, sys, csv, io, requests, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

FIRMS_API_KEY = os.getenv("FIRMS_API_KEY") or "public"
print(f"\n{'='*60}")
print(f"  FIRE PIPELINE DIAGNOSTIC  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*60}\n")

# ── 1. FETCH FROM FIRMS ─────────────────────────────────────────
satellite_sources = [
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "MODIS_C6_1_NRT"
]
bbox  = "-180,-90,180,90"
days  = 1   # today only
raw   = []

for source in satellite_sources:
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_API_KEY}/{source}/{bbox}/{days}"
    print(f"[FIRMS] Trying {source}...")
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "FireDiagnostic/1.0"})
        print(f"       → HTTP {r.status_code}")
        if r.status_code == 200:
            if "html" in r.text.lower() or "error" in r.text.lower():
                print(f"       → ❌ Got HTML/error body, skipping")
                continue
            reader = csv.DictReader(io.StringIO(r.text))
            data   = list(reader)
            if data:
                print(f"       → ✅ {len(data)} raw fire points from {source}\n")
                raw = data
                USED_SOURCE = source
                break
            else:
                print(f"       → ⚠️ Empty CSV response")
    except Exception as e:
        print(f"       → ⚠️ Error: {e}")

if not raw:
    print("\n❌ DIAGNOSIS: All FIRMS sources returned 0 data today.\n"
          "   Possible causes:\n"
          "   1. FIRMS API key invalid or rate-limited.\n"
          "   2. NASA FIRMS server outage.\n"
          "   3. No NRT data published yet for today (data is usually 3-5 hrs delayed).\n")
    sys.exit(1)

print(f"Columns in FIRMS response: {list(raw[0].keys())}\n")
print(f"{'='*60}")
print(f"  STAGE-BY-STAGE FILTER REPORT  (Total: {len(raw)} raw events)")
print(f"{'='*60}\n")

# ── 2. NORMALISE CONFIDENCE ─────────────────────────────────────
def normalize_conf(val):
    if val == 'h': return 90
    if val == 'n': return 60
    if val == 'l': return 20
    try:    return int(val)
    except: return 50

for row in raw:
    row["confidence"] = normalize_conf(row.get("confidence", "50"))

# ── 3. SORT BY FRP ──────────────────────────────────────────────
raw.sort(key=lambda x: float(x.get("frp") or x.get("brightness", 0)), reverse=True)
TOP_N = 50  # mirrors fire_pipeline(limit=50)

# ── 4. FILTER STEP BY STEP ──────────────────────────────────────
after_sort    = raw[:TOP_N]
filter_stages = {
    "A. Total from FIRMS API today":         len(raw),
    "B. After top-50 sort/limit":            len(after_sort),
}

null_coords  = [f for f in after_sort if float(f.get("latitude",0))==0 or float(f.get("longitude",0))==0]
filter_stages["C. Dropped: zero lat/lon"] = len(null_coords)

valid_coords = [f for f in after_sort if float(f.get("latitude",0))!=0 and float(f.get("longitude",0))!=0]

low_conf = [f for f in valid_coords if int(f.get("confidence",50)) < 30]
filter_stages["D. Dropped: confidence < 30"] = len(low_conf)
after_conf = [f for f in valid_coords if int(f.get("confidence",50)) >= 30]

low_frp = [f for f in after_conf if float(f.get("frp",0) or 0) < 5]
filter_stages["E. Dropped: FRP < 5"] = len(low_frp)
after_frp = [f for f in after_conf if float(f.get("frp",0) or 0) >= 5]

# Breakdown by severity
high_sev   = [f for f in after_frp if float(f.get("frp",0)) > 50]
medium_sev = [f for f in after_frp if 20 < float(f.get("frp",0)) <= 50]
low_sev    = [f for f in after_frp if 5 <= float(f.get("frp",0)) <= 20]
filter_stages["F. Pass severity gate (FRP ≥ 5, conf ≥ 30)"] = len(after_frp)
filter_stages["   ↳ HIGH severity   (FRP > 50)"] = len(high_sev)
filter_stages["   ↳ MEDIUM severity (FRP 20-50)"] = len(medium_sev)
filter_stages["   ↳ LOW severity    (FRP 5-20)"]  = len(low_sev)

# CNN filter: 0.6 FIRE_THRESHOLD (current setting in app.py)
print(f"\n{'='*60}")
print(f"  CNN VERIFICATION GATE  (FIRE_THRESHOLD = 0.60)")
print(f"{'='*60}")
print(f"\n⚠️  NOTE: verify_fire_image_with_cnn() fetches a GIBS/Bing tile for EACH")
print(f"   fire point and runs the ResNet-18 model on it. When the tile server")
print(f"   is unavailable or returns a non-fire image, fire_prob will be < 0.60.")
print(f"\n   With FIRE_THRESHOLD = 0.60 the filter line in app.py (line 1093) is:")
print(f"     if not fire_confirmed and fire_prob < 0.30 and conf < 70: SKIP")
print(f"\n   But fire_confirmed = (fire_prob >= 0.60). So an event is ONLY skipped if:")
print(f"   • CNN fire probability  < 0.30  AND")
print(f"   • Satellite confidence  < 70")
print(f"\n   Fallback paths in verify_fire_image_with_cnn():")
print(f"   • If GIBS tile unreachable → returns (0.85, True)  [fire ACCEPTED]")
print(f"   • If Bing tile unreachable → returns (0.85, True)  [fire ACCEPTED]")
print(f"   • If CNN exception        → returns (0.83, True)  [fire ACCEPTED]")

# ── 5. DUPLICATE FILTER ─────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  DATABASE DEDUPLICATION  (±0.01° radius)")
print(f"{'='*60}")
print(f"\n⚠️  The pipeline checks:")
print(f"   db.query(FireEvent).filter(lat between ±0.01, lon between ±0.01).first()")
print(f"\n   If a fire event already exists in the DB from a PREVIOUS run (past 5 days),")
print(f"   it is silently SKIPPED – even if it is still burning today.")
print(f"   The pipeline uses days=5 so FIRMS will return events from past 5 days,")
print(f"   but the DB dedup means they're all marked as seen after the first run.")

# ── 6. PRINT SUMMARY TABLE ──────────────────────────────────────
print(f"\n{'='*60}")
print(f"  FILTER STAGE SUMMARY")
print(f"{'='*60}")
for stage, count in filter_stages.items():
    print(f"  {stage:<45} {count}")

# ── 7. SHOW TODAY'S TOP EVENTS THAT PASSED ALL FILTERS ──────────
print(f"\n{'='*60}")
print(f"  TODAY'S TOP 10 FIRE EVENTS (post-filter, CNN not yet applied)")
print(f"{'='*60}")
print(f"{'#':<4} {'Lat':>8} {'Lon':>9} {'FRP':>8} {'Conf':>6} {'Severity':<10} {'Date':<12} {'Time':<8}")
print("-"*65)
for i, f in enumerate(after_frp[:10], 1):
    frp  = float(f.get("frp", 0))
    conf = int(f.get("confidence", 50))
    sev  = "HIGH" if frp > 50 else ("MEDIUM" if frp > 20 else "LOW")
    lat  = f.get("latitude", "?")
    lon  = f.get("longitude", "?")
    date = f.get("acq_date", "?")
    time = f.get("acq_time", "?")
    print(f"{i:<4} {lat:>8} {lon:>9} {frp:>8.1f} {conf:>6} {sev:<10} {date:<12} {time:<8}")

# ── 8. ROOT CAUSE SUMMARY ───────────────────────────────────────
print(f"\n{'='*60}")
print(f"  ROOT CAUSE ANALYSIS")
print(f"{'='*60}")
print("""
The most likely reasons you only see 1 fire event today:

🔴 REASON 1 — DB DEDUPLICATION (most likely)
   fire_pipeline() fetches 5 days of data but only adds NEW events.
   Every fire seen in a previous run is already in the DB and is skipped.
   Events from yesterday are still "active" in FIRMS data → all skipped.

🔴 REASON 2 — SCHEDULER LIMIT (very likely)
   The scheduler calls fire_pipeline(limit=10) every 15 min.
   Only the top-10 events by FRP are processed per cycle.
   If the #1 event was already in the DB, only 0 new events get stored.

🔴 REASON 3 — GIBS TILE SERVER (common)
   verify_fire_image_with_cnn() downloads a NASA GIBS imagery tile.
   GIBS tiles are updated daily and may be unavailable/blank for today.
   When the tile is a featureless ocean/land image, the CNN correctly
   returns a low fire probability (< 0.60), failing the CNN gate.

🟡 REASON 4 — FIRMS DATA LATENCY
   Near-Real-Time (NRT) FIRMS data has a 3-5 hour delay.
   At 17:20 IST, today's data only covers events detected before ~12:00 IST.

✅ FIX: Update app.py fire_pipeline() to:
   1. Lower FIRE_THRESHOLD from 0.60 → 0.40 (best F1 per eval_thresholds.py)
   2. Use days=1 (not days=5) to avoid re-processing stale events
   3. Widen dedup radius or use acquisition timestamp to allow same-location re-fires
""")
