import requests
import time
import json

BASE_URL = "http://localhost:5000"

def test_config_api():
    session = requests.Session()
    
    # 1. Login as Admin
    print("Logging in as admin...")
    login_url = f"{BASE_URL}/auth/login"
    payload = {'username': 'admin', 'password': 'admin123'}
    r = session.post(login_url, data=payload)
    if r.status_code != 200:
        print(f"Login failed: {r.status_code}")
        return

    # 2. Test GET Templates
    print("\nFetching Templates...")
    r = session.get(f"{BASE_URL}/api/config/templates")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        templates = r.json()
        print(f"Found {len(templates)} templates.")
        if len(templates) > 0:
            print(f"Sample: {templates[0]['name']}")
    else:
        print(f"Error: {r.text}")

    # 3. Test GET Assets
    print("\nFetching Assets...")
    r = session.get(f"{BASE_URL}/api/config/assets")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        assets = r.json()
        print(f"Found {len(assets)} assets.")
        if len(assets) > 0:
            print(f"Sample: {assets[0]['name']}")
    else:
        print(f"Error: {r.text}")
        
    # 4. Test GET Locations
    print("\nFetching Locations...")
    r = session.get(f"{BASE_URL}/api/config/locations")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        locations = r.json()
        print(f"Found {len(locations)} locations.")
    else:
        print(f"Error: {r.text}")

if __name__ == "__main__":
    test_config_api()
