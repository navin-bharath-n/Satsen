import sys
from sqlalchemy import text
from app import engine

print("Connecting to database...")
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE deforestation_events ADD COLUMN t1_ndvi_url VARCHAR(500) NULL"))
        print("Added t1_ndvi_url")
except Exception as e:
    print(f"Failed t1: {e}")

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE deforestation_events ADD COLUMN t2_ndvi_url VARCHAR(500) NULL"))
        print("Added t2_ndvi_url")
except Exception as e:
    print(f"Failed t2: {e}")

print("Done.")
