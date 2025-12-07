"""
Test script for verifying Authentication and RBAC.
"""
import requests
import sys

BASE_URL = "http://localhost:5000"
SESSION = requests.Session()

def test_auth():
    print(f"Testing Auth at {BASE_URL}")
    
    # 1. Try accessing protected route without login
    print("\nTest 1: Access protected route (No Login)")
    resp = SESSION.get(f"{BASE_URL}/api/latest-states", allow_redirects=False)
    print(f"Status: {resp.status_code}")
    if resp.status_code in [401, 302]:
        print("✅ Passed (Redirected/Unauthorized)")
    else:
        print(f"❌ Failed (Got {resp.status_code})")
        
    # 2. Setup Admin (if not exists)
    print("\nTest 2: Setup Admin")
    resp = SESSION.get(f"{BASE_URL}/auth/setup-admin")
    print(f"Response: {resp.text}")
    
    # 3. Login as Admin
    print("\nTest 3: Login as Admin")
    resp = SESSION.post(f"{BASE_URL}/auth/login", data={
        "username": "admin",
        "password": "admin123"
    })
    print(f"Status: {resp.status_code}")
    # Check if we are redirected to index or dashboard
    if resp.url.endswith('/'):
        print("✅ Passed (Logged in)")
    else:
        print("❌ Failed to login")
        
    # 4. Access protected route (With Login)
    print("\nTest 4: Access protected route (Logged In)")
    resp = SESSION.get(f"{BASE_URL}/api/latest-states")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("✅ Passed")
    else:
        print(f"❌ Failed (Got {resp.status_code})")

    # 5. Test Logout
    print("\nTest 5: Logout")
    resp = SESSION.get(f"{BASE_URL}/auth/logout")
    print(f"Status: {resp.status_code}")
    
    # Verify we can't access anymore
    resp = SESSION.get(f"{BASE_URL}/api/latest-states", allow_redirects=False)
    if resp.status_code in [401, 302]:
        print("✅ Passed (Logout successful)")
    else:
        print("❌ Failed (Still logged in)")

if __name__ == "__main__":
    test_auth()
