import os
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

print("1. Loading dotenv")
load_dotenv()

print("2. getting creds")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "satellite_fire_db")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
from urllib.parse import quote_plus
DB_PASSWORD = quote_plus(DB_PASSWORD)

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
print(f"3. Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}")

engine = create_engine(DATABASE_URL)
try:
    with engine.begin() as conn:
        print("4. Executing ALTER TABLE 1")
        conn.execute(text("ALTER TABLE deforestation_events ADD COLUMN t1_ndvi_url VARCHAR(500) NULL"))
        print("t1_ndvi_url added")
except Exception as e:
    print("Error 1:", e)
    
try:
    with engine.begin() as conn:
        print("5. Executing ALTER TABLE 2")
        conn.execute(text("ALTER TABLE deforestation_events ADD COLUMN t2_ndvi_url VARCHAR(500) NULL"))
        print("t2_ndvi_url added")
except Exception as e:
    print("Error 2:", e)

print("Done")
