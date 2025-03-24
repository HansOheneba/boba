import subprocess
import base64
import json
import os
from config import Config

def test_hubtel_with_curl():
    """Test Hubtel API using curl command line for raw HTTP control"""
    print("\n=== Testing Hubtel API Using curl ===\n")
    
    # Get credentials
    api_id = Config.HUBTEL_API_ID.strip() if Config.HUBTEL_API_ID else ""
    api_key = Config.HUBTEL_API_KEY.strip() if Config.HUBTEL_API_KEY else ""
    merchant_account = Config.HUBTEL_MERCHANT_ACCOUNT.strip() if Config.HUBTEL_MERCHANT_ACCOUNT else ""
    
    # Create authentication string (without base64 encoding - curl will do it)
    auth_string = f"{api_id}:{api_key}"
    
    # Create test payload
    payload = {
        "totalAmount": 1.0,
        "description": "Test Transaction",
        "callbackUrl": "http://localhost:5000/hubtel-callback",
        "returnUrl": "http://localhost:5000/return",
        "merchantAccountNumber": merchant_account,
        "cancellationUrl": "http://localhost:5000/cancel",
        "clientReference": "curl-test-001"
    }
    
    # Convert payload to JSON
    payload_json = json.dumps(payload)
    
    # Construct the curl command
    curl_cmd = [
        'curl',
        '-X', 'POST',
        'https://payproxyapi.hubtel.com/items/initiate',
        '-H', 'Accept: application/json',
        '-H', 'Content-Type: application/json',
        '-H', 'Cache-Control: no-cache',
        '-u', auth_string,  # Using -u for basic auth instead of manual encoding
        '-d', payload_json,
        '-v'  # For verbose output to see headers
    ]
    
    print("Executing curl command...")
    print(f"API ID: {api_id[:4]}..." if len(api_id) > 4 else f"API ID: {api_id}")
    print(f"Merchant account: {merchant_account}")
    print(f"Payload: {payload_json}")
    
    try:
        # Execute the curl command and capture output
        process = subprocess.Popen(
            curl_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        print("\n--- cURL Output ---\n")
        # stderr from curl contains the request and response headers
        print(stderr)
        
        print("\n--- Response Body ---\n")
        print(stdout)
        
        # Try to parse JSON response
        try:
            response_data = json.loads(stdout)
            print("\nFormatted JSON Response:")
            print(json.dumps(response_data, indent=2))
        except:
            print("\nResponse is not valid JSON")
            
    except Exception as e:
        print(f"Error executing curl: {str(e)}")
    
    print("\n=== Test Complete ===\n")

if __name__ == "__main__":
    test_hubtel_with_curl()
