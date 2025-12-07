"""
Test script for verifying the Ingestion API.
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000/api/ingest"
API_KEY = "dev-api-key"

def test_ingest():
    print(f"Testing Ingestion API at {BASE_URL}")
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    
    # Test Case 1: Valid Data
    payload = {
        "machine_id": "FILLING_001",
        "timestamp": datetime.utcnow().isoformat(),
        "sensors": {
            "Fill_Volume_Sensor": 99.5,
            "Nozzle_Pressure": 2.2,
            "Vibration": 0.1
        }
    }
    
    try:
        response = requests.post(BASE_URL, headers=headers, json=payload)
        print(f"Test 1 (Valid Data): Status {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Test 1 Passed")
        else:
            print("❌ Test 1 Failed")
            
    except Exception as e:
        print(f"❌ Test 1 Error: {e}")

    # Test Case 2: Invalid API Key
    try:
        bad_headers = headers.copy()
        bad_headers["X-API-Key"] = "wrong-key"
        response = requests.post(BASE_URL, headers=bad_headers, json=payload)
        print(f"\nTest 2 (Invalid Key): Status {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Test 2 Passed")
        else:
            print("❌ Test 2 Failed")
    except Exception as e:
        print(f"❌ Test 2 Error: {e}")

    # Test Case 3: Unknown Machine
    try:
        bad_payload = payload.copy()
        bad_payload["machine_id"] = "UNKNOWN_999"
        response = requests.post(BASE_URL, headers=headers, json=bad_payload)
        print(f"\nTest 3 (Unknown Machine): Status {response.status_code}")
        
        if response.status_code == 400:
            print("✅ Test 3 Passed")
        else:
            print("❌ Test 3 Failed")
    except Exception as e:
        print(f"❌ Test 3 Error: {e}")

if __name__ == "__main__":
    test_ingest()
