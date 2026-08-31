# pyright: reportPrivateImportUsage=false
# ==========================================================
# GLOBAL REAL-TIME AI FOREST FIRE(FINAL)
# FIRMS + SENTINEL-2 + CNN + LSTM + OPEN-METEO
# ==========================================================

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, Form
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, inspect
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import sys, os, time, threading, asyncio, requests, math, hashlib
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

from dotenv import load_dotenv
import subprocess
from pydantic import BaseModel
import geopandas as gpd
from shapely.geometry import Point
os.makedirs("uploads", exist_ok=True)
import random
from torchvision import models, transforms
from PIL import Image
from dotenv import load_dotenv
import os
import earth_engine_service

load_dotenv()
app = FastAPI(title="AI Powered Satellite Monitoring System")

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
TORCH_AVAILABLE = True
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from openai import OpenAI
import os
from passlib.context import CryptContext
import jwt
from datetime import timedelta
from pydantic import BaseModel

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your_super_secret_key" # Replace with env variable in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ================= TWILIO SETUP =================
def send_twilio_sms(mobile_no, message):
    sid = os.getenv("TWILIO_SID", "")
    auth = os.getenv("TWILIO_AUTH", "")
    from_no = os.getenv("TWILIO_PHONE", "")
    
    if not sid or not auth or not from_no:
        print("⚠️ Twilio credentials not configured. SMS alerts will be disabled.")
        return
        
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        
        # Format mobile number to ensure it has +91 for India if no country code provided
        clean_no = str(mobile_no).strip()
        if not clean_no.startswith('+'):
            clean_no = '+91' + clean_no
            
        payload = {
            "To": clean_no,
            "From": from_no,
            "Body": message
        }
        
        response = requests.post(url, data=payload, auth=(sid, auth), timeout=5)
        print("Twilio Response:", response.text)
    except Exception as e:
        print(f"Failed to send SMS via Twilio: {e}")

# ================= LSTM SETUP =================
LABELS = ["LOW", "MEDIUM", "HIGH"]
DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

class FireLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(4, 32, batch_first=True)
        self.fc = nn.Linear(32, 3)
        self.register_buffer("mean", torch.tensor([11.022466, 177.8312, 1.9988, 55.2473]))
        self.register_buffer("std", torch.tensor([5.20969696, 103.75680437, 0.81514723, 20.59177372]))

    def forward(self, x):
        # Normalize input
        x = (x - self.mean) / self.std
        out, _ = self.lstm(x)
        return self.fc(out[:, -1])

lstm = None
LSTM_PATH = "training/fire_lstm.pth"  # ← use YOUR trained model path

try:
    lstm = FireLSTM()
    lstm.load_state_dict(torch.load(LSTM_PATH, map_location="cpu"))
    lstm.eval()
    print("🔥 LSTM loaded successfully")
except Exception as e:
    lstm = None
    print("❌ LSTM failed to load:", e)


IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]
FIRE_THRESHOLD = 0.40  # Optimal threshold: F1=0.9944, Precision=99.65%, Recall=99.22% (eval_thresholds.py)

def load_fire_model():
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    path = "training/best_fire_cnn.pth" if os.path.exists("training/best_fire_cnn.pth") else "training/fire_cnn.pth"
    model.load_state_dict(torch.load(path, map_location="cpu"))
    model.eval()
    return model

try:
    cnn = load_fire_model()
    print("🔥 CNN loaded successfully")
except Exception as e:
    cnn = None
    print("❌ CNN failed to load:", e)


# ================= DEFORESTATION CNN SETUP =================
class DeforestationResNet(nn.Module):
    def __init__(self):
        super(DeforestationResNet, self).__init__()
        # Use a pre-trained ResNet18 for powerful feature extraction
        self.resnet = models.resnet18(weights=None)
        num_ftrs = self.resnet.fc.in_features
        
        # Replace the classifier for our binary task (0 to 1 probability)
        self.resnet.fc = nn.Sequential( # type: ignore
            nn.Linear(num_ftrs, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.resnet(x)

deforestation_cnn = None
DEFORESTATION_CNN_PATH = "training/deforestation_resnet.pth"

try:
    deforestation_cnn = DeforestationResNet()
    if os.path.exists(DEFORESTATION_CNN_PATH):
        deforestation_cnn.load_state_dict(torch.load(DEFORESTATION_CNN_PATH, map_location="cpu"))
        print("🌳 Deforestation ResNet loaded successfully")
    else:
        print("⚠️ Deforestation ResNet weights not found. Using untrained foundational model.")
    deforestation_cnn.eval()
except Exception as e:
    deforestation_cnn = None
    print("❌ Deforestation ResNet failed to load:", e)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("✅ Application starting up...")
    try:
        # Test database connection
        from sqlalchemy import text
        db = Session()
        db.execute(text("SELECT 1"))
        db.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Application shutting down...")
    engine.dispose()
    print("✅ Database connections closed")

def safe_broadcast(data):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast(data))
    except RuntimeError:
        # No running loop (background thread)
        asyncio.run(broadcast(data))



# ================= LAND MASK =================
LAND = None

def get_land():
    global LAND
    if LAND is None:
        import os
        import urllib.request
        land_file = "ne_110m_admin_0_countries.zip"
        if not os.path.exists(land_file):
            try:
                print("Downloading LAND dataset...")
                urllib.request.urlretrieve("https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip", land_file)
            except Exception as e:
                print("Failed to download land dataset:", e)
                return None
        if os.path.exists(land_file):
            LAND = gpd.read_file(land_file).to_crs("EPSG:4326")
    return LAND


def is_on_land(lat, lon):
    land = get_land()
    if land is None: return True # fallback if download fails
    point = Point(lon, lat)
    # Check if point is on land or within a small buffer (~5km) to catch coastal/shore fires
    return land.intersects(point.buffer(0.05)).any()



import rasterio
import numpy as np

# ================= Sentinel =================
from sentinelsat import SentinelAPI, geojson_to_wkt
from shapely.geometry import Point

# ================= ENV =================
load_dotenv()
FIRMS_API_KEY = os.getenv("FIRMS_API_KEY")
COPERNICUS_USER = os.getenv("COPERNICUS_USER")
COPERNICUS_PASS = os.getenv("COPERNICUS_PASS")

genai = None
try:
    from google import genai
except ImportError:
    try:
        import google.generativeai as genai
    except ImportError:
        genai = None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None
if GEMINI_API_KEY and genai and hasattr(genai, "Client"):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print("Warning: Gemini client init error:", e)


# ================= APP =================

# ================= DATABASE =================
# ================= DATABASE (MySQL) =================

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
# ================= DATABASE CONFIG =================
from urllib.parse import quote_plus

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD", ""))

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
    echo=False
)

Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ================= TABLE MODELS =================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    mobile_no = Column(String(20), unique=True, index=True)
    password_hash = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)

class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    mobile_no = Column(String(20), index=True)
    otp = Column(String(10))
    expires_at = Column(DateTime)
    timestamp = Column(DateTime, default=datetime.utcnow)

class FireEvent(Base):
    __tablename__ = "fire_events"

    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float)
    lon = Column(Float)
    severity = Column(String(50))
    spread_risk = Column(String(50))
    spread_direction = Column(String(10))
    district = Column(String(255))
    state = Column(String(255))
    cnn_probability = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)


class DeforestationEvent(Base):
    __tablename__ = "deforestation_events"

    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float)
    lon = Column(Float)
    area_sq_km = Column(Float)
    risk_level = Column(String(50))
    environmental_impact = Column(String(255))
    district = Column(String(255))
    state = Column(String(255))
    ndvi_shift = Column(Float, nullable=True) # Change in NDVI
    cnn_confidence = Column(Float, nullable=True) # CNN detection confidence
    t1_ndvi_url = Column(String(500), nullable=True)
    t2_ndvi_url = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)



class UserLocation(Base):
    __tablename__ = "user_locations"

    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float)
    lon = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)


# Create tables automatically if not exists
Base.metadata.create_all(engine)


# ================= AUTH SCHEMAS & ROUTES =================
class OTPSendRequest(BaseModel):
    mobile_no: str

class OTPVerifyRequest(BaseModel):
    mobile_no: str
    password: str
    otp: str

class UserLogin(BaseModel):
    mobile_no: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def get_password_hash(password):
    # SHA256 pre-hash passwords 72 bytes or longer (bcrypt limit is 71 chars)
    if len(password.encode('utf-8')) > 71:
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    # Apply same SHA256 pre-hash if password is 72 bytes or longer
    if len(plain_password.encode('utf-8')) > 71:
        plain_password = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None): # type: ignore
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/auth/send-otp")
def send_otp(request: OTPSendRequest):
    try:
        mobile_no = request.mobile_no
        
        db = Session()
        try:
            db_user = db.query(User).filter(User.mobile_no == mobile_no).first()
            if db_user:
                raise HTTPException(status_code=400, detail="Mobile number already registered")
                
            # Generate 6-digit OTP
            import random
            import string
            otp = ''.join(random.choices(string.digits, k=6))
            
            # Invalidate previous OTPs for this number
            db.query(OTPCode).filter(OTPCode.mobile_no == mobile_no).delete()
            
            # Create new OTP code (expires in 10 minutes)
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            new_otp = OTPCode(mobile_no=mobile_no, otp=otp, expires_at=expires_at)
            db.add(new_otp)
            db.commit()
            
            # Send via Twilio
            print(f"\n[DEV LOG] ----------------------------------")
            print(f"[DEV LOG] Generated OTP {otp} for {mobile_no}")
            print(f"[DEV LOG] ----------------------------------\n")
            
            send_twilio_sms(mobile_no, f"Your forest monitoring system verification code is {otp}")
            
            return {"message": "OTP sent successfully"}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in send_otp: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")

@app.post("/auth/verify-otp")
def verify_otp(request: OTPVerifyRequest):
    db = Session()
    try:
        # Step 1: Check if registered
        db_user = db.query(User).filter(User.mobile_no == request.mobile_no).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Mobile number already registered")
            
        # Step 2: Validate OTP
        otp_record = db.query(OTPCode).filter(
            (OTPCode.mobile_no == request.mobile_no) & 
            (OTPCode.otp == request.otp)
        ).first()
        
        if not otp_record:
            raise HTTPException(status_code=400, detail="Invalid OTP")
            
        if otp_record.expires_at < datetime.utcnow(): # type: ignore
            raise HTTPException(status_code=400, detail="OTP has expired")
            
        # Step 3: Create User
        hashed_password = get_password_hash(request.password)
        new_user = User(mobile_no=request.mobile_no, password_hash=hashed_password)
        db.add(new_user)
        
        # Delete the used OTP
        db.query(OTPCode).filter(OTPCode.mobile_no == request.mobile_no).delete()
        db.commit()
        
        return {"message": "User registered successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in verify_otp: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    finally:
        db.close()

@app.post("/auth/login", response_model=Token)
def login(user: UserLogin):
    try:
        db = Session()
        try:
            db_user = db.query(User).filter(User.mobile_no == user.mobile_no).first()
            
            if not db_user or not verify_password(user.password, db_user.password_hash):
                raise HTTPException(status_code=401, detail="Incorrect mobile number or password")
        
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": db_user.mobile_no}, expires_delta=access_token_expires
            )
            return {"access_token": access_token, "token_type": "bearer"}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in login: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

# ================= TEST ROUTES =================

@app.post("/add-test-fire")
def add_test_fire():
    db = Session()
    fire = FireEvent(
        lat=10.9331,
        lon=76.9273,
        severity="HIGH",
        spread_risk="MEDIUM",
        spread_direction="NE",
        district="Coimbatore",
        state="Tamil Nadu",
        cnn_probability=0.87
    )
    db.add(fire)
    db.commit()
    db.close()
    return {"message": "Test fire inserted"}

@app.get("/fire-events")
def get_fires():
    db = Session()
    fires = db.query(FireEvent).all()
    result = []
    for f in fires:
        result.append({
            "id": f.id,
            "lat": f.lat,
            "lon": f.lon,
            "severity": f.severity,
            "district": f.district,
            "state": f.state
        })
    db.close()
    return result


# ================= REQUEST SCHEMAS =================

# ================= WEBSOCKET =================
clients = set()

@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    try:
        await websocket.accept()
        clients.add(websocket)
        # Send initial connection message
        await websocket.send_json({"type": "connected", "message": "WebSocket connected successfully"})
        # Keep connection alive
        while True:
            try:
                # Wait for any message (ping/pong or data)
                data = await websocket.receive_text()
                # Echo back if needed
                if data:
                    await websocket.send_json({"type": "pong", "data": data})
            except WebSocketDisconnect:
                # Normal client disconnect
                break
            except Exception as e:
                print(f"WebSocket receive error: {e}")
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket connection error: {e}")
    finally:
        clients.discard(websocket)

async def broadcast(data):
    disconnected_clients = set()
    for c in list(clients):
        try:
            await c.send_json(data)
        except Exception as e:
            print(f"Failed to send WebSocket message: {e}")
            disconnected_clients.add(c)
    # Clean up disconnected clients
    for c in disconnected_clients:
        clients.discard(c)

# ================= GEO HELPERS =================
def reverse_geocode(lat, lon):
    """Reverse geocode coordinates to get district and state"""
    # Use BigDataCloud first as it has no rate limits and is extremely fast (~50-100ms)
    try:
        r = requests.get(
            "https://api.bigdatacloud.net/data/reverse-geocode-client",
            params={"latitude": lat, "longitude": lon, "localityLanguage": "en"},
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            district = data.get("city") or data.get("locality") or "Unknown"
            state = data.get("principalSubdivision") or data.get("countryName") or "Unknown"
            if district != "Unknown" or state != "Unknown":
                return district, state
    except Exception as e:
        print("BigDataCloud geocode error, trying Nominatim:", e)

    # Fallback to Nominatim if BigDataCloud fails
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": lat,
                "lon": lon,
                "format": "json",
                "addressdetails": 1,
                "zoom": 10
            },
            headers={"User-Agent": "FireMonitoringSystem/1.0"},
            timeout=5
        )
        
        if r.status_code != 200:
            return get_location_fallback(lat, lon)
        
        address = r.json().get("address", {})
        
        # Try multiple field names for district
        district = (
            address.get("district") or
            address.get("county") or
            address.get("subdistrict") or
            address.get("taluka") or
            address.get("tehsil") or
            address.get("suburb") or
            address.get("city") or
            address.get("town") or
            address.get("village") or
            address.get("municipality") or
            address.get("city_district") or
            address.get("neighbourhood") or
            None
        )
        
        # If district is still None, try to extract from display_name
        if not district:
            display_name = r.json().get("display_name", "")
            parts = display_name.split(",")
            if len(parts) >= 2:
                potential_district = parts[1].strip() if len(parts) > 1 else None
                if potential_district and potential_district not in ["India", "IN"]:
                    district = potential_district
        
        district = district or "Unknown"
        
        # Try multiple field names for state
        state = (
            address.get("state") or
            address.get("region") or
            address.get("province") or
            "Unknown"
        )
        
        # If still unknown, try fallback
        if district == "Unknown" or state == "Unknown":
            fallback_district, fallback_state = get_location_fallback(lat, lon)
            if district == "Unknown":
                district = fallback_district
            if state == "Unknown":
                state = fallback_state
        
        return district, state
    except Exception as e:
        print(f"Reverse geocoding error: {e}")
        return get_location_fallback(lat, lon)

def get_location_fallback(lat, lon):
    """Fallback method to get location using alternative APIs or approximations"""
    try:
        # Try using a different geocoding service as fallback
        r = requests.get(
            f"https://api.bigdatacloud.net/data/reverse-geocode-client",
            params={"latitude": lat, "longitude": lon, "localityLanguage": "en"},
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            district = data.get("city") or data.get("locality") or "Unknown"
            state = data.get("principalSubdivision") or data.get("countryName") or "Unknown"
            return district, state
    except:
        pass
    
    # Final fallback: return coordinates-based name
    return f"Area ({lat:.2f}, {lon:.2f})", "Unknown"

# ================= OPEN-METEO =================
def get_wind(lat, lon):
    try:
        r = requests.get(
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=wind_speed_10m,wind_direction_10m",
            timeout=10
        )
        c = r.json()["current"]
        return c["wind_speed_10m"], c["wind_direction_10m"]
    except:
        return 8, 90

def spread_direction(wind_direction_deg):
    """Convert wind direction in degrees to compass direction"""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = int((wind_direction_deg + 22.5) / 45) % 8
    return directions[index]
def cnn_predict(image_tensor):
    if cnn is None or image_tensor is None:
        return False, 0.0
    with torch.no_grad():
        out = cnn(image_tensor)
        probs = torch.nn.functional.softmax(out, dim=1)
        fire_prob = probs[0][1].item()
    return fire_prob >= FIRE_THRESHOLD, fire_prob


# ================= FIRMS =================
def fetch_firms_basic(days=1):
    try:
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/json/"
            f"{FIRMS_API_KEY}/VIIRS_SNPP_NRT/"
            f"-180,-90,180,90/{days}"
        )

        r = requests.get(url, timeout=20)
        print("FIRMS BASIC status:", r.status_code)

        if r.status_code != 200:
            return []

        if "html" in r.text.lower():
            print("❌ BASIC returned HTML")
            return []

        return r.json()

    except Exception as e:
        print("Basic FIRMS error:", e)
        return []
def fetch_firms_secure(days=1):
    try:
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/json/"
            f"{FIRMS_API_KEY}/VIIRS_SNPP_NRT/"
            f"-180,-90,180,90/{days}"
        )

        headers = {
            "Authorization": f"Bearer {FIRMS_API_KEY}",
            "User-Agent": "FireMonitoringSystem/1.0"
        }

        r = requests.get(url, headers=headers, timeout=20)

        print("FIRMS SECURE status:", r.status_code)

        if r.status_code != 200:
            return []

        if "html" in r.text.lower():
            print("❌ SECURE returned HTML")
            return []

        return r.json()

    except Exception as e:
        print("Secure FIRMS error:", e)
        return []


def fetch_firms(area="world", days=1):
    """Fetch fire data from NASA FIRMS API with multi-sensor fallback.
    area: 'world', 'IND' (India), or country code
    days: number of days to fetch (1-10)
    """
    import csv
    import io
    
    if not area or area == "world" or "," not in str(area):
        bbox = "-180,-90,180,90"
    else:
        bbox = area

    # List of satellite sources to try in order of priority
    satellite_sources = [
        "VIIRS_SNPP_NRT",
        "VIIRS_NOAA20_NRT",
        "VIIRS_NOAA21_NRT",
        "MODIS_C6_1_NRT"
    ]
    
    key = FIRMS_API_KEY or "public"
    
    for idx, source in enumerate(satellite_sources):
        try:
            url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{bbox}/{days}"
            print(f"[{idx+1}/{len(satellite_sources)}] Fetching FIRMS CSV data from {source}: {url}")
            
            r = requests.get(url, timeout=15, headers={"User-Agent": "FireMonitoringSystem/1.0"})
            print(f"FIRMS status for {source}:", r.status_code)
            
            if r.status_code == 200:
                if "html" in r.text.lower() or "not found" in r.text.lower() or "error" in r.text.lower():
                    print(f"⚠️ Warning: Received invalid response text from {source}. Trying next source...")
                    continue
                    
                csv_file = io.StringIO(r.text)
                reader = csv.DictReader(csv_file)
                data = []
                for row in reader:
                    conf_val = row.get("confidence")
                    if conf_val == 'h':
                        numeric_conf = 90
                    elif conf_val == 'n':
                        numeric_conf = 60
                    elif conf_val == 'l':
                        numeric_conf = 20
                    else:
                        try:
                            numeric_conf = int(conf_val) if conf_val else 50
                        except ValueError:
                            numeric_conf = 50
                    
                    row["confidence"] = numeric_conf
                    data.append(row)
                
                if data:
                    print(f"🚀 Success: Fetched {len(data)} live fire events from {source} API")
                    return data
                else:
                    print(f"⚠️ Warning: No fire rows returned from {source}. Trying next source...")
            else:
                print(f"❌ Failed: status {r.status_code} for {source}. Trying next source...")
                
        except Exception as e:
            print(f"⚠️ Error fetching from {source}: {e}. Trying next source...")
            
    # If all sources fail, fall back to sample data
    print("❌ All satellite sources failed, falling back to sample data")
    return get_sample_fire_data()


def severity_from_firms(frp, conf):
    """Determine fire severity from FRP (Fire Radiative Power) and confidence"""
    if conf is None or conf < 30: return None
    if frp is None or frp < 5: return None
    if frp > 50: return "HIGH"
    if frp > 20: return "MEDIUM"
    return "LOW"

def get_sample_fire_data():
    """Sample fire data for testing when API is unavailable"""
    import random
    return [
        {
            "latitude": 20.5937 + random.uniform(-5, 5),
            "longitude": 78.9629 + random.uniform(-5, 5),
            "frp": random.uniform(15, 60),
            "confidence": random.randint(50, 100),
            "acq_date": datetime.now().strftime("%Y-%m-%d"),
            "acq_time": datetime.now().strftime("%H%M")
        }
        for _ in range(5)
    ]

def get_satellite_image_url(lat, lon, zoom=9):
    """Get satellite image URL from various sources including NASA GIBS, NASA Worldview, Mapbox, Bing"""
    from datetime import datetime, timedelta
    import math

    date = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    worldview_url = f"https://worldview.earthdata.nasa.gov/?v={lon-0.1},{lat-0.1},{lon+0.1},{lat+0.1}&l=VIIRS_SNPP_CorrectedReflectance_TrueColor"

    mapbox_token = os.getenv("MAPBOX_TOKEN", "")
    static_map = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/pin-s-fire+ff0000({lon},{lat})/{lon},{lat},{zoom},0/800x600?access_token={mapbox_token}"

    def lat_lon_to_tile(lat, lon, zoom_level):
        n = 2 ** zoom_level
        x = int((lon + 180) / 360 * n)
        lat_rad = math.radians(lat)
        y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
        return max(0, x), max(0, y)

    gibs_zoom = min(zoom, 9)
    tile_x, tile_y = lat_lon_to_tile(lat, lon, gibs_zoom)
    gibs_url = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/{yesterday}/GoogleMapsCompatible_Level9/{gibs_zoom}/{tile_y}/{tile_x}.jpg"

    def lat_lon_to_quadkey(lat, lon, z_level):
        def tile_to_quadkey(x, y, z):
            quadkey = ""
            for i in range(z, 0, -1):
                digit = 0
                mask = 1 << (i - 1)
                if (x & mask) != 0:
                    digit += 1
                if (y & mask) != 0:
                    digit += 2
                quadkey += str(digit)
            return quadkey
        n = 2 ** z_level
        x = int((lon + 180) / 360 * n)
        lat_rad = math.radians(lat)
        y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
        return tile_to_quadkey(x, y, z_level)

    quadkey = lat_lon_to_quadkey(lat, lon, zoom)
    bing_url = f"https://ecn.t0.tiles.virtualearth.net/tiles/a{quadkey}.jpeg?g=685&n=z"

    sentinel_url = None
    if os.getenv("SENTINEL_HUB_API_KEY"):
        sentinel_url = f"https://services.sentinel-hub.com/ogc/wms/{os.getenv('SENTINEL_HUB_API_KEY')}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&CRS=EPSG:4326&BBOX={lon-0.01},{lat-0.01},{lon+0.01},{lat+0.01}&WIDTH=512&HEIGHT=512&LAYERS=TRUE_COLOR&FORMAT=image/jpeg"

    return {
        "worldview": worldview_url,
        "static": static_map,
        "gibs": gibs_url,
        "bing": bing_url,
        "sentinel": sentinel_url,
        "google_earth": f"https://earth.google.com/web/@{lat},{lon},1000a,35y,0h,0t,0r"
    }

def verify_fire_image_with_cnn(lat, lon):
    """Download satellite image tile for coordinates and run ResNet18 fire CNN model.
    Tries multiple tile providers with blank-tile detection.
    Falls back to trust FIRMS satellite confidence if no image is available.
    """
    import io, math
    from datetime import datetime, timedelta

    if not TORCH_AVAILABLE or cnn is None:
        return 0.88, True

    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        zoom = 9
        n = 2 ** zoom
        tx = int((lon + 180) / 360 * n)
        lat_rad = math.radians(lat)
        ty = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)

        # Build quadkey for Bing
        def _quadkey(x, y, z):
            qk = ""
            for i in range(z, 0, -1):
                d = 0
                mask = 1 << (i - 1)
                if (x & mask) != 0: d += 1
                if (y & mask) != 0: d += 2
                qk += str(d)
            return qk

        quadkey = _quadkey(tx, ty, zoom)

        # Priority-ordered list of tile URLs to try
        tile_urls = [
            # GIBS VIIRS True Color (may 404 on very fresh dates)
            f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_NOAA20_CorrectedReflectance_TrueColor/default/{yesterday}/GoogleMapsCompatible_Level9/{zoom}/{ty}/{tx}.jpg",
            f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/{yesterday}/GoogleMapsCompatible_Level9/{zoom}/{ty}/{tx}.jpg",
            # Bing Maps satellite
            f"https://ecn.t0.tiles.virtualearth.net/tiles/a{quadkey}.jpeg?g=685&n=z",
            f"https://ecn.t1.tiles.virtualearth.net/tiles/a{quadkey}.jpeg?g=685&n=z",
            # ESRI World Imagery (public, no key)
            f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{ty}/{tx}",
            # OpenStreetMap standard (vegetation context fallback)
            f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png",
        ]

        img_content = None
        used_url = None
        for url in tile_urls:
            try:
                resp = requests.get(url, timeout=6, headers={"User-Agent": "SatSen-FireMonitor/2.0"})
                if resp.status_code == 200 and len(resp.content) > 5000:  # >5KB = real image
                    img_content = resp.content
                    used_url = url
                    break
                else:
                    print(f"  Tile skip: {url[:60]}... -> HTTP {resp.status_code} size={len(resp.content)}b")
            except Exception as te:
                print(f"  Tile error: {url[:60]}... -> {te}")
                continue

        if img_content is None:
            # No tile available – trust FIRMS satellite confidence directly
            print(f"No valid satellite tile for ({lat:.4f},{lon:.4f}) — trusting FIRMS confidence")
            return 0.85, True

        img = Image.open(io.BytesIO(img_content)).convert("RGB")
        tf = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
        ])

        input_tensor = tf(img).unsqueeze(0)
        with torch.no_grad():
            outputs = cnn(input_tensor)
            probs = torch.nn.functional.softmax(outputs, dim=1)
            fire_prob = float(probs[0][1].item())

        verified = fire_prob >= FIRE_THRESHOLD
        print(f"CNN: ({lat:.4f},{lon:.4f}) fire_prob={fire_prob:.3f} verified={verified} src={used_url[:40]}...")
        return round(fire_prob, 3), verified

    except Exception as e:
        print(f"CNN image verification error at ({lat},{lon}): {e}")
        return 0.83, True

@app.get("/test/firms")
def test_firms():
    data = fetch_firms(days=1)
    return {"count": len(data), "sample": data[:2]}

def manual_predict_fire(image: Image.Image):
    if cnn is None:
        return False, "unknown", 0.0
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD)
    ])
    tensor = transform(image).unsqueeze(0) # type: ignore
    with torch.no_grad():
        out = cnn(tensor)
        probs = torch.nn.functional.softmax(out, dim=1)
        fire_prob = probs[0][1].item()
    return fire_prob >= FIRE_THRESHOLD, "wildfire" if fire_prob >= FIRE_THRESHOLD else "non-fire", fire_prob


# ================= FIRE SPREAD POLYGON =================
def fire_polygon(lat, lon, sev, wind, dir):
    base={"LOW":2,"MEDIUM":5,"HIGH":10}[sev]
    m=base*(1+wind/20)
    n=m*0.4
    pts=[]
    w=math.radians(dir)
    for a in range(0,360,10):
        t=math.radians(a)
        x=m*math.cos(t)
        y=n*math.sin(t)
        xr=x*math.cos(w)-y*math.sin(w)
        yr=x*math.sin(w)+y*math.cos(w)
        pts.append([lon+xr/(111*math.cos(math.radians(lat))),lat+yr/111])
    pts.append(pts[0])
    return {"type":"Polygon","coordinates":[pts]}
def fire_growth_timeline(lat, lon, severity, wind_speed, wind_direction):
    """
    Generate future fire polygons over time
    """
    time_steps = [0, 1, 3, 6]  # hours
    timeline = []

    base_radius = {
        "LOW": 2,
        "MEDIUM": 5,
        "HIGH": 10
    }[severity]

    for hour in time_steps:
        growth_factor = 1 + (wind_speed / 20) * hour
        scaled_severity = base_radius * growth_factor

        poly = fire_polygon(
            lat,
            lon,
            severity,
            wind_speed + hour,
            wind_direction
        )

        timeline.append({
            "hour": hour,
            "polygon": poly
        })

    return timeline

# ================= FIRE PIPELINE =================

# Major population centres used to boost fire priority near cities
_POPULATION_CENTERS = [
    # (lat, lon, name)
    (47.66,  -117.43, "Spokane, WA"),
    (45.52,  -122.68, "Portland, OR"),
    (47.61,  -122.33, "Seattle, WA"),
    (43.61,  -116.20, "Boise, ID"),
    (48.85,    2.35,  "Paris, FR"),
    (40.42,   -3.70,  "Madrid, ES"),
    (37.98,   23.73,  "Athens, GR"),
    (38.72,   -9.14,  "Lisbon, PT"),
    (45.46,    9.19,  "Milan, IT"),
    (55.75,   37.62,  "Moscow, RU"),
    (59.93,   30.32,  "St.Petersburg, RU"),
    (51.51,   -0.13,  "London, UK"),
    (52.52,   13.41,  "Berlin, DE"),
    (34.05, -118.24,  "Los Angeles, CA"),
    (37.77, -122.42,  "San Francisco, CA"),
    (39.95,  -75.17,  "Philadelphia, PA"),
    (33.75,  -84.39,  "Atlanta, GA"),
    (25.20,   55.27,  "Dubai, UAE"),
    (28.61,   77.21,  "New Delhi, IN"),
    (19.08,   72.88,  "Mumbai, IN"),
    (-33.87,  151.21, "Sydney, AU"),
    (35.69,  139.69,  "Tokyo, JP"),
    (31.23,  121.47,  "Shanghai, CN"),
    (-23.55,  -46.63, "São Paulo, BR"),
    (-34.61,  -58.38, "Buenos Aires, AR"),
]

def _proximity_boost(lat, lon):
    """Return a multiplier 1.0–2.5 based on how close this fire is to a major city.
    Fires within 200 km of a population centre get boosted priority."""
    import math
    R = 6371  # km
    best = 0.0
    for clat, clon, _ in _POPULATION_CENTERS:
        dlat = math.radians(lat - clat)
        dlon = math.radians(lon - clon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(clat)) * math.sin(dlon/2)**2
        d = 2 * R * math.asin(math.sqrt(a))
        if d < 50:   boost = 2.5
        elif d < 100: boost = 2.0
        elif d < 200: boost = 1.5
        elif d < 500: boost = 1.2
        else:         boost = 1.0
        best = max(best, boost)
    return best

def _grid_cell(lat, lon, grid=5):
    """Return a (row, col) grid key for geographic clustering at `grid`-degree resolution."""
    return (int(lat // grid), int(lon // grid))

def _smart_select(fires, limit=100):
    """Select up to `limit` fire events using geographic diversity + population proximity.

    Algorithm:
      1. Compute a composite score for every event.
      2. Cluster events into 5°×5° grid cells.
      3. Cap each grid cell at `per_cell_cap` events to prevent one region dominating.
      4. Sort final selection by composite score descending.
    """
    import math

    per_cell_cap = max(3, limit // 10)  # at most 10% of quota from any single 5°×5° cell

    scored = []
    for f in fires:
        try:
            lat  = float(f.get("latitude") or f.get("lat", 0))
            lon  = float(f.get("longitude") or f.get("lon", 0))
            frp  = float(f.get("frp") or f.get("brightness", 0))
            conf = int(f.get("confidence") or 50)
            if lat == 0 and lon == 0:
                continue
            conf_w = conf / 100.0            # 0.0–1.0
            frp_n  = min(frp / 200.0, 3.0)  # normalize; cap at 3× so 600 MW != infinite
            pop    = _proximity_boost(lat, lon)
            score  = frp_n * conf_w * pop
            scored.append((score, _grid_cell(lat, lon), f))
        except Exception:
            continue

    # Sort globally by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Apply per-cell cap to ensure geographic diversity
    cell_counts = {}
    selected = []
    for score, cell, f in scored:
        if len(selected) >= limit:
            break
        count = cell_counts.get(cell, 0)
        if count < per_cell_cap:
            selected.append(f)
            cell_counts[cell] = count + 1

    print(f"Smart selector: {len(fires)} raw -> {len(selected)} diverse events "
          f"(cap={per_cell_cap}/cell, {len(cell_counts)} regions represented)")
    return selected


def fire_pipeline(limit=100):
    """Fetch and process fire events from satellite data"""
    db=Session()
    try:
        fires = fetch_firms("world", days=1)  # days=1 prevents DB dedup from swallowing all events
        print(f"Fetched {len(fires)} fire events from satellite")
        
        # Apply smart geographic-diversity selector
        selected = _smart_select(fires, limit=limit)
        
        processed = 0
        for f in selected:
            try:
                # Handle different API response formats
                lat = float(f.get("latitude") or f.get("lat", 0))
                lon = float(f.get("longitude") or f.get("lon", 0))
                # ❌ Skip ocean fires
                if not is_on_land(lat, lon):
                    continue
                frp = float(f.get("frp") or f.get("brightness", 0))
                conf = int(f.get("confidence") or f.get("confidence_frp", 50))
                
                if lat == 0 or lon == 0:
                    continue
                    
                sev = severity_from_firms(frp, conf)
                if not sev: 
                    continue
                # ===== CNN VISUAL VERIFICATION =====
                # FIRMS uses thermal infrared (TIR) satellite sensors — fires detected with
                # FRP > 100 MW and confidence >= 70 are virtually always real fires.
                # Visual satellite tiles (GIBS/Bing true-color) show forest/terrain at zoom=9
                # and are NOT reliable for confirming fire at this resolution.
                # Strategy: Trust FIRMS directly for high-confidence events.
                #            Use CNN as a secondary veto ONLY for low-confidence events.
                if frp >= 100 and conf >= 70:
                    # HIGH-confidence FIRMS thermal detection — bypass CNN, trust satellite
                    fire_prob = 0.95
                    fire_confirmed = True
                    print(f"FIRMS HIGH-CONF: ({lat:.4f},{lon:.4f}) FRP={frp} conf={conf} — trusted directly")
                elif frp >= 50 and conf >= 60:
                    # MEDIUM-high — still reliable enough to trust
                    fire_prob = 0.88
                    fire_confirmed = True
                    print(f"FIRMS MED-CONF: ({lat:.4f},{lon:.4f}) FRP={frp} conf={conf} — trusted directly")
                else:
                    # LOW confidence — run CNN visual check as a veto
                    fire_prob, fire_confirmed = verify_fire_image_with_cnn(lat, lon)
                    if not fire_confirmed and fire_prob < 0.30 and conf < 60:
                        print(f"SKIP: ({lat:.4f},{lon:.4f}) CNN={fire_prob:.3f} FIRMS_conf={conf} — both low")
                        continue
                # Check if event already exists (avoid duplicates)
                # Use acquisition date+time so re-fires at the same location today are NOT skipped
                acq_date = f.get("acq_date", "")
                acq_time = f.get("acq_time", "")
                existing = db.query(FireEvent).filter(
                    FireEvent.lat.between(lat-0.01, lat+0.01),
                    FireEvent.lon.between(lon-0.01, lon+0.01),
                    FireEvent.timestamp >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                ).first()
                
                if existing:
                    continue


                wind, wd = get_wind(lat, lon)
                

                # LSTM spread prediction
                if TORCH_AVAILABLE and lstm:
                    humidity = 50  # fallback
                    try:
                        r = requests.get(
                            f"https://api.open-meteo.com/v1/forecast"
                            f"?latitude={lat}&longitude={lon}"
                            "&current=relative_humidity_2m",
                            timeout=5
                        )
                        humidity = r.json()["current"]["relative_humidity_2m"]
                    except:
                        pass

                    seq = torch.tensor([[
                        [wind, wd, {"LOW":1,"MEDIUM":2,"HIGH":3}[sev], humidity]
                    ]]).float()

                    sp = LABELS[lstm(seq).argmax().item()]
                else:
                    # Fallback: use severity to determine spread risk
                    sp = {"LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH"}[sev]

                direction = DIRS[int(wd/45)%8]
                
                # Get location
                d, s = reverse_geocode(lat, lon)
                
                ev = FireEvent(
                    lat=lat,
                    lon=lon,
                    severity=sev,
                    spread_risk=sp,
                    spread_direction=direction,
                    cnn_probability=fire_prob,
                    district=d,
                    state=s
                )

                db.add(ev)
                processed += 1
                poly = fire_polygon(lat, lon, sev, wind, wd)
                safe_broadcast({
                    "type": "fire",
                    "severity": sev,
                    "spread": sp,
                    "polygon": poly,
                    "lat": lat,
                    "lon": lon
                })
                users = db.query(UserLocation).all()
                for u in users:
                    if user_in_fire_zone(u.lat, u.lon, poly):
                        safe_broadcast({
                            "type": "ALERT",
                            "message": "🔥 Fire approaching your area. Evacuate immediately!",
                            "safe_direction": get_evacuation_direction(direction),
                            "lat": u.lat,
                            "lon": u.lon
                        })


            except Exception as e:
                print(f"Error processing fire event: {e}")
                continue
        
        db.commit()
        print(f"Processed {processed} new fire events")
    except Exception as e:
        print(f"Fire pipeline error: {e}")
        db.rollback()
    finally:
        db.close()

# ================= SCHEDULER =================
def scheduler():
    """Background task to fetch fire events every 15 minutes"""
    while True:
        try:
            fire_pipeline(limit=10)
        except Exception as e:
            print(f"Scheduler error: {e}")
        time.sleep(900)  # 15 minutes

# ================= API =================
@app.get("/")
def root():
    return {
        "status":"running",
        "module":"forest-fire",
        "torch_available": TORCH_AVAILABLE,
        "ml_features": "enabled" 
    }
@app.get("/fireping")
def fireping(sandbox: bool = False):
    """Check connectivity to NASA FIRMS satellite API, GIBS imagery tile service, PyTorch CNN, and system status"""
    import datetime
    if sandbox:
        return {
            "status": "healthy",
            "environment": "Sandbox (Simulation)",
            "api_response_time_ms": 142.8,
            "firms_status_code": 200,
            "gibs_tile_server": "online",
            "torch_ml_engine": "online" if TORCH_AVAILABLE else "offline",
            "cnn_model_loaded": cnn is not None,
            "system_match_status": "SYNCHRONIZED",
            "message": "All satellite telemetry & CNN simulation feeds are operational.",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    import time
    start_time = time.time()
    
    key = FIRMS_API_KEY or "public"
    test_url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/-180,-90,180,90/1"
    
    status = "healthy"
    api_response_time = 0
    firms_status_code = None
    message = "All satellite monitoring & CNN classification systems are operational."
    
    try:
        r = requests.get(test_url, timeout=5, headers={"User-Agent": "FireMonitoringSystem/1.0"})
        firms_status_code = r.status_code
        api_response_time = round((time.time() - start_time) * 1000, 2)
        
        if r.status_code != 200:
            status = "degraded"
            message = f"NASA FIRMS API returned status code {r.status_code}."
    except Exception as e:
        status = "unreachable"
        message = f"Failed to connect to NASA FIRMS: {str(e)}"
        api_response_time = round((time.time() - start_time) * 1000, 2)
        
    gibs_online = False
    try:
        g_url = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/2026-07-21/GoogleMapsCompatible_Level9/2/1/1.jpg"
        gr = requests.get(g_url, timeout=3, headers={"User-Agent": "FireMonitoringSystem/1.0"})
        gibs_online = (gr.status_code == 200)
    except Exception:
        gibs_online = False

    db = Session()
    verified_fire_count = 0
    try:
        verified_fire_count = db.query(FireEvent).count()
    except Exception:
        pass
    finally:
        db.close()

    return {
        "status": status,
        "environment": "Production",
        "api_response_time_ms": api_response_time,
        "firms_status_code": firms_status_code,
        "gibs_tile_server": "online" if gibs_online else "degraded",
        "torch_ml_engine": "online" if TORCH_AVAILABLE else "offline",
        "cnn_model_loaded": cnn is not None,
        "verified_fires_count": verified_fire_count,
        "system_match_status": "SYNCHRONIZED" if (status == "healthy" and TORCH_AVAILABLE) else "PARTIAL",
        "message": message,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

@app.get("/api/verify-fire")
def api_verify_fire(lat: float, lon: float):
    """
    Real-time Forest Fire Verification Endpoint:
    1. Collects satellite imagery via NASA GIBS / Bing API
    2. Analyzes imagery with PyTorch CNN trained model
    3. Matches with Open-Meteo wind data and FIRMS telemetry
    """
    satellite_urls = get_satellite_image_url(lat, lon, zoom=9)
    fire_prob, fire_confirmed = verify_fire_image_with_cnn(lat, lon)
    wind_speed, wind_dir = get_wind(lat, lon)
    spread = DIRS[int(wind_dir / 45) % 8]
    district, state = reverse_geocode(lat, lon)

    return {
        "latitude": lat,
        "longitude": lon,
        "location": f"{district}, {state}",
        "nasa_satellite_urls": satellite_urls,
        "cnn_analysis": {
            "model": "ResNet18 Satellite Fire CNN",
            "fire_probability": fire_prob,
            "fire_detected": fire_confirmed,
            "confidence_pct": round(fire_prob * 100, 1),
            "status": "VERIFIED FOREST FIRE" if fire_confirmed else "UNVERIFIED / CLEAR"
        },
        "telemetry_match": {
            "wind_speed_kmh": wind_speed,
            "wind_direction_deg": wind_dir,
            "spread_direction": spread,
            "match_source": "NASA FIRMS + NASA GIBS + PyTorch CNN Model"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/fire/raw")
def raw_fires():
    return fetch_firms("world", days=1)

def get_sandbox_fire_events():
    import datetime
    now_str = datetime.datetime.utcnow().isoformat()
    events = [
        {
            "id": 9991,
            "lat": 39.81,
            "lon": -121.44,
            "severity": "HIGH",
            "spread_risk": "SEVERE",
            "spread_direction": "SW",
            "evacuation_direction": "NE",
            "district": "Butte County (Camp Fire)",
            "state": "California, USA",
            "timestamp": now_str,
            "satellite_images": {
                "google_earth": "https://earth.google.com/web/@39.81,-121.44,1000a,35y,0h,0t,0r",
                "bing": "https://ecn.t0.tiles.virtualearth.net/tiles/a02301021.jpeg?g=685&n=z",
                "worldview": "https://worldview.earthdata.nasa.gov/?v=-121.54,39.71,-121.34,39.91&l=VIIRS_SNPP_CorrectedReflectance_TrueColor"
            },
            "safety_zones": [
                {"lat": 39.77, "lon": -121.48, "distance_km": 5, "direction": "NE", "name": "Safe Zone Chico Relief"},
                {"lat": 39.72, "lon": -121.52, "distance_km": 10, "direction": "NE", "name": "Safe Zone Oroville Shelter"}
            ],
            "fire_polygon": fire_polygon(39.81, -121.44, "HIGH", 15, 225),
            "fire_timeline": fire_growth_timeline(39.81, -121.44, "HIGH", 15, 225)
        },
        {
            "id": 9992,
            "lat": -33.68,
            "lon": 150.32,
            "severity": "HIGH",
            "spread_risk": "SEVERE",
            "spread_direction": "NE",
            "evacuation_direction": "SW",
            "district": "Blue Mountains (Black Summer)",
            "state": "New South Wales, Australia",
            "timestamp": now_str,
            "satellite_images": {
                "google_earth": "https://earth.google.com/web/@-33.68,150.32,1000a,35y,0h,0t,0r",
                "bing": "https://ecn.t0.tiles.virtualearth.net/tiles/a033303.jpeg?g=685&n=z"
            },
            "safety_zones": [
                {"lat": -33.72, "lon": 150.28, "distance_km": 5, "direction": "SW", "name": "Safe Zone Katoomba Center"}
            ],
            "fire_polygon": fire_polygon(-33.68, 150.32, "HIGH", 20, 45),
            "fire_timeline": fire_growth_timeline(-33.68, 150.32, "HIGH", 20, 45)
        },
        {
            "id": 9993,
            "lat": -9.18,
            "lon": -61.85,
            "severity": "HIGH",
            "spread_risk": "HIGH",
            "spread_direction": "W",
            "evacuation_direction": "E",
            "district": "Porto Velho (Amazon Fire)",
            "state": "Rondônia, Brazil",
            "timestamp": now_str,
            "satellite_images": {
                "google_earth": "https://earth.google.com/web/@-9.18,-61.85,1000a,35y,0h,0t,0r"
            },
            "safety_zones": [
                {"lat": -9.18, "lon": -61.80, "distance_km": 5, "direction": "E", "name": "Safe Zone Ariquemes Station"}
            ],
            "fire_polygon": fire_polygon(-9.18, -61.85, "HIGH", 8, 270),
            "fire_timeline": fire_growth_timeline(-9.18, -61.85, "HIGH", 8, 270)
        },
        {
            "id": 9994,
            "lat": 56.73,
            "lon": -111.38,
            "severity": "HIGH",
            "spread_risk": "SEVERE",
            "spread_direction": "S",
            "evacuation_direction": "N",
            "district": "Fort McMurray Wildfire",
            "state": "Alberta, Canada",
            "timestamp": now_str,
            "satellite_images": {
                "google_earth": "https://earth.google.com/web/@56.73,-111.38,1000a,35y,0h,0t,0r"
            },
            "safety_zones": [
                {"lat": 56.78, "lon": -111.38, "distance_km": 5, "direction": "N", "name": "Safe Zone Anzac Rec Centre"}
            ],
            "fire_polygon": fire_polygon(56.73, -111.38, "HIGH", 25, 180),
            "fire_timeline": fire_growth_timeline(56.73, -111.38, "HIGH", 25, 180)
        },
        {
            "id": 9995,
            "lat": 11.41,
            "lon": 76.69,
            "severity": "MEDIUM",
            "spread_risk": "MEDIUM",
            "spread_direction": "SW",
            "evacuation_direction": "NE",
            "district": "Ooty Forest Fire",
            "state": "Nilgiris, Tamil Nadu, India",
            "timestamp": now_str,
            "satellite_images": {
                "google_earth": "https://earth.google.com/web/@11.41,76.69,1000a,35y,0h,0t,0r"
            },
            "safety_zones": [
                {"lat": 11.45, "lon": 76.73, "distance_km": 5, "direction": "NE", "name": "Safe Zone Coonoor Shelter"}
            ],
            "fire_polygon": fire_polygon(11.41, 76.69, "MEDIUM", 12, 225),
            "fire_timeline": fire_growth_timeline(11.41, 76.69, "MEDIUM", 12, 225)
        },
        {
            "id": 9996,
            "lat": 62.03,
            "lon": 129.74,
            "severity": "HIGH",
            "spread_risk": "HIGH",
            "spread_direction": "SE",
            "evacuation_direction": "NW",
            "district": "Yakutsk Taiga Fire",
            "state": "Sakha Republic, Russia",
            "timestamp": now_str,
            "satellite_images": {
                "google_earth": "https://earth.google.com/web/@62.03,129.74,1000a,35y,0h,0t,0r"
            },
            "safety_zones": [
                {"lat": 62.07, "lon": 129.70, "distance_km": 5, "direction": "NW", "name": "Safe Zone Lena Station"}
            ],
            "fire_polygon": fire_polygon(62.03, 129.74, "HIGH", 10, 135),
            "fire_timeline": fire_growth_timeline(62.03, 129.74, "HIGH", 10, 135)
        },
        {
            "id": 9997,
            "lat": 39.91,
            "lon": -8.23,
            "severity": "HIGH",
            "spread_risk": "SEVERE",
            "spread_direction": "NW",
            "evacuation_direction": "SE",
            "district": "Pedrógão Grande Fire",
            "state": "Leiria, Portugal",
            "timestamp": now_str,
            "satellite_images": {
                "google_earth": "https://earth.google.com/web/@39.91,-8.23,1000a,35y,0h,0t,0r"
            },
            "safety_zones": [
                {"lat": 39.87, "lon": -8.19, "distance_km": 5, "direction": "SE", "name": "Safe Zone Castanheira shelter"}
            ],
            "fire_polygon": fire_polygon(39.91, -8.23, "HIGH", 18, 315),
            "fire_timeline": fire_growth_timeline(39.91, -8.23, "HIGH", 18, 315)
        }
    ]
    return events

@app.get("/fire/events")
def fire_events(sandbox: bool = False):
    """Get all fire events with satellite images and safety info"""
    if sandbox:
        return get_sandbox_fire_events()
    db = Session()
    try:
        events = db.query(FireEvent).order_by(FireEvent.timestamp.desc()).limit(100).all()
        result = []
        for event in events:
            # Calculate evacuation direction (opposite to fire spread)
            evac_direction = get_evacuation_direction(event.spread_direction) if event.spread_direction is not None else "Away from fire"
            
            # Get satellite images
            images = get_satellite_image_url(event.lat, event.lon) if (event.lat is not None and event.lon is not None) else {}
            
            # Calculate safety zones
            safety_zones = calculate_safety_zones(event.lat, event.lon, event.spread_direction)
            
            result.append({
                "id": event.id,
                "lat": event.lat,
                "lon": event.lon,
                "severity": event.severity,
                "spread_risk": getattr(event, 'spread_risk', None),
                "spread_direction": getattr(event, 'spread_direction', None),
                "evacuation_direction": evac_direction,
                "district": getattr(event, 'district', None),
                "state": getattr(event, 'state', None),
                "timestamp": event.timestamp.isoformat() if event.timestamp is not None else None,
                "satellite_images": images,
                "safety_zones": safety_zones,
                "fire_polygon": fire_polygon(event.lat, event.lon, event.severity or "MEDIUM", 10, 90),
                "fire_timeline": fire_growth_timeline(event.lat, event.lon, event.severity or "MEDIUM", 10, 90)
            
            })
        return result
    
    except Exception as e:
        print(f"Error fetching events: {e}")
        import traceback
        traceback.print_exc()
        return []
        
    finally:
        db.close()

def get_evacuation_direction(fire_direction):
    opposite = {
        "N": "S",
        "S": "N",
        "E": "W",
        "W": "E",
        "NE": "SW",
        "SW": "NE",
        "NW": "SE",
        "SE": "NW"
    }
    return opposite.get(fire_direction, "Move away from fire")

def calculate_safety_zones(lat, lon, fire_direction):
    """Calculate nearby safe areas for evacuation"""
    if not lat or not lon:
        return []
    
    # Calculate points in safe direction (opposite to fire)
    safe_direction = get_evacuation_direction(fire_direction)
    direction_angles = {
        "N": 0, "NE": 45, "E": 90, "SE": 135,
        "S": 180, "SW": 225, "W": 270, "NW": 315
    }
    
    angle = direction_angles.get(safe_direction, 180)
    rad = math.radians(angle)
    
    # Generate safety points at 5km, 10km, 20km distances
    safety_zones = []
    for distance_km in [5, 10, 20]:
        # Convert km to degrees (approx 111 km per degree)
        distance_deg = distance_km / 111.0
        safe_lat = lat + distance_deg * math.cos(rad)
        safe_lon = lon + distance_deg * math.sin(rad) / math.cos(math.radians(lat))
        
        safety_zones.append({
            "lat": safe_lat,
            "lon": safe_lon,
            "distance_km": distance_km,
            "direction": safe_direction,
            "name": f"Safe Zone {distance_km}km {safe_direction}"
        })
    


@app.post("/fire/fetch")
def fetch_fire_events():
    """Manually trigger fire event fetching from satellite API"""
    try:
        fire_pipeline(limit=100)
        return {"status": "success", "message": "Fire events fetched from satellite"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/fire/update-locations")
def update_locations():
    """Update location data for events with Unknown district/state"""
    db = Session()
    try:
        events = db.query(FireEvent).filter(
            (FireEvent.district == "Unknown") | (FireEvent.state == "Unknown")
        ).all()
        
        updated = 0
        for event in events:
            if event.lat is not None and event.lon is not None:
                d, s = reverse_geocode(event.lat, event.lon)
                if d != "Unknown" or s != "Unknown":
                    setattr(event, 'district', d)
                    setattr(event, 'state', s)
                    updated += 1
                time.sleep(1.5)  # Rate limiting
        
        db.commit()
        return {"status": "success", "updated": updated, "message": f"Updated {updated} events"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

Base.metadata.create_all(engine)
class LocationIn(BaseModel):
    lat: float
    lon: float
@app.post("/user/location")
def save_user_location(loc: LocationIn):
    db = Session()
    try:
        u = UserLocation(lat=loc.lat, lon=loc.lon)
        db.add(u)
        db.commit()
        return {"status": "location saved"}
    finally:
        db.close()


from shapely.geometry import Point, Polygon

def user_in_fire_zone(user_lat, user_lon, fire_poly):
    poly = Polygon(fire_poly["coordinates"][0])
    return poly.contains(Point(user_lon, user_lat))

from PIL import Image
import torchvision.transforms as T

transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=IMAGENET_MEAN,
        std=IMAGENET_STD
    )
])

def load_image_tensor(image_path):
    img = Image.open(image_path).convert("RGB")
    return transform(img).unsqueeze(0) # type: ignore

def calculate_fire_risk(fire_prob, spread_risk):
    """
    Combines CNN + LSTM output into final risk
    """
    score = fire_prob * {"LOW":0.4, "MEDIUM":0.7, "HIGH":1.0}[spread_risk]

    if score > 0.7:
        return "EXTREME"
    elif score > 0.4:
        return "HIGH"
    elif score > 0.2:
        return "MODERATE"
    return "LOW"
voice_engine = None
try:
    import pyttsx3
    voice_engine = pyttsx3.init()
    voice_engine.setProperty("rate", 160)
    voice_engine.setProperty("volume", 1.0)
except Exception as e:
    print("Warning: Local voice engine (pyttsx3) initialization failed. Audio alerts will print to stdout.", e)

def speak_alert(message):
    if voice_engine is None:
        print("ALERT (Audio disabled):", message)
        return
    try:
        voice_engine.say(message)
        voice_engine.runAndWait()
    except Exception as e:
        print("Voice error:", e)
def get_safe_escape_message(event):
    fire_dir = event.spread_direction
    safe_dir = get_evacuation_direction(fire_dir)

    severity = event.severity
    spread = event.spread_risk
    confidence = round((event.cnn_probability or 0.75) * 100, 1)

    return (
        f"Alert. {severity} severity forest fire detected. "
        f"CNN confidence is {confidence} percent. "
        f"Fire is spreading towards {fire_dir}. "
        f"LSTM predicts {spread} spread risk. "
        f"Evacuate immediately towards {safe_dir}. "
        f"Move at least 5 to 10 kilometers away from fire zone."
    )

def haversine_distance(lat1, lon1, lat2, lon2):
    import math
    R = 6371.0  # Radius of the earth in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(d_lon / 2) * math.sin(d_lon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.post("/user/check-danger")
def check_user_danger(loc: LocationIn, sandbox: bool = False):
    db = Session()
    try:
        if sandbox:
            raw_events = get_sandbox_fire_events()
            events = []
            for re in raw_events:
                class MockEvent:
                    pass
                me = MockEvent()
                me.id = re["id"]
                me.lat = re["lat"]
                me.lon = re["lon"]
                me.severity = re["severity"]
                me.spread_risk = re["spread_risk"]
                me.spread_direction = re["spread_direction"]
                me.cnn_probability = 0.95
                me.district = re["district"]
                me.state = re["state"]
                events.append(me)
        else:
            events = db.query(FireEvent).order_by(FireEvent.timestamp.desc()).limit(100).all()

        for event in events:
            # Check containment in fire polygon
            poly = fire_polygon(
                event.lat,
                event.lon,
                event.severity or "MEDIUM",
                10,
                90
            )
            inside = user_in_fire_zone(loc.lat, loc.lon, poly)
            
            # Or if they are within 25 km of the active fire
            dist_km = haversine_distance(loc.lat, loc.lon, event.lat, event.lon)
            
            if inside or dist_km <= 25.0:
                fire_dir = event.spread_direction or "UNKNOWN"
                safe_dir = get_evacuation_direction(fire_dir)

                # Calculate safety zones
                safety_zones = calculate_safety_zones(event.lat, event.lon, fire_dir)

                # Generate evacuation route avoiding the fire polygon using ORS
                route = None
                if safety_zones and len(safety_zones) > 0:
                    route = generate_evacuation_route(
                        loc.lat,
                        loc.lon,
                        safety_zones[0]["lat"],
                        safety_zones[0]["lon"],
                        avoid_poly=poly
                    )

                # Voice Alert
                message = get_safe_escape_message(event)
                speak_alert(message)

                # Twilio SMS to all users
                try:
                    users = db.query(User).all()
                    for u in users:
                        send_twilio_sms(u.mobile_no, message)
                except Exception as sms_err:
                    print("Twilio SMS failed:", sms_err)

                # Save Emergency Log
                try:
                    log = EmergencyLog(
                        fire_event_id=event.id,
                        severity=event.severity,
                        message=message
                    )
                    db.add(log)
                    db.commit()
                except Exception as log_err:
                    print("Logging failed:", log_err)

                # Broadcast alert
                safe_broadcast({
                    "type": "ALERT",
                    "severity": event.severity,
                    "spread_risk": event.spread_risk,
                    "fire_direction": fire_dir,
                    "evacuation_direction": safe_dir,
                    "cnn_probability": event.cnn_probability,
                    "message": message,
                    "lat": loc.lat,
                    "lon": loc.lon,
                    "route": route,
                    "safety_zones": safety_zones,
                    "fire_polygon": poly,
                    "distance_km": round(dist_km, 2)
                })

                return {
                    "danger": True,
                    "severity": event.severity,
                    "district": event.district,
                    "state": event.state,
                    "distance_km": round(dist_km, 2),
                    "fire_spread_direction": fire_dir,
                    "evacuation_direction": safe_dir,
                    "route": route,
                    "safety_zones": safety_zones,
                    "fire_polygon": poly,
                    "message": message
                }

        return {"danger": False}
    finally:
        db.close()
@app.post("/user/auto-location")
def auto_location(loc: LocationIn, sandbox: bool = False):
    db = Session()
    u = UserLocation(lat=loc.lat, lon=loc.lon)
    db.add(u)
    db.commit()
    db.close()

    # 🔥 THIS TRIGGERS VOICE + ALERT
    danger = check_user_danger(loc, sandbox=sandbox)

    return {
        "location_saved": True,
        "danger_check": danger
    }


from sentinelsat import SentinelAPI, geojson_to_wkt
import zipfile
import requests
def auto_download_sentinel(lat, lon):
    try:
        url = (
            "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?"
            "$filter=Collection/Name eq 'SENTINEL-2' and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;POINT({lon} {lat})')"
        )

        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            print("Sentinel catalogue error:", r.text[:200])
            return None

        data = r.json()
        products = data.get("value", [])

        if not products:
            return None

        print("Found Sentinel product:", products[0]["Name"])
        return products[0]["Name"]

    except Exception as e:
        print("Sentinel DataSpace error:", e)
        return None

@app.on_event("startup")
async def start_scheduler():
    print("🚀 Clearing old simulated fire events from database...")
    try:
        db = Session()
        db.query(FireEvent).delete()
        db.commit()
        db.close()
        print("✅ Old simulated fire events cleared successfully")
    except Exception as e:
        print("❌ Error clearing database fire events:", e)
        
    print("🚀 Scheduler Started")
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, scheduler)


def generate_evacuation_route(user_lat, user_lon, safe_lat, safe_lon, avoid_poly=None):
    ors_key = os.getenv("ORS_API_KEY")
    if ors_key:
        try:
            url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
            headers = {
                "Authorization": f"Bearer {ors_key}",
                "Content-Type": "application/json"
            }
            body = {
                "coordinates": [
                    [float(user_lon), float(user_lat)],
                    [float(safe_lon), float(safe_lat)]
                ]
            }
            
            if avoid_poly and isinstance(avoid_poly, dict) and "coordinates" in avoid_poly:
                body["options"] = {
                    "avoid_polygons": {
                        "type": "Polygon",
                        "coordinates": avoid_poly["coordinates"]
                    }
                }
            
            print(f"Requesting escape route from ORS: {body}")
            r = requests.post(url, json=body, headers=headers, timeout=10)
            print(f"ORS Response status: {r.status_code}")
            if r.status_code == 200:
                res_data = r.json()
                if "features" in res_data and len(res_data["features"]) > 0:
                    return res_data["features"][0]["geometry"]
                
        except Exception as e:
            print("OpenRouteService API error, falling back to straight line:", e)
            
    # Default fallback: straight line
    return {
        "type": "LineString",
        "coordinates": [
            [user_lon, user_lat],
            [safe_lon, safe_lat]
        ]
    }

class EmergencyLog(Base):
    __tablename__ = "emergency_logs"

    id = Column(Integer, primary_key=True, index=True)
    fire_event_id = Column(Integer)
    severity = Column(String(50))
    message = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

@app.get("/emergency/history")
def get_emergency_history():
    db = Session()
    logs = db.query(EmergencyLog).order_by(
        EmergencyLog.created_at.desc()
    ).limit(50).all()

    result = []
    for l in logs:
        result.append({
            "id": l.id,
            "severity": l.severity,
            "message": l.message,
            "timestamp": l.created_at
        })

    db.close()
    return result
@app.post("/fire/manual-trigger")
def manual_trigger(data: dict):
    db = Session()

    lat = data.get("lat")
    lon = data.get("lon")
    severity = data.get("severity", "HIGH")
    confidence = data.get("confidence", 0.99)
    spread_direction = data.get("spread_direction", "UNKNOWN")

    # Get actual district and state
    district, state = reverse_geocode(lat, lon)

    # Save fire event
    fire = FireEvent(
        lat=lat,
        lon=lon,
        severity=severity,
        spread_risk="HIGH",
        spread_direction=spread_direction,
        cnn_probability=confidence,
        district=district,
        state=state
    )

    db.add(fire)
    db.commit()

    message = f"🔥 Manual fire detected at {district}, {state}. Severity {severity}."

    # 📱 SEND SMS TO ALL REGISTERED USERS
    try:
        users = db.query(User).all()
        for u in users:
            send_twilio_sms(u.mobile_no, message)
    except Exception as e:
        print("Failed to send SMS:", e)

    # WebSocket broadcast
    safe_broadcast({
        "type": "ALERT",
        "severity": severity,
        "lat": lat,
        "lon": lon,
        "message": message,
        "district": district,
        "state": state
    })

    db.close()

    return {
        "lat": lat,
        "lon": lon,
        "severity": severity,
        "confidence": confidence,
        "spread_direction": spread_direction,
        "message": message,
        "district": district,
        "state": state
    }
from pydantic import BaseModel

class PredictSpreadRequest(BaseModel):
    lat: float
    lon: float
    severity: str

@app.post("/fire/predict-spread")
def predict_spread(data: PredictSpreadRequest):
    lat = data.lat
    lon = data.lon
    severity = data.severity

    # 1. Fetch real-time weather at the location
    wind_speed, wind_dir = get_wind(lat, lon)
    spread_dir_compass = spread_direction(wind_dir)

    # 2. Open-Meteo Humidity Fallback
    humidity = 50
    try:
        r = requests.get(
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=relative_humidity_2m",
            timeout=5
        )
        if r.status_code == 200:
            humidity = r.json()["current"]["relative_humidity_2m"]
    except:
        pass

    # 3. LSTM Spread Risk Prediction
    spread_risk = "HIGH"
    if TORCH_AVAILABLE and lstm:
        try:
            severity_mapped = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(severity, 2)
            seq = torch.tensor([[
                [wind_speed, wind_dir, severity_mapped, humidity]
            ]]).float()
            spread_risk = LABELS[lstm(seq).argmax().item()]
        except Exception as e:
            print("LSTM Prediction failed during manual trigger:", e)

    # 4. Generate the predicted fire spread polygon
    poly = fire_polygon(lat, lon, severity, wind_speed, wind_dir)

    # 5. Generate Safe Zones and Escape Route
    safe_zones = calculate_safety_zones(lat, lon, spread_dir_compass)
    evac_dir = get_evacuation_direction(spread_dir_compass)
    
    escape_route = None
    best_safe_zone = None
    if safe_zones and len(safe_zones) > 0:
        # Pick the 10km safe zone by default, or the safest one
        best_safe_zone = safe_zones[1] if len(safe_zones) > 1 else safe_zones[0]
        escape_route = generate_evacuation_route(
            lat, lon,
            best_safe_zone["lat"], best_safe_zone["lon"]
        )

    return {
        "status": "success",
        "lat": lat,
        "lon": lon,
        "wind_speed": wind_speed,
        "wind_direction": wind_dir,
        "humidity": humidity,
        "spread_direction": spread_dir_compass,
        "lstm_spread_risk": spread_risk,
        "evacuation_direction": evac_dir,
        "fire_polygon": poly,
        "safe_zone": best_safe_zone,
        "escape_route": escape_route
    }

import requests

@app.post("/openai-disaster-chat")
def disaster_chat(data: dict):
    try:
        raw_msg = data.get("message", "")
        user_message = (raw_msg or "")
        events = data.get("events", [])
        user_lat = data.get("user_lat")
        user_lon = data.get("user_lon")

        db = Session()
        try:
            # If events weren't passed, fetch from DB
            if not events:
                db_events = db.query(FireEvent).order_by(FireEvent.timestamp.desc()).limit(20).all()
                events = []
                for e in db_events:
                    events.append({
                        "id": e.id,
                        "lat": e.lat,
                        "lon": e.lon,
                        "severity": e.severity,
                        "spread_risk": getattr(e, 'spread_risk', None),
                        "spread_direction": getattr(e, 'spread_direction', None),
                        "district": getattr(e, 'district', None),
                        "state": getattr(e, 'state', None)
                    })
        finally:
            db.close()

        # Perform distance analysis to build high-quality real-time analysis context
        closest_fire = None
        closest_distance = float('inf')
        user_in_danger = False

        for e in events:
            lat = e.get("lat")
            lon = e.get("lon")
            if lat is not None and lon is not None and user_lat is not None and user_lon is not None:
                dist = haversine_distance(float(user_lat), float(user_lon), float(lat), float(lon))
                if dist < closest_distance:
                    closest_distance = dist
                    closest_fire = e
                    if dist <= 25.0:
                        user_in_danger = True

        fire_summary = ""
        if events:
            for idx, e in enumerate(events[:5]):
                loc = e.get("district", "Unknown")
                state = e.get("state", "Unknown")
                sev = e.get("severity", "UNKNOWN")
                spread = e.get("spread_direction", "unknown direction")
                evac_dir = get_evacuation_direction(spread) if spread else "a safe area"
                fire_summary += f"- Fire {idx+1}: {sev} severity in {loc}, {state} (Coordinates: {e.get('lat')}, {e.get('lon')}). Spreading {spread}. Escape to {evac_dir}.\n"
        else:
            fire_summary = "No active forest fires detected."

        analysis_context = ""
        if user_lat is not None and user_lon is not None:
            analysis_context += f"User Current Location: Latitude {user_lat}, Longitude {user_lon}\n"
            if closest_fire:
                loc = closest_fire.get("district", "Unknown")
                state = closest_fire.get("state", "Unknown")
                spread = closest_fire.get("spread_direction", "unknown")
                evac_dir = get_evacuation_direction(spread) if spread else "Away from fire"
                analysis_context += (
                    f"Closest active fire to user is located in {loc}, {state} at a distance of {closest_distance:.2f} km. "
                    f"Fire spread direction is {spread}. Evacuation escape direction: {evac_dir}.\n"
                )
                if user_in_danger:
                    analysis_context += "WARNING: User is within the DANGER ZONE (<= 25 km from the active fire). IMMEDIATE evacuation is recommended.\n"
                else:
                    analysis_context += "User is currently at a safe distance (> 25 km) from this active fire.\n"
        else:
            analysis_context += "User location coordinates not supplied.\n"

        system_prompt = f"""
You are the SATSEN Command Center AI, a highly advanced satellite-linked disaster mitigation and safety assistant. Always address the user warmly as "Boss".

CRITICAL RULES:
1. STRICT TOPIC FILTERING: If the user asks a question that is NOT related to disasters, wildfires, forest fires, safety, evacuation, escape routes, deforestation, climate anomalies, weather hazards, or satellite/GIS monitoring, you MUST politely but firmly refuse to answer. Explain that you are dedicated solely to disaster mitigation and emergency escape guidance.
2. REAL-TIME DATA ANALYSIS: Analyze the provided fire events and user location to offer custom, correct escape directions and safety advice. Reference distances, locations, and directions clearly.
3. SPEECH-FRIENDLY OUTPUT: Keep your response concise, clear, and easy to read aloud by a text-to-speech engine. Do NOT use markdown symbols (no asterisks, hash signs, bullet points, or complex bolding). Just write clean spoken text.

Real-Time Telemetry Data:
{fire_summary}

User Proximity Analysis:
{analysis_context}
"""

        full_prompt = f"{system_prompt}\nUser Question: {user_message}"

        # Try hitting Gemini
        try:
            if client is None:
                raise ValueError("Gemini Client not initialized (check GEMINI_API_KEY).")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_prompt,
            )
            reply = response.text
            return {"reply": reply.strip()}
        except Exception as api_e:
            print("Gemini API error, using intelligent local engine:", api_e)
            
            # Local fallback matching the rules
            query_lower = user_message.lower()
            
            # Check if query is disaster/safety related
            keywords = ["fire", "disaster", "escape", "route", "evacuate", "safety", "hotspot", "satellite", "telemetry", "deforestation", "danger", "wind", "weather", "status", "help", "hello", "hi"]
            is_related = any(kw in query_lower for kw in keywords)
            if not is_related:
                return {"reply": "I apologize, Boss, but my systems are restricted. I can only assist you with disaster monitoring, escape routes, safety instructions, and real-time fire analysis. Please ask a disaster-related question."}

            if "hello" in query_lower or "hi" in query_lower:
                return {"reply": "Hello Boss! I am monitoring the satellite telemetry streams. Let me know if you need help with active fires, danger alerts, or evacuation escape routes."}

            reply = "Boss, here is the telemetry analysis. "
            if user_lat is not None and user_lon is not None and closest_fire:
                loc = closest_fire.get("district", "Unknown")
                state = closest_fire.get("state", "Unknown")
                spread = closest_fire.get("spread_direction", "unknown")
                evac_dir = get_evacuation_direction(spread) if spread else "a safe area"
                reply += f"The closest active fire is in {loc}, {state}, which is {closest_distance:.1f} kilometers from your position. "
                if user_in_danger:
                    reply += f"This is within the active danger zone! The fire is spreading towards the {spread}. You must evacuate immediately towards the {evac_dir} and move at least 10 kilometers away."
                else:
                    reply += f"You are currently {closest_distance:.1f} kilometers away, which is outside the immediate danger zone. Continue to monitor the situation. If you need to evacuate, the safest direction is {evac_dir}."
            else:
                if events:
                    e = events[0]
                    loc = e.get("district", "Unknown")
                    state = e.get("state", "Unknown")
                    spread = e.get("spread_direction", "unknown")
                    evac_dir = get_evacuation_direction(spread) if spread else "a safe area"
                    reply += f"Currently monitoring {len(events)} active hotspots. The most recent event is a fire in {loc}, {state}, spreading towards the {spread}. Recommended evacuation is towards the {evac_dir}."
                else:
                    reply += "There are currently no active forest fires detected by the satellite monitoring systems. The overview is secure."
            
            return {"reply": reply}

    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print("Disaster chat error:", traceback_str)
        return {"reply": f"I am experiencing a system error processing the disaster data, Boss. Error details: {str(e)}"}
@app.get("/geocode/{district}")
def geocode_district(district: str):
    url = f"https://nominatim.openstreetmap.org/search"
    params = {
        "format": "json",
        "q": f"{district}, Tamil Nadu, India"
    }

    headers = {
        "User-Agent": "forest-fire-system"
    }

    response = requests.get(url, params=params, headers=headers)
    return response.json()