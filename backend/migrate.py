import os
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD") or "")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL)

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE deforestation_events ADD COLUMN t1_ndvi_url VARCHAR(500) NULL"))
        print("Added t1_ndvi_url")
except Exception as e:
    print(f"Failed to add t1_ndvi_url: {e}")
    
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE deforestation_events ADD COLUMN t2_ndvi_url VARCHAR(500) NULL"))
        print("Added t2_ndvi_url")
except Exception as e:
    print(f"Failed to add t2_ndvi_url: {e}")
