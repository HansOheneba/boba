import requests
import base64
import json
from config import Config

def test_hubtel_exact_format():
    """Test using the exact format shown in Hubtel documentation"""
    print("\n=== Testing Hubtel API Using Exact Format from Documentation ===\n")
    
    # Get and clean credentials
    api_id = Config.HUBTEL_API_ID.strip() if Config.HUBTEL_API_ID else ""
    api_key = Config.HUBTEL_API_KEY.strip() if Config.HUBTEL_API_KEY else ""
    merchant_account = Config.HUBTEL_MERCHANT_ACCOUNT.strip() if Config.HUBTEL_MERCHANT_ACCOUNT else ""
    
    # Print credentials for verification
    print(f"API ID: {api_id}")
    print(f"API KEY: {api_key[:4]}..." if len(api_key) > 4 else api_key)
    print(f"Merchant Account: {merchant_account}")
    
    # Create auth string as required
    auth_string = f"{api_id}:{api_key}"
    basic_auth = base64.b64encode(auth_string.encode()).decode('utf-8')
    
    # Prepare test payload exactly like documentation example
    payload = {  
        "totalAmount": 1.0,
        "description": "Test Transaction",
        "callbackUrl": "http://localhost:5000/hubtel-callback",
        "returnUrl": "http://localhost:5000/order-confirmation",
        "merchantAccountNumber": merchant_account,
        "cancellationUrl": "http://localhost:5000/order-cancelled",
        "clientReference": "test-001"
    }
    
    # Prepare headers exactly like documentation example
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {basic_auth}",
        "Cache-Control": "no-cache"
    }
    
    print(f"\nRequest Headers:")
    for key, value in headers.items():
        # Only show first few chars of auth to protect credentials
        if key == "Authorization":
            print(f"{key}: {value[:15]}...")
        else:
            print(f"{key}: {value}")
    
    print(f"\nRequest Payload:")
    print(json.dumps(payload, indent=2))
    
    print("\nSending request...")
    
    try:
        response = requests.post(
            "https://payproxyapi.hubtel.com/items/initiate",
            json=payload,
            headers=headers
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response Body (JSON):\n{json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Body:\n{response.text}")
        
        print(f"\nResponse Headers:")
        for key, value in response.headers.items():
            print(f"{key}: {value}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    
    print("\n=== Test Complete ===\n")

if __name__ == "__main__":
    test_hubtel_exact_format()
