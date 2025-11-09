import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api"

def print_response(response, endpoint_name):
    print(f"\n{'='*50}")
    print(f"Testing: {endpoint_name}")
    print(f"Status: {response.status_code}")
    if response.status_code >= 400:
        print(f"Error: {response.text}")
    else:
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response: {response.text}")

def test_authentication():
    """Test user login and token generation"""
    print("🔐 Testing Authentication")
    
    # Test student login
    login_data = {
        "username": "student1",
        "password": "student123"
    }
    
    response = requests.post(f"{BASE_URL}/token/", json=login_data)
    print_response(response, "Student Login")
    
    if response.status_code == 200:
        tokens = response.json()
        return tokens['access']
    return None

def test_equipment_endpoints(token):
    """Test equipment-related endpoints"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get all equipment
    response = requests.get(f"{BASE_URL}/equipment/", headers=headers)
    print_response(response, "Get All Equipment")
    
    # Get available equipment only
    response = requests.get(f"{BASE_URL}/equipment/?available=true", headers=headers)
    print_response(response, "Get Available Equipment")
    
    # Search equipment
    response = requests.get(f"{BASE_URL}/equipment/?search=camera", headers=headers)
    print_response(response, "Search Equipment (camera)")
    
    # Get equipment by category
    response = requests.get(f"{BASE_URL}/equipment/?category=1", headers=headers)
    print_response(response, "Get Equipment by Category (Photography)")
    
    # Get specific equipment details
    response = requests.get(f"{BASE_URL}/equipment/1/", headers=headers)
    print_response(response, "Get Equipment Details (ID: 1)")
    
    # Check equipment availability
    start_date = (datetime.now() + timedelta(days=1)).isoformat()
    end_date = (datetime.now() + timedelta(days=7)).isoformat()
    response = requests.get(
        f"{BASE_URL}/equipment/1/availability/?start={start_date}&end={end_date}", 
        headers=headers
    )
    print_response(response, "Check Equipment Availability")

def test_borrow_requests(token):
    """Test borrow request endpoints"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get my requests
    response = requests.get(f"{BASE_URL}/requests/my_requests/", headers=headers)
    print_response(response, "Get My Borrow Requests")
    
    # Create a new borrow request
    borrow_data = {
        "equipment": 2,  # MacBook Pro
        "quantity": 1,
        "purpose": "Testing API - need for programming project",
        "borrow_from": (datetime.now() + timedelta(days=2)).isoformat(),
        "borrow_until": (datetime.now() + timedelta(days=9)).isoformat()
    }
    
    response = requests.post(f"{BASE_URL}/requests/", json=borrow_data, headers=headers)
    print_response(response, "Create Borrow Request")
    
    if response.status_code == 201:
        request_id = response.json()['id']
        return request_id
    return None

def test_categories(token):
    """Test category endpoints"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get all categories
    response = requests.get(f"{BASE_URL}/categories/", headers=headers)
    print_response(response, "Get All Categories")

def test_dashboard(token):
    """Test dashboard endpoints"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get dashboard statistics
    response = requests.get(f"{BASE_URL}/dashboard/statistics/", headers=headers)
    print_response(response, "Get Dashboard Statistics")

def test_wishlist(token):
    """Test wishlist functionality"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Add to wishlist
    response = requests.post(f"{BASE_URL}/equipment/1/wishlist/", headers=headers)
    print_response(response, "Add to Wishlist")
    
    # Get wishlist items
    response = requests.get(f"{BASE_URL}/wishlist/", headers=headers)
    print_response(response, "Get Wishlist")

def test_user_profile(token):
    """Test user profile endpoints"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get user profile
    response = requests.get(f"{BASE_URL}/users/me/", headers=headers)
    print_response(response, "Get User Profile")

def main():
    print("🚀 Starting API Tests for Equipment Lending System")
    print("="*60)
    
    # Get authentication token
    token = test_authentication()
    
    if not token:
        print("❌ Authentication failed. Please check credentials.")
        return
    
    print(f"✅ Successfully obtained token: {token[:20]}...")
    
    # Test various endpoints
    test_user_profile(token)
    test_categories(token)
    test_equipment_endpoints(token)
    test_borrow_requests(token)
    test_dashboard(token)
    test_wishlist(token)
    
    print("\n" + "="*60)
    print("✅ All API tests completed!")

if __name__ == "__main__":
    main()