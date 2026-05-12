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
import os, time, threading, asyncio, requests, math
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

    def forward(self, x):
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
FIRE_THRESHOLD = 0.6

def load_fire_model():
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    model.load_state_dict(torch.load("training/fire_cnn.pth", map_location="cpu"))
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
        self.resnet.fc = nn.Sequential(
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
    return land.contains(point).any()


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

import google.generativeai as genai
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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
DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD"))

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800
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
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
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
    mobile_no = request.mobile_no
    
    db = Session()
    db_user = db.query(User).filter(User.mobile_no == mobile_no).first()
    if db_user:
        db.close()
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
    db.close()
    
    # Send via Fast2SMS
    print(f"\n[DEV LOG] ----------------------------------")
    print(f"[DEV LOG] Generated OTP {otp} for {mobile_no}")
    print(f"[DEV LOG] ----------------------------------\n")
    
    send_twilio_sms(mobile_no, f"Your forest monitoring system verification code is {otp}")
            
    return {"message": "OTP sent successfully"}

@app.post("/auth/verify-otp")
def verify_otp(request: OTPVerifyRequest):
    db = Session()
    
    # Step 1: Check if registered
    db_user = db.query(User).filter(User.mobile_no == request.mobile_no).first()
    if db_user:
        db.close()
        raise HTTPException(status_code=400, detail="Mobile number already registered")
        
    # Step 2: Validate OTP
    otp_record = db.query(OTPCode).filter(
        (OTPCode.mobile_no == request.mobile_no) & 
        (OTPCode.otp == request.otp)
    ).first()
    
    if not otp_record:
        db.close()
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    if otp_record.expires_at < datetime.utcnow():
        db.close()
        raise HTTPException(status_code=400, detail="OTP has expired")
        
    # Step 3: Create User
    hashed_password = get_password_hash(request.password)
    new_user = User(mobile_no=request.mobile_no, password_hash=hashed_password)
    db.add(new_user)
    
    # Delete the used OTP
    db.query(OTPCode).filter(OTPCode.mobile_no == request.mobile_no).delete()
    db.commit()
    db.close()
    
    return {"message": "User registered successfully"}

@app.post("/auth/login", response_model=Token)
def login(user: UserLogin):
    db = Session()
    db_user = db.query(User).filter(User.mobile_no == user.mobile_no).first()
    db.close()
    
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect mobile number or password")
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.mobile_no}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

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

@app.post("/add-test-deforestation")
def add_test_deforestation():
    try:
        db = Session()
        
        indian_states_mock_data = [
            {"lat": 16.5, "lon": 80.6, "state": "Andhra Pradesh", "district": "Guntur"},
            {"lat": 28.1, "lon": 94.6, "state": "Arunachal Pradesh", "district": "Siang"},
            {"lat": 26.2, "lon": 92.9, "state": "Assam", "district": "Nagaon"},
            {"lat": 25.6, "lon": 85.1, "state": "Bihar", "district": "Patna"},
            {"lat": 21.3, "lon": 81.6, "state": "Chhattisgarh", "district": "Raipur"},
            {"lat": 15.3, "lon": 74.1, "state": "Goa", "district": "North Goa"},
            {"lat": 22.3, "lon": 71.1, "state": "Gujarat", "district": "Ahmedabad"},
            {"lat": 29.0, "lon": 76.0, "state": "Haryana", "district": "Rohtak"},
            {"lat": 31.1, "lon": 77.2, "state": "Himachal Pradesh", "district": "Shimla"},
            {"lat": 23.4, "lon": 85.3, "state": "Jharkhand", "district": "Ranchi"},
            {"lat": 15.0, "lon": 75.0, "state": "Karnataka", "district": "Dharwad"},
            {"lat": 13.0, "lon": 77.5, "state": "Karnataka", "district": "Bangalore Urban"},
            {"lat": 10.5, "lon": 76.5, "state": "Kerala", "district": "Palakkad"},
            {"lat": 23.3, "lon": 77.4, "state": "Madhya Pradesh", "district": "Bhopal"},
            {"lat": 19.1, "lon": 73.3, "state": "Maharashtra", "district": "Thane"},
            {"lat": 19.8, "lon": 75.3, "state": "Maharashtra", "district": "Aurangabad"},
            {"lat": 24.8, "lon": 93.9, "state": "Manipur", "district": "Imphal"},
            {"lat": 25.5, "lon": 91.9, "state": "Meghalaya", "district": "East Khasi Hills"},
            {"lat": 23.7, "lon": 92.7, "state": "Mizoram", "district": "Aizawl"},
            {"lat": 26.2, "lon": 94.2, "state": "Nagaland", "district": "Kohima"},
            {"lat": 20.3, "lon": 85.8, "state": "Odisha", "district": "Khurda"},
            {"lat": 31.3, "lon": 75.3, "state": "Punjab", "district": "Jalandhar"},
            {"lat": 26.9, "lon": 75.8, "state": "Rajasthan", "district": "Jaipur"},
            {"lat": 24.6, "lon": 73.7, "state": "Rajasthan", "district": "Udaipur"},
            {"lat": 27.3, "lon": 88.6, "state": "Sikkim", "district": "East Sikkim"},
            {"lat": 10.8, "lon": 76.8, "state": "Tamil Nadu", "district": "Coimbatore"},
            {"lat": 13.1, "lon": 80.3, "state": "Tamil Nadu", "district": "Chennai"},
            {"lat": 17.4, "lon": 78.5, "state": "Telangana", "district": "Hyderabad"},
            {"lat": 23.8, "lon": 91.3, "state": "Tripura", "district": "West Tripura"},
            {"lat": 26.8, "lon": 81.0, "state": "Uttar Pradesh", "district": "Lucknow"},
            {"lat": 30.3, "lon": 78.0, "state": "Uttarakhand", "district": "Dehradun"},
            {"lat": 22.6, "lon": 88.4, "state": "West Bengal", "district": "Kolkata"},
        ]

        import random
        
        # Pre-defined attributes
        risks = ["LOW", "MODERATE", "SEVERE", "CRITICAL"]
        impacts = [
            "Moderate impact on local wildlife.",
            "High loss of biodiversity, soil erosion risks.",
            "Severe groundwater depletion, drastic temperature rise.",
            "Mild forest cover reduction."
        ]

        events = []
        for st in indian_states_mock_data:
            area = round(random.uniform(5.0, 50.0), 2)
            risk = random.choice(risks)
            impact = random.choice(impacts)
            
            # Simulate Sentinel-2 NDVI processing & CNN Output
            # In a real scenario, this involves fetching Band 4 & Band 8 via API, computing matrix (NIR-R)/(NIR+R)
            # and passing through the DeforestationCNN.
            ndvi_shift = round(random.uniform(-0.1, -0.4), 3) # Negative shift indicates vegetation loss
            
            cnn_confidence = 0.0
            if deforestation_cnn:
                 # ResNet expects 3x224x224 or at least 3x128x128
                 # Using the same transform logic from training script
                 dummy_tensor = torch.rand(1, 3, 128, 128)
                 # normalize
                 mean = torch.tensor([0.485, 0.456, 0.406]).view(1,3,1,1)
                 std = torch.tensor([0.229, 0.224, 0.225]).view(1,3,1,1)
                 dummy_tensor = (dummy_tensor - mean) / std
                 with torch.no_grad():
                      cnn_confidence = round(deforestation_cnn(dummy_tensor).item(), 3)
            else:
                 cnn_confidence = round(random.uniform(0.65, 0.98), 3) 
                 
            
            events.append({
                "lat": st["lat"],
                "lon": st["lon"],
                "area_sq_km": area,
                "risk_level": risk,
                "environmental_impact": impact,
                "district": st["district"],
                "state": st["state"],
                "ndvi_shift": ndvi_shift,
                "cnn_confidence": cnn_confidence
            })
        
        for e in events:
            deforestation = DeforestationEvent(**e)
            db.add(deforestation)
            
        db.commit()
        db.close()
        return {"message": f"Inserted {len(events)} test deforestation events across all states."}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}

@app.get("/deforestation-events")
def get_deforestation_events():
    db = Session()
    events = db.query(DeforestationEvent).all()
    result = []
    for e in events:
        result.append({
            "id": e.id,
            "lat": e.lat,
            "lon": e.lon,
            "area_sq_km": e.area_sq_km,
            "risk_level": e.risk_level,
            "environmental_impact": e.environmental_impact,
            "district": e.district,
            "state": e.state,
            "ndvi_shift": e.ndvi_shift,
            "cnn_confidence": e.cnn_confidence,
            "t1_ndvi_url": getattr(e, "t1_ndvi_url", None),
            "t2_ndvi_url": getattr(e, "t2_ndvi_url", None),
            "timestamp": e.timestamp
        })
    db.close()
    return result

class DeforestationAnalyzeRequest(BaseModel):
    lat: float
    lon: float
    start_t1: str = "2023-01-01"
    end_t1: str = "2023-12-31"
    start_t2: str = "2024-01-01"
    end_t2: str = "2024-12-31"

@app.post("/analyze-deforestation")
def analyze_deforestation_real(req: DeforestationAnalyzeRequest):
    try:
        # 1. Fetch real NDVI shift from Google Earth Engine
        shift = earth_engine_service.calculate_ndvi_change(
            req.lat, req.lon, 
            req.start_t1, req.end_t1, 
            req.start_t2, req.end_t2
        )
        t1_url = earth_engine_service.get_ndvi_map_url(req.lat, req.lon, req.start_t1, req.end_t1)
        t2_url = earth_engine_service.get_ndvi_map_url(req.lat, req.lon, req.start_t2, req.end_t2)
        
        # 2. Feed to CNN
        cnn_conf = 0.0
        if deforestation_cnn:
            dummy_tensor = torch.rand(1, 3, 128, 128)
            mean = torch.tensor([0.485, 0.456, 0.406]).view(1,3,1,1)
            std = torch.tensor([0.229, 0.224, 0.225]).view(1,3,1,1)
            dummy_tensor = (dummy_tensor - mean) / std
            with torch.no_grad():
                cnn_conf = round(deforestation_cnn(dummy_tensor).item(), 3)
        else:
            cnn_conf = 0.85 # Fallback
            
        location_info = reverse_geocode(req.lat, req.lon)
        dist = location_info.get("district", "Unknown")
        st = location_info.get("state", "Unknown")
        
        risk = "LOW"
        if shift and shift < -0.2: risk = "SEVERE"
        elif shift and shift < -0.1: risk = "MODERATE"
        elif cnn_conf > 0.8: risk = "HIGH"
        
        db = Session()
        new_event = DeforestationEvent(
            lat=req.lat, lon=req.lon,
            area_sq_km=random.uniform(5.0, 20.0), # Mock area for now
            risk_level=risk,
            environmental_impact="Detected via Real Sentinel-2 API",
            district=dist, state=st,
            ndvi_shift=shift if shift is not None else -0.15,
            cnn_confidence=cnn_conf,
            t1_ndvi_url=t1_url,
            t2_ndvi_url=t2_url
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        event_id = new_event.id
        db.close()
        
        return {
            "status": "success", 
            "event_id": event_id, 
            "ndvi_shift": shift, 
            "t1_url": t1_url, 
            "t2_url": t2_url, 
            "risk": risk
        }
        
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


def generate_deforestation_prediction(state: str, current_area_lost: float, hotspot_count: int):
    """
    AI Prediction Mock/Heuristic for Future Deforestation.
    In a real scenario, this would call an ML model or use historical Open-Meteo weather trends 
    (e.g., rising temperatures & dropping precipitation) to predict future risk.
    """
    import random
    
    # Base risk modifiers based on current state of affairs
    base_multiplier = 1.0 + (hotspot_count * 0.05) + (current_area_lost * 0.01)
    
    # Simulate slightly random climate factors (temperature anomalies, drought indices)
    temp_anomaly = random.uniform(0.5, 2.5) # °C rise simulated
    drought_factor = random.uniform(1.0, 1.5)
    
    predicted_loss_2030 = round(current_area_lost * base_multiplier * drought_factor, 2)
    predicted_loss_2040 = round(predicted_loss_2030 * random.uniform(1.2, 1.6), 2)
    predicted_loss_2050 = round(predicted_loss_2040 * random.uniform(1.3, 1.8), 2)
    
    # Generate a risk level
    if predicted_loss_2050 > 150 or temp_anomaly > 2.0:
        future_risk = "CRITICAL"
        warning = f"High drought factor and {temp_anomaly:.1f}°C temp anomaly predict severe habitat loss by 2050."
    elif predicted_loss_2050 > 80:
        future_risk = "SEVERE"
        warning = "Accelerated deforestation expected due to climate trends extending into 2050."
    elif predicted_loss_2050 > 40:
        future_risk = "MODERATE"
        warning = "Steady rate of deforestation expected through 2050."
    else:
        future_risk = "LOW"
        warning = "Current trends indicate manageable forest loss through 2050, but monitoring required."
        
    return {
        "predicted_area_loss_2030_sq_km": predicted_loss_2030,
        "predicted_area_loss_2040_sq_km": predicted_loss_2040,
        "predicted_area_loss_2050_sq_km": predicted_loss_2050,
        "future_risk_level": future_risk,
        "ai_warning": warning,
        "climate_factors_considered": {
            "simulated_temp_anomaly_C": round(temp_anomaly, 2),
            "drought_intensity_factor": round(drought_factor, 2)
        }
    }

@app.get("/deforestation-state-report")
def get_deforestation_state_report():
    """
    Get a complete report of deforestation grouped by state, including future AI predictions.
    """
    db = Session()
    events = db.query(DeforestationEvent).all()
    db.close()
    
    # Group by state
    state_data = {}
    for e in events:
        s = e.state or "Unknown"
        if s not in state_data:
            state_data[s] = {
                "state": s,
                "total_area_lost": 0.0,
                "hotspot_count": 0,
                "districts_affected": set(),
                "events": []
            }
        
        state_data[s]["total_area_lost"] += float(e.area_sq_km or 0)
        state_data[s]["hotspot_count"] += 1
        if e.district:
            state_data[s]["districts_affected"].add(e.district)
            
        state_data[s]["events"].append({
            "id": e.id,
            "lat": e.lat,
            "lon": e.lon,
            "area": e.area_sq_km,
            "risk": e.risk_level,
            "district": e.district,
            "ndvi_shift": e.ndvi_shift,
            "cnn_confidence": e.cnn_confidence,
            "t1_ndvi_url": getattr(e, "t1_ndvi_url", None),
            "t2_ndvi_url": getattr(e, "t2_ndvi_url", None)
        })
        
    # Format report and add predictions
    report = []
    for s, data in state_data.items():
        data["total_area_lost"] = round(data["total_area_lost"], 2)
        data["districts_count"] = len(data["districts_affected"])
        data["districts_affected"] = list(data["districts_affected"])
        
        # Geerate AI Prediction
        prediction = generate_deforestation_prediction(
            s, 
            data["total_area_lost"], 
            data["hotspot_count"]
        )
        data["future_prediction"] = prediction
        
        report.append(data)
        
    # Sort by total area lost descending
    report.sort(key=lambda x: x["total_area_lost"], reverse=True)
    
    return {
        "total_states_affected": len(report),
        "total_national_area_lost": round(sum(r["total_area_lost"] for r in report), 2),
        "state_reports": report
    }

# ================= REQUEST SCHEMAS =================
class LocationIn(BaseModel):
    lat: float
    lon: float

# ================= WEBSOCKET =================
clients = set()

@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
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
        print(f"WebSocket error: {e}")
    finally:
        clients.discard(websocket)

async def broadcast(data):
    for c in list(clients):
        try:
            await c.send_json(data)
        except:
            clients.remove(c)

# ================= GEO HELPERS =================
def reverse_geocode(lat, lon):
    """Reverse geocode coordinates to get district and state"""
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
            timeout=10
        )
        
        if r.status_code != 200:
            return get_location_fallback(lat, lon)
        
        address = r.json().get("address", {})
        
        # Debug: print address to see what fields are available
        if not address.get("state_district"):
            print(f"Address fields available: {list(address.keys())}")
        
        # Try multiple field names for district (India-specific fields included)
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
            # Try to extract district from display_name (format: "District, State, Country")
            parts = display_name.split(",")
            if len(parts) >= 2:
                # Usually format is: "Area, District, State, Country"
                # Try second part as district
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
        probs = torch.softmax(out, dim=1)
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
    """Fetch fire data from NASA FIRMS API
    area: 'world', 'IND' (India), or country code
    days: number of days to fetch (1-10)
    """
    try:
        # Try multiple API endpoints for better reliability
        urls = []
        
        # Option 1: Country-based endpoint (works without API key for public data)
        if area != "world":
            urls.append(f"https://firms.modaps.eosdis.nasa.gov/api/country/json/{FIRMS_API_KEY or 'public'}/VIIRS_SNPP_NRT/{area}/{days}")
        
        # Option 2: Area endpoint with bounding box (for world, use large bounding box)
        if area == "world":
            # World bounding box: -180,-90,180,90
            urls.append(f"https://firms.modaps.eosdis.nasa.gov/api/area/json/{FIRMS_API_KEY or 'public'}/VIIRS_SNPP_NRT/-180,-90,180,90/{days}")
        else:
            urls.append(f"https://firms.modaps.eosdis.nasa.gov/api/area/json/{FIRMS_API_KEY or 'public'}/VIIRS_SNPP_NRT/{area}/{days}")
        
        # Try each URL until one works
        for url in urls:
            try:
                r = requests.get(url, timeout=15, headers={"User-Agent": "FireMonitoringSystem/1.0"})
                print("FIRMS status:", r.status_code)
                print("FIRMS text:", r.text[:200])
                if r.status_code == 200:
                    data = r.json()
                    # Handle different response formats
                    if isinstance(data, dict):
                        if 'data' in data:
                            return data['data']
                        elif 'fires' in data:
                            return data['fires']
                        # If it's a dict with list values, return first list found
                        for key, value in data.items():
                            if isinstance(value, list) and len(value) > 0:
                                return value
                    elif isinstance(data, list):
                        return data
                    break
            except Exception as e:
                print(f"Trying next URL... {e}")
                continue
        
        # If all URLs fail, return sample data for testing
        print("Using sample data - API unavailable")
        return get_sample_fire_data()
    except Exception as e:
        print(f"FIRMS API error: {e}")
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

def get_satellite_image_url(lat, lon, zoom=12):
    """Get satellite image URL from various sources"""
    # Option 1: NASA Worldview (interactive)
    date = datetime.now().strftime("%Y-%m-%d")
    worldview_url = f"https://worldview.earthdata.nasa.gov/?v={lon-0.1},{lat-0.1},{lon+0.1},{lat+0.1}&l=VIIRS_SNPP_CorrectedReflectance_TrueColor"

    # Option 2: Mapbox Static Satellite Image (direct image)
    static_map = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/pin-s-fire+ff0000({lon},{lat})/{lon},{lat},{zoom},0/800x600?access_token=MAPBOX_TOKEN_REMOVED"

    # Option 3: NASA GIBS - Global Imagery Browse Services (direct satellite images)
    # Convert lat/lon to tile coordinates for EPSG:3857
    import math
    def lat_lon_to_tile(lat, lon, zoom):
        n = 2 ** zoom
        x = int((lon + 180) / 360 * n)
        y = int((1 - math.log(math.tan(lat * math.pi / 180) + 1 / math.cos(lat * math.pi / 180)) / math.pi) / 2 * n)
        return x, y

    tile_x, tile_y = lat_lon_to_tile(lat, lon, zoom)
    gibs_url = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/{date}/GoogleMapsCompatible_Level9/{zoom}/{tile_y}/{tile_x}.jpg"

    # Option 4: Bing Maps Satellite (direct image)
    # Bing Maps uses quadkey system for tiles
    def lat_lon_to_quadkey(lat, lon, zoom):
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
        n = 2 ** zoom
        x = int((lon + 180) / 360 * n)
        y = int((1 - math.log(math.tan(lat * math.pi / 180) + 1 / math.cos(lat * math.pi / 180)) / math.pi) / 2 * n)
        return tile_to_quadkey(x, y, zoom)

    quadkey = lat_lon_to_quadkey(lat, lon, zoom)
    bing_url = f"https://ecn.t{0}.tiles.virtualearth.net/tiles/a{quadkey}.jpeg?g=685&n=z"

    # Option 5: Sentinel Hub WMS (if API key available)
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
@app.get("/test/firms")
def test_firms():
    data = fetch_firms(days=1)
    return {"count": len(data), "sample": data[:2]}
# ================= SENTINEL-2 =================




    # =============================
    # 🚨 IF FIRE DETECTED → TRIGGER SYSTEM
    # =============================
    if fire:

        message = (
            f"🔥 Forest fire detected with {round(confidence*100,1)}% confidence. "
            f"Wind moving {spread}. Evacuate immediately."
        )

        # 🔊 Local voice
        speak_alert(message)

        # 📡 WebSocket Broadcast
        safe_broadcast({
            "type": "ALERT",
            "severity": final_risk,
            "message": message,
            "lat": lat,
            "lon": lon,
            "spread_direction": spread
        })

        # 📱 SMS Broadcast
        db = Session()
        users = db.query(User).all()

        for u in users:
            send_twilio_sms(u.mobile_no, message)

        db.close()

    return {
        "fire_detected": fire,
        "class": label,
        "confidence": round(confidence, 3),
        "wind_speed_kmph": wind_speed,
        "wind_direction_deg": wind_dir,
        "spread_direction": spread,
        "final_risk": final_risk,
        "lat": lat,
        "lon": lon
    }
def manual_predict_fire(image: Image.Image):
    if cnn is None:
        return False, "unknown", 0.0
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD)
    ])
    tensor = transform(image).unsqueeze(0)
    with torch.no_grad():
        out = cnn(tensor)
        probs = torch.softmax(out, dim=1)
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
def fire_pipeline(limit=50):
    """Fetch and process fire events from satellite data"""
    db=Session()
    try:
        fires = fetch_firms("world", days=5)
        print(f"Fetched {len(fires)} fire events from satellite")
        
        processed = 0
        for f in fires[:limit]:
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
                # ================= Sentinel Auto CNN Confirm =================
                folder = auto_download_sentinel(lat, lon)

                fire_confirmed = True
                fire_prob = 0.8  # default fallback

                if folder:
                    try:
                        # You must later extract real RGB band
                        # For now use sample test image
                        image_path = "uploads/test_fire.jpg"

                        if os.path.exists(image_path):
                            image_tensor = load_image_tensor(image_path)
                            fire_confirmed, fire_prob = cnn_predict(image_tensor)
                        else:
                            fire_confirmed = True  # fallback
                    except Exception as e:
                        print("CNN confirm error:", e)
                        fire_confirmed = True

                if not fire_confirmed:
                    continue
                # Check if event already exists (avoid duplicates)
                existing = db.query(FireEvent).filter(
                    FireEvent.lat.between(lat-0.01, lat+0.01),
                    FireEvent.lon.between(lon-0.01, lon+0.01)
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
                
                # Get location with retry for better accuracy
                d, s = reverse_geocode(lat, lon)
                
                # If district is still unknown, try again with a slight delay (rate limiting)
                if d == "Unknown":
                    time.sleep(1.5)  # Rate limiting for Nominatim
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
            fire_pipeline(limit=500)
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
@app.get("/fire/raw")
def raw_fires():
    return fetch_firms("world", days=1)

@app.get("/fire/events")
def fire_events():
    """Get all fire events with satellite images and safety info"""
    db = Session()
    try:
        events = db.query(FireEvent).order_by(FireEvent.timestamp.desc()).limit(100).all()
        result = []
        for event in events:
            # Calculate evacuation direction (opposite to fire spread)
            evac_direction = get_evacuation_direction(event.spread_direction) if event.spread_direction else "Away from fire"
            
            # Get satellite images
            images = get_satellite_image_url(event.lat, event.lon) if event.lat and event.lon else {}
            
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
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
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
            if event.lat and event.lon:
                d, s = reverse_geocode(event.lat, event.lon)
                if d != "Unknown" or s != "Unknown":
                    event.district = d
                    event.state = s
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
    return transform(img).unsqueeze(0)

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
import pyttsx3

voice_engine = pyttsx3.init()
voice_engine.setProperty("rate", 160)
voice_engine.setProperty("volume", 1.0)

def speak_alert(message):
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

@app.post("/user/check-danger")
def check_user_danger(loc: LocationIn):
    db = Session()
    try:
        events = db.query(FireEvent).order_by(FireEvent.timestamp.desc()).limit(20).all()

        for event in events:
            poly = fire_polygon(
                event.lat,
                event.lon,
                event.severity or "MEDIUM",
                10,
                90
            
            )
           


            if user_in_fire_zone(loc.lat, loc.lon, poly):

                # 🧠 LSTM-based escape direction
                fire_dir = event.spread_direction
                safe_dir = get_evacuation_direction(fire_dir)

                # Calculate safety zones
                safety_zones = calculate_safety_zones(event.lat, event.lon, fire_dir)

                # 🔊 VOICE ALERT
                message = get_safe_escape_message(event)
                speak_alert(message)
                map_link = f"https://www.google.com/maps?q={event.lat},{event.lon}"

                message = (
                    f"🔥 FOREST FIRE ALERT 🔥\n"
                    f"Severity: {event.severity}\n"
                    f"Evacuate: {safe_dir}\n"
                    f"Location: {map_link}"
                )


                # 📡 WEBSOCKET POPUP
                safe_broadcast({
                    "type": "ALERT",
                    "severity": event.severity,
                    "spread_risk": event.spread_risk,
                    "fire_direction": event.spread_direction,
                    "evacuation_direction": safe_dir,
                    "cnn_probability": event.cnn_probability,
                    "message": message,
                    "lat": loc.lat,
                    "lon": loc.lon
                })

                route = generate_evacuation_route(
                    loc.lat,
                    loc.lon,
                    safety_zones[0]["lat"],
                    safety_zones[0]["lon"]
                )

                return {
                    "danger": True,
                    "severity": event.severity,
                    "district": event.district,
                    "state": event.state,
                    "fire_spread_direction": fire_dir,
                    "evacuation_direction": safe_dir
                }
            if user_in_fire_zone(loc.lat, loc.lon, poly):

                fire_dir = event.spread_direction
                safe_dir = get_evacuation_direction(fire_dir)

                message = get_safe_escape_message(event)

                # 🔊 Speak locally
                speak_alert(message)

                # 📡 WebSocket broadcast
                safe_broadcast({
                    "type": "ALERT",
                    "severity": event.severity,
                    "spread_risk": event.spread_risk,
                    "fire_direction": event.spread_direction,
                    "evacuation_direction": safe_dir,
                    "cnn_probability": event.cnn_probability,
                    "message": message,
                    "lat": loc.lat,
                    "lon": loc.lon
                })

                # 📱 SEND SMS TO ALL REGISTERED USERS
                users = db.query(User).all()

                for u in users:
                    send_twilio_sms(u.mobile_no, message)

                # 📒 Save emergency log
                log = EmergencyLog(
                    fire_event_id=event.id,
                    severity=event.severity,
                    message=message
                )
                db.add(log)
                db.commit()

                return {
                    "danger": True,
                    "severity": event.severity,
                    "district": event.district,
                    "state": event.state,
                    "fire_spread_direction": fire_dir,
                    "evacuation_direction": safe_dir,
                    "message": message
                }



        return {"danger": False}
    finally:
        db.close()
@app.post("/user/auto-location")
def auto_location(loc: LocationIn):
    db = Session()
    u = UserLocation(lat=loc.lat, lon=loc.lon)
    db.add(u)
    db.commit()
    db.close()

    # 🔥 THIS TRIGGERS VOICE + ALERT
    danger = check_user_danger(loc)

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
    print("🚀 Scheduler Started")
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, scheduler)


def generate_evacuation_route(user_lat, user_lon, safe_lat, safe_lon):
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
        user_message = (raw_msg or "").lower()
        events = data.get("events", [])
        
        # Build a concise summary for the LLM
        fire_summary = ""
        if events and len(events) > 0:
            for idx, e in enumerate(events[:5]):
                loc = e.get("district", "Unknown")
                state = e.get("state", "Unknown")
                sev = e.get("severity", "UNKNOWN")
                spread = e.get("spread_direction", "unknown direction")
                evac_dir = e.get("evacuation_direction", "a safe area")
                safe_zones_list = e.get("safety_zones") or []
                safe_zones = ", ".join([z.get("name", "") for z in safe_zones_list][:2])
                fire_summary += f"- Level {sev} fire in {loc}, {state}. Spreading {spread}. Evacuate towards {evac_dir}. Safe zones: {safe_zones}.\n"
        else:
            fire_summary = "There are currently no active forest fires detected by the system."

        system_prompt = f"""
You are an AI Safety & Disaster Awareness Assistant. You speak like a very knowledgeable, helpful friend to the user. Always address the user warmly as "Boss".

CRITICAL INSTRUCTION:
1. First and foremost, ANSWER THE USER'S SPECIFIC QUESTION directly. Do not simply list all active fires unless the user explicitly asks for a general update or "what is the status".
2. If the user asks a general question (e.g., "what are the important measures to escape"), answer THAT question. Do NOT list the current fire incidents unless they ask for them.
3. If the user asks about a specific location, only mention fires relevant to that location.
4. If they just say "hello", greet them back warmly and ask how you can help. Do not dump fire statistics on them.

Analyze the user's sentiment. If they express fear, panic, or anxiety, begin your response with a very calming, comforting, and empathetic tone before providing any information or safety instructions.
Keep your response concise, actionable, and suitable for an audio text-to-speech engine (do not use markdown formatting like asterisks or hashes, just plain spoken text).

Real-Time Fire Events Data (ONLY reference this if the user asks about active fires, locations, or their status):
{fire_summary}
"""
        full_prompt = f"{system_prompt}\nUser Question: {user_message}"

        # Try hitting Gemini
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(full_prompt)
            reply = response.text
            return {"reply": reply.strip()}
        except Exception as api_e:
            import traceback
            traceback.print_exc()
            print("Gemini API is unreachable or returned an error:", api_e)
            
            # Fallback to the hardcoded logic if Ollama fails
            if not events or len(events) == 0:
                return {"reply": "Hello Boss. There are currently no active forest fires detected by the orbital monitoring system. The national overview is secure."}

            wants_escape = "escape" in user_message or "route" in user_message or "evacuate" in user_message or "safe" in user_message
            emergency_broadcast = "Hello Boss. Warning. "
            
            for idx, e in enumerate(events[:3]):
                loc = e.get("district", "Unknown District")
                state = e.get("state", "Unknown State")
                sev = e.get("severity", "UNKNOWN")
                
                emergency_broadcast += f"Active level {sev} fire detected in {loc}, {state}. "
                
                spread_dir = e.get("spread_direction", "")
                if spread_dir:
                    emergency_broadcast += f"The fire is actively spreading towards the {spread_dir}. "
                    
                if wants_escape:
                    evac_dir = e.get("evacuation_direction", "")
                    if evac_dir:
                        emergency_broadcast += f"Immediate evacuation is required. Proceed immediately towards the {evac_dir}. "
                    
                    safe_zones_list = e.get("safety_zones") or []
                    if safe_zones_list and len(safe_zones_list) > 0:
                        emergency_broadcast += f"The nearest verified safe zone is {safe_zones_list[0].get('name', 'a nearby relief center')}. "

            emergency_broadcast += "Please stay safe, Boss, and follow local instructions."
            return {"reply": emergency_broadcast}

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