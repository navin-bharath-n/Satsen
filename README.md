# 🛰️ SatSen — AI-Powered Satellite Fire Monitoring System

A real-time forest fire detection and alert platform using satellite imagery, machine learning, and live weather data.

---

## 🚀 Features

- 🔥 **Real-time fire detection** via NASA FIRMS satellite API
- 🛰️ **Sentinel-2 satellite image** auto-download & CNN confirmation
- 🧠 **LSTM spread prediction** with wind + humidity inputs
- 🌿 **Deforestation detection** via ResNet50
- 📡 **WebSocket live alerts** for users in danger zones
- 🗺️ **Evacuation route generation** with safe zone mapping
- 🤖 **Gemini AI chatbot** for disaster awareness Q&A
- 📱 **Twilio SMS alerts** to registered users

---

## 🗂️ Project Structure

```
SatSen/
├── backend/          # FastAPI Python server
│   ├── app.py        # Main API server
│   ├── cnn.py        # CNN fire classifier
│   ├── earth_engine_service.py
│   ├── requirements.txt
│   └── .env.example  # Environment variable template
└── frontend/         # React + Vite frontend
    ├── src/
    ├── public/
    └── package.json
```

---

## ⚙️ Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/macOS

pip install -r requirements.txt

# Copy and fill in environment variables
copy .env.example .env

# Run the server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 🔑 Environment Variables

See `backend/.env.example` for a full list. Required keys:

| Variable | Description |
|----------|-------------|
| `FIRMS_API_KEY` | NASA FIRMS satellite fire data |
| `GEMINI_API_KEY` | Google Gemini AI chatbot |
| `COPERNICUS_USER/PASS` | Sentinel-2 image access |
| `DB_*` | MySQL database credentials |
| `TWILIO_*` | SMS alert credentials |
| `ORS_API_KEY` | Evacuation route generation |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Server health check |
| GET | `/fire/events` | All detected fire events |
| POST | `/fire/fetch` | Trigger satellite data pull |
| POST | `/fire/predict-spread` | LSTM spread prediction |
| POST | `/fire/manual-trigger` | Manually log a fire |
| POST | `/user/check-danger` | Check if user location is in fire zone |
| POST | `/openai-disaster-chat` | AI chatbot Q&A |
| WS | `/ws` | Live WebSocket alerts |

---

## 🛠️ Tech Stack

**Backend:** FastAPI · SQLAlchemy · PyTorch · Sentinel API · FIRMS · Open-Meteo · Twilio · Gemini AI  
**Frontend:** React · Vite · Leaflet.js

---

## ⚠️ Notes

- Never commit `.env` — it contains API keys and DB credentials
- The `venv/` and `node_modules/` folders are excluded from git
- ML model weights in `/training` are excluded due to size
