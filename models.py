import pymysql
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
from werkzeug.datastructures import FileStorage
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

# Load environment variables and configure Cloudinary
load_dotenv()
cloudinary.config(cloudinary_url=os.getenv("CLOUDINARY_URL"))


def upload_image_to_cloudinary(file: FileStorage):
    try:
        # Upload file to Cloudinary
        result = cloudinary.uploader.upload(file)

        # Get the secure URL from the result
        image_url = result.get("secure_url")
        if not image_url:
            print("Error: No URL returned from Cloudinary")
            return None

        print("Upload Successful! Image URL:", image_url)
        return image_url

    except Exception as e:
        print("Upload Failed! Error:", str(e))
        return None


def get_db_connection():
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def create_admin(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    cursor.execute(
        "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
        (username, password_hash),
    )
    conn.commit()
    conn.close()


def get_admin_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
    admin = cursor.fetchone()
    conn.close()
    return admin


from typing import Dict, Any


def create_transactions_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS transactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        
        # Standard response fields
        response_code VARCHAR(20),
        status VARCHAR(50),
        
        # Transaction metadata
        checkout_id VARCHAR(255),
        sales_invoice_id VARCHAR(255),
        client_reference VARCHAR(255),
        amount DECIMAL(10, 2),
        customer_phone VARCHAR(20),
        description TEXT,
        
        # Payment details (stored as JSON)
        payment_details JSON,
        
        # Raw data storage
        raw_request TEXT,
        full_response JSON,
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX(client_reference),
        INDEX(checkout_id)
    )
    """
    )
    conn.commit()
    conn.close()


def save_transaction_record(callback_data: Dict[str, Any], raw_request: str = None):
    """Save complete Hubtel callback details to database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO transactions (
        response_code,
        status,
        checkout_id,
        sales_invoice_id,
        client_reference,
        amount,
        customer_phone,
        description,
        payment_details,
        raw_request,
        full_response
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    params = (
        callback_data.get("ResponseCode"),
        callback_data.get("Status"),
        callback_data.get("Data", {}).get("CheckoutId"),
        callback_data.get("Data", {}).get("SalesInvoiceId"),
        callback_data.get("Data", {}).get("ClientReference"),
        callback_data.get("Data", {}).get("Amount"),
        callback_data.get("Data", {}).get("CustomerPhoneNumber"),
        callback_data.get("Data", {}).get("Description"),
        json.dumps(
            callback_data.get("Data", {}).get("PaymentDetails", {})
        ),  # Store as JSON
        raw_request,
        json.dumps(callback_data),  # Store entire response as JSON
    )

    cursor.execute(query, params)
    conn.commit()
    conn.close()


def get_transaction_by_reference(client_reference: str):
    """Get transaction by client reference"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(
        """
    SELECT * FROM transactions 
    WHERE client_reference = %s 
    ORDER BY created_at DESC 
    LIMIT 1
    """,
        (client_reference,),
    )
    transaction = cursor.fetchone()
    conn.close()
    return transaction


def create_order(
    name,
    location,
    order_details,
    preferences,
    phone,
    total,
    order_number,
    payment_method,
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (name, location, order_details, preferences, phone, total, order_number,payment_method, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            name,
            location,
            order_details,
            preferences,
            phone,
            total,
            order_number,
            payment_method,
            "pending",
        ),
    )
    conn.commit()
    conn.close()


def get_orders(status=None):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Base query
    query = (
        "SELECT *, TIMESTAMPDIFF(SECOND, created_at, NOW()) as seconds_ago FROM orders"
    )

    # Add WHERE condition properly
    if status:
        query += " WHERE status = %s"
        cursor.execute(query + " ORDER BY id DESC", (status,))
    else:
        cursor.execute(query + " ORDER BY id DESC")

    orders = cursor.fetchall()
    conn.close()

    # Convert time to human-readable format
    for order in orders:
        order["time_ago"] = format_time_ago(order["seconds_ago"])

    return orders


def format_time_ago(seconds):
    """Convert seconds into a short, readable time format."""
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        return f"{seconds // 60} mins ago"
    elif seconds < 86400:
        return f"{seconds // 3600} hrs ago"
    else:
        return f"{seconds // 86400} days ago"


def update_order_status(order_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))
    conn.commit()
    conn.close()


def confirm_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch order details before updating status
    cursor.execute(
        "SELECT name, phone, order_number FROM orders WHERE id=%s", (order_id,)
    )
    order = cursor.fetchone()

    if order:
        # Update status to confirmed
        cursor.execute("UPDATE orders SET status='confirmed' WHERE id=%s", (order_id,))
        conn.commit()

    conn.close()
    return order  # Return order details to use in SMS


def cancel_order(order_id):
    update_order_status(order_id, "canceled")


def get_products():
    """Fetch all active (non-deleted) products from the database."""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM products WHERE deleted = 0 ORDER BY id")
    products = cursor.fetchall()
    conn.close()
    return products


def add_product(name, image_url, category, in_stock):
    """Add a new product to the database with ImageKit URL."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if not image_url:
        print("Warning: Image URL is empty before inserting into DB!")

    cursor.execute(
        "INSERT INTO products (name, image, category, in_stock) VALUES (%s, %s, %s, %s)",
        (name, image_url, category, in_stock),
    )
    conn.commit()
    conn.close()


def update_product(product_id, name, category, in_stock, image_url=None):
    """Update a product’s details, including optional ImageKit URL update."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if image_url:  # Only update image if a new one is provided
        cursor.execute(
            "UPDATE products SET name=%s, category=%s, in_stock=%s, image=%s WHERE id=%s",
            (name, category, in_stock, image_url, product_id),
        )
    else:
        cursor.execute(
            "UPDATE products SET name=%s, category=%s, in_stock=%s WHERE id=%s",
            (name, category, in_stock, product_id),
        )

    conn.commit()
    conn.close()


def delete_product(product_id):
    """Soft delete a product by setting its deleted flag to 1."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET deleted = 1 WHERE id = %s", (product_id,))
    conn.commit()
    conn.close()


def update_payment_method(order_number, payment_method):
    """Update the payment method for a specific order."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET payment_method=%s WHERE order_number=%s",
        (payment_method, order_number),
    )
    conn.commit()
    conn.close()


def save_transaction_record(
    checkout_id,
    sales_invoice_id,
    client_reference,
    amount,
    customer_phone,
    payment_details,
    description,
):
    """Save transaction details to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO transactions (
        checkout_id, sales_invoice_id, client_reference, amount, customer_phone, payment_details, description
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    params = (
        checkout_id,
        sales_invoice_id,
        client_reference,
        amount,
        customer_phone,
        payment_details,
        description,
    )

    cursor.execute(query, params)
    conn.commit()
    conn.close()
