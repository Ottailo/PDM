import requests
import time
import json

URL = "http://localhost:5000/api/latest-states"
# Need to login first or use API key if available.
# The endpoint requires @login_required.
# I'll try to use a session.

def test_api():
    session = requests.Session()
    
    # Login
    login_url = "http://localhost:5000/auth/login"
    print(f"Logging in to {login_url}...")
    try:
        # CSRF token might be needed? Flask-WTF usually requires it.
        # But let's try simple post first.
        # If it fails, I might need to fetch the login page first to get CSRF token.
        
        # Fetch login page first
        r = session.get(login_url)
        if r.status_code != 200:
            print(f"Failed to get login page: {r.status_code}")
            return

        # Assuming standard flask login without strict CSRF for now or trying to parse it
        # If this fails, I'll need to use a more complex script or just check if I can hit a public endpoint.
        # But /api/latest-states is protected.
        
        # Try to login
        payload = {'username': 'admin', 'password': 'admin123'}
        r = session.post(login_url, data=payload)
        print(f"Login status: {r.status_code}")
        
        # Now hit the API
        print(f"Requesting {URL}...")
        start = time.time()
        r = session.get(URL)
        duration = time.time() - start
        
        print(f"Status: {r.status_code}")
        print(f"Duration: {duration:.4f}s")
        
        if r.status_code == 200:
            try:
                data = r.json()
                print("Response JSON keys:", data.keys())
                print("Predictions count:", len(data.get('predictions', {})))
            except:
                print("Response is not JSON:", r.text[:200])
        else:
            print("Error response:", r.text[:200])
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_api()
