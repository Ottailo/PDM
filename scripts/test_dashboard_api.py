import sys
import os
import requests
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:5000"

def login():
    session = requests.Session()
    
    # Ensure admin exists
    try:
        session.get(f"{BASE_URL}/auth/setup-admin")
    except:
        pass

    response = session.post(f"{BASE_URL}/auth/login", data={
        "username": "admin",
        "password": "admin123" # Try admin123 as per auth.py setup_admin
    })
    
    # Check if we are redirected to dashboard (or at least NOT login page)
    if "Login" not in response.text and response.status_code == 200:
        print("Login successful")
        return session
    else:
        # Try 'admin' password just in case
        response = session.post(f"{BASE_URL}/auth/login", data={
            "username": "admin",
            "password": "admin"
        })
        if "Login" not in response.text and response.status_code == 200:
             print("Login successful (password: admin)")
             return session
             
        print(f"Login failed. URL: {response.url}")
        return None

def test_latest_states(session):
    print("\nTesting /api/latest-states...")
    response = session.get(f"{BASE_URL}/api/latest-states")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print("Success!")
            print(f"Operational: {data.get('is_operational')}")
            print(f"KPIs: {json.dumps(data.get('kpis'), indent=2)}")
            
            predictions = data.get('predictions', {})
            print(f"Predictions count: {len(predictions)}")
            
            if predictions:
                first_key = list(predictions.keys())[0]
                print(f"Sample prediction for {first_key}:")
                # print(json.dumps(predictions[first_key], indent=2))
                
                # Verify structure
                pred = predictions[first_key]
                if 'sensor_info' in pred and 'thresholds' in pred:
                    print(" - Sensor Info present")
                    print(" - Thresholds present")
                else:
                    print(" - WARNING: Missing sensor info or thresholds")
        except json.JSONDecodeError:
            print(f"Failed to decode JSON. Response text:\n{response.text}")
    else:
        print(f"Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    session = login()
    if session:
        test_latest_states(session)
