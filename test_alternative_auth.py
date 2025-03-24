import requests
import base64
import json
from config import Config

def test_different_auth_methods():
    """Try various authentication methods with the Hubtel API"""
    print("\n=== Testing Alternative Authentication Methods for Hubtel API ===\n")
    
    # Get and clean credentials
    api_id = Config.HUBTEL_API_ID.strip() if Config.HUBTEL_API_ID else ""
    api_key = Config.HUBTEL_API_KEY.strip() if Config.HUBTEL_API_KEY else ""
    merchant_account = Config.HUBTEL_MERCHANT_ACCOUNT.strip() if Config.HUBTEL_MERCHANT_ACCOUNT else ""
    
    # Minimum required payload
    test_payload = {
        "totalAmount": 1.0,
        "description": "Auth test",
        "callbackUrl": "http://localhost:5000/callback",
        "returnUrl": "http://localhost:5000/return",
        "merchantAccountNumber": merchant_account,
        "clientReference": "test-auth-001",
        "cancellationUrl": "http://localhost:5000/cancel"
    }
    
    print("Credentials being used:")
    print(f"API ID: {api_id[:4]}..." if len(api_id) > 4 else api_id)
    print(f"API KEY: {'*' * 8}...")
    print(f"Merchant Account: {merchant_account}")
    print(f"Checkout URL: {Config.HUBTEL_CHECKOUT_URL}")
    print("\n")
    
    # Method 1: Using requests.auth parameter
    print("METHOD 1: Using requests.auth parameter")
    try:
        response = requests.post(
            Config.HUBTEL_CHECKOUT_URL,
            json=test_payload,
            auth=(api_id, api_key)
        )
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {str(e)}")
    print("\n")
    
    # Method 2: Using base64 encoded Authorization header
    print("METHOD 2: Using base64 encoded header (utf-8)")
    try:
        auth_string = f"{api_id}:{api_key}"
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_base64}"
        }
        response = requests.post(
            Config.HUBTEL_CHECKOUT_URL,
            json=test_payload,
            headers=headers
        )
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {str(e)}")
    print("\n")
    
    # Method 3: Using ASCII encoding 
    print("METHOD 3: Using base64 encoded header (ASCII)")
    try:
        auth_string = f"{api_id}:{api_key}"
        auth_bytes = auth_string.encode('ascii')
        auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_base64}"
        }
        response = requests.post(
            Config.HUBTEL_CHECKOUT_URL,
            json=test_payload,
            headers=headers
        )
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {str(e)}")
    print("\n")
    
    # Method 4: Using an API key/Client Secret approach
    print("METHOD 4: Using direct API parameters")
    try:
        # Some APIs use query parameters or custom headers
        params = {
            "clientId": api_id,
            "clientSecret": api_key
        }
        response = requests.post(
            Config.HUBTEL_CHECKOUT_URL,
            json=test_payload,
            params=params
        )
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    print("\n=== Testing Complete ===")

if __name__ == "__main__":
    test_different_auth_methods()
