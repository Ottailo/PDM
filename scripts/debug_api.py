import requests
import json
import sys

try:
    response = requests.get('http://127.0.0.1:5000/api/latest-states')
    data = response.json()
    
    print(f"API Status Code: {response.status_code}")
    print(f"Is Operational: {data.get('is_operational')}")
    
    predictions = data.get('predictions', {})
    print(f"Machines in predictions: {list(predictions.keys())}")
    
    if 'BOXING_001' in predictions:
        box = predictions['BOXING_001']
        print("\n--- BOXING_001 Data ---")
        print(f"State: {box.get('state')}")
        print(f"Sensor Data Keys: {list(box.get('sensor_data', {}).keys())}")
        
        sensor_data = box.get('sensor_data', {})
        if sensor_data:
            first_key = list(sensor_data.keys())[0]
            print(f"Sample data for {first_key}: {sensor_data[first_key][:5]} (len: {len(sensor_data[first_key])})")
        else:
            print("SENSOR DATA IS EMPTY")
            
        print(f"Sensor Readings: {box.get('sensor_readings')}")
    else:
        print("BOXING_001 not found in predictions")
        
except Exception as e:
    print(f"Error: {e}")
