import mysql.connector
from mysql.connector import Error
from config import Config  # Assuming your Config class is in config.py

def check_db_connection():
    try:
        connection = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )

        if connection.is_connected():
            db_info = connection.get_server_info()
            print("✅ Connected to MySQL Server version:", db_info)
            print("✅ Connected to database:", Config.MYSQL_DB)

    except Error as e:
        print("❌ Error while connecting to MySQL:", e)

    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("🔌 MySQL connection is closed.")

if __name__ == "__main__":
    check_db_connection()
