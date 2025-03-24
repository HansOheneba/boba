import requests
import os
import base64
import json
from config import Config

def test_hubtel_auth():
    """Test Hubtel API authentication using multiple methods"""
    print("\n=== Testing Hubtel API Authentication ===\n")
    
    # Print configuration
    Config.print_hubtel_config()
    
    # Format the API credentials - ensure no whitespace
    api_id = Config.HUBTEL_API_ID.strip() if Config.HUBTEL_API_ID else ""
    api_key = Config.HUBTEL_API_KEY.strip() if Config.HUBTEL_API_KEY else ""
    
    # Create auth string and encode properly
    auth_string = f"{api_id}:{api_key}"
    basic_auth = base64.b64encode(auth_string.encode()).decode('utf-8')
    
    # Create a simple test payload
    test_payload = {
        "totalAmount": 1.0,
        "description": "API Authentication Test",
        "returnUrl": "http://example.com/return",
        "callbackUrl": "http://example.com/callback",
        "merchantAccountNumber": Config.HUBTEL_MERCHANT_ACCOUNT.strip() if Config.HUBTEL_MERCHANT_ACCOUNT else "",
        "clientReference": "test-auth-001",
        "cancellationUrl": "http://example.com/cancel"
    }
    
    print("\n--- ATTEMPT 1: Using auth parameter ---")
    try_auth_parameter(api_id, api_key, test_payload)
    
    print("\n--- ATTEMPT 2: Using Authorization header ---")
    try_auth_header(basic_auth, test_payload)
    
    print("\n--- ATTEMPT 3: Using different format for Auth header ---")
    try_alternate_auth_header(api_id, api_key, test_payload)
    
    print("\n=== Test Complete ===\n")

def try_auth_parameter(api_id, api_key, payload):
    """Try authentication using the auth parameter"""
    try:
        print(f"Using API ID: {api_id[:4]}...")
        print(f"Using API KEY: {'*****' if api_key else 'Not set!'}")
        
        response = requests.post(
            Config.HUBTEL_CHECKOUT_URL,
            json=payload,
            auth=(api_id, api_key),
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("Authentication failed with auth parameter method")
        elif response.status_code == 200:
            print("✅ SUCCESS with auth parameter method")
        else:
            print(f"Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

def try_auth_header(basic_auth, payload):
    """Try authentication using the Authorization header"""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {basic_auth}"
        }
        
        print(f"Using Authorization: Basic {basic_auth[:10]}...")
        
        response = requests.post(
            Config.HUBTEL_CHECKOUT_URL,
            json=payload,
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("Authentication failed with header method")
        elif response.status_code == 200:
            print("✅ SUCCESS with header method")
        else:
            print(f"Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

def try_alternate_auth_header(api_id, api_key, payload):
    """Try an alternate format for the Authorization header"""
    try:
        # Some APIs require credentials in different formats
        # Try with alternative encoding and format
        import base64
        auth_bytes = f"{api_id}:{api_key}".encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_b64}"
        }
        
        print(f"Using alternate encoding: Basic {auth_b64[:10]}...")
        
        response = requests.post(
            Config.HUBTEL_CHECKOUT_URL,
            json=payload,
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("Authentication failed with alternate encoding")
        elif response.status_code == 200:
            print("✅ SUCCESS with alternate encoding")
        else:
            print(f"Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_hubtel_auth()
