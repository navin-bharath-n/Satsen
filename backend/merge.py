import sys

def main():
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()

        old_str = """@app.post("/fire/manual-trigger")
def manual_trigger(data: dict):
    db = Session()

    lat = data.get("lat")
    lon = data.get("lon")
    severity = data.get("severity")
    confidence = data.get("confidence")
    spread_direction = data.get("spread_direction")

    # Save fire event
    fire = FireEvent(
        lat=lat,
        lon=lon,
        severity=severity,
        spread_risk="HIGH",
        spread_direction=spread_direction,
        cnn_probability=confidence,
        district="Manual Upload",
        state="User Area"
    )

    db.add(fire)
    db.commit()

    message = f"🔥 Fire detected! Evacuate immediately."

    # WebSocket broadcast
    safe_broadcast({
        "type": "ALERT",
        "severity": severity,
        "lat": lat,
        "lon": lon,
        "message": message
    })

    db.close()

    return {
        "lat": lat,
        "lon": lon,
        "severity": severity,
        "confidence": confidence,
        "spread_direction": spread_direction,
        "message": message
    }
from pydantic import BaseModel

class ManualFireTrigger(BaseModel):
    lat: float
    lon: float
    severity: str
    spread_direction: str


@app.post("/fire/manual-trigger")
def manual_trigger(data: ManualFireTrigger):

    message = (
        f"🔥 Manual fire detected. "
        f"Severity {data.severity}. "
        f"Evacuate towards safe direction."
    )

    # 📱 SEND SMS TO ALL REGISTERED USERS
    db = Session()
    try:
        users = db.query(User).all()

        for u in users:
            send_twilio_sms(u.mobile_no, message)
    finally:
        db.close()

    safe_broadcast({
        "type": "ALERT",
        "severity": data.severity,
        "spread_direction": data.spread_direction,
        "evacuation_direction": get_evacuation_direction(data.spread_direction),
        "lat": data.lat,
        "lon": data.lon,
        "message": message
    })

    return {"status": "alert broadcasted"}"""

        new_str = """@app.post("/fire/manual-trigger")
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
from pydantic import BaseModel"""

        if old_str in content:
            content = content.replace(old_str, new_str)
            with open('app.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("Successfully updated app.py")
        else:
            print("Failed to find the string to replace.")

    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    main()
