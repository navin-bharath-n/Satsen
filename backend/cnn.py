from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import requests
import math
import os

# ======================
# APP
# ======================
app = FastAPI(title="Satellite Fire CNN API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# CONFIG
# ======================
MODEL_PATH = "training/fire_cnn.pth"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CLASSES = ["nowildfire", "wildfire"]
FIRE_CONFIDENCE_THRESHOLD = 0.6

# ======================
# TRANSFORMS (IMAGENET)
# ======================
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# ======================
# MODEL
# ======================
model = models.resnet18(weights=None)
model.fc = nn.Linear(model.fc.in_features, 2)

if not os.path.exists(MODEL_PATH):
    raise RuntimeError("❌ fire_cnn.pth not found. Train model first.")

model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model.eval()
model.to(DEVICE)

print("🔥 CNN loaded successfully (2 classes)")

# ======================
# WIND API
# ======================
def get_wind(lat, lon):
    try:
        r = requests.get(
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=wind_speed_10m,wind_direction_10m",
            timeout=10
        )
        w = r.json()["current"]
        return w["wind_speed_10m"], w["wind_direction_10m"]
    except:
        return 5.0, 90.0

# ======================
# SPREAD DIRECTION
# ======================
def spread_direction(angle):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[int((angle + 22.5) // 45) % 8]

# ======================
# PREDICTION
# ======================
def predict_fire(image: Image.Image):
    tensor = transform(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        conf, idx = probs.max(dim=1)

    confidence = conf.item()
    label = CLASSES[idx.item()]

    fire_detected = label == "wildfire" and confidence >= FIRE_CONFIDENCE_THRESHOLD
    return fire_detected, label, confidence

# ======================
# ADMIN UPLOAD API
# ======================
@app.post("/admin/upload")
async def admin_upload(
    image: UploadFile = File(...),
    lat: float = Form(...),
    lon: float = Form(...)
):
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid image file")

    img = Image.open(image.file).convert("RGB")

    fire, label, confidence = predict_fire(img)

    wind_speed, wind_dir = get_wind(lat, lon)
    spread = spread_direction(wind_dir)

    return {
        "fire_detected": fire,
        "class": label,
        "confidence": round(confidence, 3),
        "wind_speed_kmph": wind_speed,
        "wind_direction_deg": wind_dir,
        "spread_direction": spread,
        "lat": lat,
        "lon": lon
    }

# ======================
# HEALTH CHECK
# ======================
@app.get("/")
def root():
    return {
        "status": "running",
        "cnn_loaded": True,
        "device": str(DEVICE)
    }
print("✅ FastAPI backend/cnn.py is running")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("cnn:app", host="0.0.0.0", port=8001, reload=True)

