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
