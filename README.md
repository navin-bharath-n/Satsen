# 🛰️ SatSen — AI-Powered Satellite Monitoring System

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React_18-61DAFB.svg?style=flat&logo=react)](https://react.dev/)
[![PyTorch](https://img.shields.io/badge/Deep%20Learning-PyTorch-EE4C2C.svg?style=flat&logo=pytorch)](https://pytorch.org/)
[![Vite](https://img.shields.io/badge/Bundler-Vite-646CFF.svg?style=flat&logo=vite)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**SatSen** is a full-stack, real-time satellite monitoring and disaster intelligence platform. It fuses NASA FIRMS data, ESA Sentinel-2 multispectral imagery, Google Earth Engine (GEE), and deep learning models (Hybrid CNN + LSTM) to detect, predict, and monitor **wildfires** and **deforestation** events across geographical regions.

---

## 🌟 Key Features

- 🔥 **Real-Time Wildfire Detection & Monitoring**:
  - Live ingestion from NASA FIRMS (MODIS / VIIRS).
  - Open-Meteo weather integration (wind speed, wind direction, temperature, humidity) for dynamic fire spread forecasting.
  - Custom LSTM & CNN neural network architectures for fire severity and progression modeling.
  
- 🌲 **Hybrid Deforestation Detection**:
  - 4-channel Deep CNN (ResNet-18 backbone) accepting multitemporal NDVI shift layers ($T_1$, $T_2$, Edge, Infrared) via Google Earth Engine.
  - Automated forest loss risk scoring and spatial clustering.

- 🗺️ **Interactive Geospatial Dashboard**:
  - Interactive Leaflet map with satellite tiles, thermal heatmaps, cluster markers, and fire boundary overlays.
  - 3D Globe visualization powered by Three.js and `@react-three/fiber`.
  - District and state-level situational analytics and charts (Recharts).

- 🚨 **Emergency Control & Automated Alerts**:
  - Real-time WebSocket broadcasting of critical incidents.
  - Automated SMS emergency alerts and evacuation guidance via Twilio.
  - Interactive evacuation route recommendation based on wind spread vector analysis.

- 🤖 **AI Disaster Intelligence Assistant**:
  - Conversational disaster assistant powered by Google Gemini / OpenAI for real-time situational reporting and emergency instructions.

---

## 🏗️ Architecture & Tech Stack

```
SatSen/
├── backend/                  # FastAPI Python Backend
│   ├── app.py                # Core REST & WebSocket API server
│   ├── cnn.py                # CNN model architecture definitions
│   ├── earth_engine_service.py # Google Earth Engine integration
│   ├── train_hybrid_cnn.py   # Hybrid Deforestation 4-channel CNN training
│   ├── training/             # LSTM & CNN training scripts and pipelines
│   └── requirements.txt      # Python dependencies
└── frontend/                 # React + Vite Frontend
    ├── src/
    │   ├── components/       # MapView, EventList, AIAssistant, DeforestationPanel, etc.
    │   ├── pages/            # Dashboard, ControlCenter, EmergencyControl, GlobePage, etc.
    │   └── styles/           # Design system tokens and animations
    └── package.json          # Node dependencies
```

### Technologies

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.12, FastAPI, Uvicorn, SQLAlchemy, PyMySQL, WebSockets |
| **Machine Learning** | PyTorch, Torchvision, NumPy, Pandas, Scikit-learn |
| **Geospatial & Remote Sensing** | Google Earth Engine API, GeoPandas, Shapely, Rasterio, SentinelSat |
| **Frontend** | React 18, Vite, Three.js, React-Three-Fiber, Leaflet, React-Leaflet, Framer Motion, Recharts |
| **Database** | MySQL 8.x / MariaDB |
| **External APIs** | NASA FIRMS, Open-Meteo, Twilio SMS, Google Gemini / OpenAI |

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** (v18 or higher) and **npm**
- **Python** (v3.10 – 3.12 recommended)
- **MySQL Server** (v8.0+ running locally or remotely)

---

### 1. Backend Setup

1. Open terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your `.env` configuration file in the `backend/` directory:
   ```env
   # MySQL Database Configuration
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=satellite_fire_db
   DB_USER=root
   DB_PASSWORD=your_mysql_password_here

   # NASA FIRMS API (Optional)
   FIRMS_API_KEY=your_firms_api_key

   # Google Gemini AI (Optional)
   GEMINI_API_KEY=your_gemini_api_key

   # Twilio SMS Alerts (Optional)
   TWILIO_SID=your_twilio_sid
   TWILIO_AUTH=your_twilio_auth_token
   TWILIO_PHONE=+1xxxxxxxxxx

   # Mapbox Token (Optional)
   MAPBOX_TOKEN=pk.your_mapbox_token
   ```

5. Ensure MySQL is running and create the database:
   ```sql
   CREATE DATABASE IF NOT EXISTS satellite_fire_db;
   ```

6. Start the backend development server:
   ```bash
   uvicorn app:app --reload --host 127.0.0.1 --port 8000
   ```
   - Swagger API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 2. Frontend Setup

1. In a separate terminal, navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

4. Open your browser at [http://localhost:3000](http://localhost:3000)

---

## 📡 API Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | API status and health check |
| `GET` | `/fire_events` | Fetch all detected fire events and severity metrics |
| `POST` | `/fire_events/manual` | Manually report or upload a fire event |
| `GET` | `/deforestation/events` | List identified deforestation hotspot alerts |
| `POST` | `/auth/register` | Register an administrative / emergency contact user |
| `POST` | `/auth/login` | Authenticate user and generate JWT access token |
| `POST` | `/ai/chat` | Disaster AI assistant query endpoint |
| `WS` | `/ws` | Real-time WebSocket feed for live hotspot telemetry |

---

## 🧪 Model Training & Datasets

To train or initialize model weights:

- **Hybrid Deforestation CNN**:
  ```bash
  python backend/train_hybrid_cnn.py
  ```
- **Fire Spread LSTM / CNN**:
  ```bash
  python backend/training/train_lstm.py
  python backend/training/train_cnn_real.py
  ```

---

## 🛡️ License

This project is licensed under the [MIT License](LICENSE).
