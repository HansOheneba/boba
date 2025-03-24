import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB = os.getenv("MYSQL_DB")
    HUBTEL_CLIENT_ID = os.getenv("HUBTEL_CLIENT_ID")
    HUBTEL_CLIENT_SECRET = os.getenv("HUBTEL_CLIENT_SECRET")
    HUBTEL_SENDER_ID = os.getenv("HUBTEL_SENDER_ID")
    IMAGEKIT_PRIVATE_KEY = os.getenv("IMAGEKIT_PRIVATE_KEY")
    IMAGEKIT_PUBLIC_KEY = os.getenv("IMAGEKIT_PUBLIC_KEY")
    IMAGEKIT_URL_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT")
    
    # Hubtel payment API credentials
    HUBTEL_API_ID = os.getenv("HUBTEL_API_ID")
    HUBTEL_API_KEY = os.getenv("HUBTEL_API_KEY")
    HUBTEL_MERCHANT_ACCOUNT = os.getenv("HUBTEL_MERCHANT_ACCOUNT")
    
    # Hubtel API endpoints - remove duplicates
    HUBTEL_CHECKOUT_URL = "https://payproxyapi.hubtel.com/items/initiate"
    HUBTEL_STATUS_URL = "https://api-txnstatus.hubtel.com/transactions"
    
    @classmethod
    def print_hubtel_config(cls):
        """Print Hubtel configuration for debugging"""
        print("-------- HUBTEL CONFIGURATION --------")
        print(f"API ID: {'Set' if cls.HUBTEL_API_ID else 'Not set'}")
        print(f"API KEY: {'Set' if cls.HUBTEL_API_KEY else 'Not set'}")
        print(f"MERCHANT ACCOUNT: {cls.HUBTEL_MERCHANT_ACCOUNT}")
        print(f"CHECKOUT URL: {cls.HUBTEL_CHECKOUT_URL}")
        print("-------------------------------------")
