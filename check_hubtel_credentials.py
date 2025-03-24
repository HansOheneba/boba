import os
import requests
import base64
from dotenv import load_dotenv
import sys

def check_hubtel_credentials():
    """Verify Hubtel API credentials are properly set and formatted"""
    
    # Ensure environment variables are loaded
    load_dotenv()
    
    # Check for required environment variables
    required_vars = ["HUBTEL_API_ID", "HUBTEL_API_KEY", "HUBTEL_MERCHANT_ACCOUNT"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please make sure these are set in your .env file")
        return False
    
    # Check for format issues
    for var in required_vars:
        value = os.getenv(var)
        if value.strip() != value:
            print(f"⚠️ WARNING: {var} has leading or trailing whitespace")
            print(f"  Current: '{value}'")
            print(f"  Should be: '{value.strip()}'")
    
    # Get credentials
    hubtel_api_id = os.getenv("HUBTEL_API_ID").strip()
    hubtel_api_key = os.getenv("HUBTEL_API_KEY").strip()
    hubtel_merchant_account = os.getenv("HUBTEL_MERCHANT_ACCOUNT").strip()
    
    print("\nCredentials Summary:")
    print(f"API ID: {hubtel_api_id[:4]}..." + "*" * 8)
    print(f"API KEY: " + "*" * 12)
    print(f"Merchant Account: {hubtel_merchant_account}")
    
    # Verification option
    verify = input("\nWould you like to verify these credentials with Hubtel? (y/n): ")
    
    if verify.lower() == 'y':
        # Try a simple authentication test
        auth_string = f"{hubtel_api_id}:{hubtel_api_key}"
        basic_auth = base64.b64encode(auth_string.encode()).decode('utf-8')
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {basic_auth}"
        }
        
        # Create a minimal test payload
        payload = {
            "totalAmount": 1.0,
            "description": "Credential verification test",
            "returnUrl": "http://example.com/return",
            "callbackUrl": "http://example.com/callback",
            "merchantAccountNumber": hubtel_merchant_account,
            "clientReference": "verify-001",
            "cancellationUrl": "http://example.com/cancel"
        }
        
        try:
            print("\nSending verification request to Hubtel...")
            response = requests.post(
                "https://payproxyapi.hubtel.com/items/initiate",
                json=payload,
                headers=headers
            )
            
            print(f"Response Status Code: {response.status_code}")
            
            if response.status_code == 401:
                print("❌ AUTHENTICATION FAILED: Your API credentials are invalid or expired.")
                print("Please check your Hubtel merchant dashboard for the correct credentials.")
                print(f"Response: {response.text}")
            elif response.status_code == 200:
                print("✅ AUTHENTICATION SUCCESSFUL: Your API credentials are valid.")
            else:
                print(f"⚠️ UNEXPECTED STATUS CODE: {response.status_code}")
                print(f"Response: {response.text}")
        
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
    
    # Provide instructions for updating the .env file
    print("\n--- INSTRUCTIONS FOR VERIFYING CREDENTIALS ---")
    print("1. Log into your Hubtel merchant dashboard")
    print("2. Navigate to Settings > API Integration")
    print("3. Verify your credentials match the following:")
    print("   - Merchant Account Number matches your .env HUBTEL_MERCHANT_ACCOUNT")
    print("   - API ID matches your .env HUBTEL_API_ID")
    print("   - API Key/Secret matches your .env HUBTEL_API_KEY")
    print("4. Make sure there are no spaces before or after your credentials")
    print("5. Update your .env file if needed with the correct credentials")
    print("-----------------------------------------------")
    
    return True

if __name__ == "__main__":
    check_hubtel_credentials()
