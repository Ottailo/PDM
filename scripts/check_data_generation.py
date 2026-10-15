import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.sensor_data import SensorData

app = create_app()

def check_data():
    with app.app_context():
        count_start = SensorData.query.count()
        print(f"Initial Count: {count_start}")
        
        time.sleep(5)
        
        count_end = SensorData.query.count()
        print(f"Final Count: {count_end}")
        
        if count_end > count_start:
            print("SUCCESS: Data is being generated.")
        else:
            print("FAILURE: No new data generated.")

if __name__ == "__main__":
    check_data()
