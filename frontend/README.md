# Flood & Fire Monitoring System - Frontend

React-based frontend for the Flood & Fire Monitoring System.

## Prerequisites

1. **Node.js** (v18 or higher) - Download from: https://nodejs.org/
   - This will also install `npm` (Node Package Manager)

## Installation

1. Open a new terminal/command prompt
2. Navigate to the frontend directory:
   ```powershell
   cd "C:\Users\varad\Downloads\Telegram Desktop\satellite monitering\flood monitoring\frontend"
   ```

3. Install dependencies:
   ```powershell
   npm install
   ```

## Running the Frontend

After installing dependencies, run:

```powershell
npm run dev
```

The frontend will start on `http://localhost:3000`

## Features

- 🗺️ Interactive map showing fire event locations
- 📊 Real-time event list with severity indicators
- 🔄 WebSocket connection for live updates
- 📍 Detailed event information (location, severity, spread risk)
- 🎨 Modern, responsive UI

## Backend Connection

Make sure the backend server is running on `http://localhost:8000` before starting the frontend.

To start the backend:
```powershell
cd "C:\Users\varad\Downloads\Telegram Desktop\satellite monitering\flood monitoring\backend"
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── MapView.jsx      # Interactive map component
│   │   ├── EventList.jsx    # Event list sidebar
│   │   └── StatusBar.jsx    # Status indicators
│   ├── App.jsx              # Main application component
│   ├── App.css              # App styles
│   ├── main.jsx             # Entry point
│   └── index.css            # Global styles
├── index.html               # HTML template
├── package.json             # Dependencies
└── vite.config.js           # Vite configuration


