"""
Test authentication endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_login(username, password):
    """Test login endpoint"""
    print(f"\n🔑 Testing login for user: {username}")
    
    try:
        # Test login
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"✅ Login successful!")
            print(f"Token: {token_data.get('access_token', 'N/A')}")
            return token_data.get('access_token')
        else:
            print(f"❌ Login failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_protected_endpoint(token):
    """Test accessing protected endpoint"""
    print(f"\n🛡️ Testing protected endpoint with token...")
    
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{BASE_URL}/feeds/", headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Protected endpoint access successful!")
        else:
            print(f"❌ Protected endpoint access failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_backend_health():
    """Test if backend is responding"""
    print("🏥 Testing backend health...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Health check status: {response.status_code}")
        print(f"Health response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Backend not responding: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing Authentication Flow...")
    
    # Test backend health first
    if not test_backend_health():
        print("❌ Backend is not running!")
        exit(1)
    
    # Test with your users
    users_to_test = [
        ("Adwait", "password123"),
        ("testuser", "password123"),
    ]
    
    for username, password in users_to_test:
        token = test_login(username, password)
        if token:
            test_protected_endpoint(token)
        print("-" * 50)
