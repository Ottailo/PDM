"""
Test script for verifying Database Connection.
"""
import os
import sys
from sqlalchemy import create_engine, text

# Default to the one in docker-compose
DB_URL = "postgresql://pdm_user:pdm_password@localhost:5432/pdm_db"

def test_db():
    print(f"Testing Database Connection to {DB_URL}")
    
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"Connection Successful! Result: {result.scalar()}")
            
            # Check if tables exist (basic check)
            result = conn.execute(text("SELECT to_regclass('public.sensor_data')"))
            table_exists = result.scalar()
            if table_exists:
                print("✅ Table 'sensor_data' exists.")
            else:
                print("⚠️ Table 'sensor_data' does not exist yet (Run migrations).")
                
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        print("Make sure Docker is running: docker-compose up -d")

if __name__ == "__main__":
    test_db()
