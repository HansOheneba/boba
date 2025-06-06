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
import pymysql.cursors

# Load environment variables and configure Cloudinary
load_dotenv()
cloudinary.config(cloudinary_url=os.getenv("CLOUDINARY_URL"))

# Global cache variable to be set from routes.py
cache = None


def set_cache(cache_instance):
    """Set the cache instance from routes.py"""
    global cache
    cache = cache_instance


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
        json.dumps(callback_data.get("Data", {}).get("PaymentDetails", {})),
        raw_request,
        json.dumps(callback_data),
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
    payment_status,
    status="pending",
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (name, location, order_details, preferences, phone, total, order_number, payment_status, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            name,
            location,
            order_details,
            preferences,
            phone,
            total,
            order_number,
            payment_status,
            status,
        ),
    )
    conn.commit()
    conn.close()


def get_orders(status=None):
    """Fetch orders with optional status filtering, with caching."""
    # Generate a cache key based on the status parameter
    cache_key = f'orders_{status if status else "all"}'

    # Check if we have a cache hit
    if cache:
        cached_orders = cache.get(cache_key)
        if cached_orders:
            return cached_orders

    # No cache hit, query the database
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

    # Store in cache with a shorter timeout (1 minute)
    # Orders change more frequently than products or toppings
    if cache:
        cache.set(cache_key, orders, timeout=60)

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
    """Fetch all active (non-deleted) products from the database with caching."""
    # If cache is available and has products data, return it
    if cache:
        cached_products = cache.get("all_products")
        if cached_products:
            return cached_products

    # No cache hit, query the database
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM products WHERE deleted = 0 ORDER BY id")
    products = cursor.fetchall()
    conn.close()

    # Store in cache if available
    if cache:
        # Cache for 5 minutes (300 seconds)
        cache.set("all_products", products, timeout=300)

    return products


def add_product(
    name, image_url, category, in_stock, small_price=None, large_price=None
):
    """Add a new product to the database with ImageKit URL and price information."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if not image_url:
        print("Warning: Image URL is empty before inserting into DB!")

    cursor.execute(
        "INSERT INTO products (name, image, category, in_stock, small_price, large_price) VALUES (%s, %s, %s, %s, %s, %s)",
        (name, image_url, category, in_stock, small_price, large_price),
    )
    conn.commit()
    conn.close()

    # Invalidate products cache when a new product is added
    if cache:
        cache.delete("all_products")


def update_product(
    product_id,
    name,
    category,
    in_stock,
    image_url=None,
    small_price=None,
    large_price=None,
):
    """Update a product's details, including optional ImageKit URL update and price information."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if image_url:  # Only update image if a new one is provided
        cursor.execute(
            "UPDATE products SET name=%s, category=%s, in_stock=%s, image=%s, small_price=%s, large_price=%s WHERE id=%s",
            (name, category, in_stock, image_url, small_price, large_price, product_id),
        )
    else:
        cursor.execute(
            "UPDATE products SET name=%s, category=%s, in_stock=%s, small_price=%s, large_price=%s WHERE id=%s",
            (name, category, in_stock, small_price, large_price, product_id),
        )

    conn.commit()
    conn.close()

    # Invalidate products cache when a product is updated
    if cache:
        cache.delete("all_products")


def delete_product(product_id):
    """Soft delete a product by setting its deleted flag to 1."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET deleted = 1 WHERE id = %s", (product_id,))
    conn.commit()
    conn.close()

    # Invalidate products cache when a product is deleted
    if cache:
        cache.delete("all_products")


def get_transactions(search_query=None):
    """Fetch all transactions with optional search filtering"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if search_query:
        cursor.execute(
            """
            SELECT * FROM transactions 
            WHERE client_reference LIKE %s 
            OR customer_phone LIKE %s
            ORDER BY created_at DESC
        """,
            (f"%{search_query}%", f"%{search_query}%"),
        )
    else:
        cursor.execute("SELECT * FROM transactions ORDER BY created_at DESC")

    transactions = cursor.fetchall()
    conn.close()

    # Format the created_at time for display
    for txn in transactions:
        if txn["created_at"]:
            txn["created_at"] = txn["created_at"].strftime("%Y-%m-%d %H:%M:%S")

    return transactions


def get_transaction_details(transaction_id):
    """Get full details of a specific transaction"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM transactions WHERE id = %s", (transaction_id,))
    transaction = cursor.fetchone()
    conn.close()
    return transaction


def get_order_by_reference(order_number):
    """Retrieve an order by its reference number"""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)  # Changed this line
    cursor.execute("SELECT * FROM orders WHERE order_number = %s", (order_number,))
    order = cursor.fetchone()
    conn.close()
    return order


def update_payment_status(order_number, payment_status):
    """Update the payment status of an order."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET payment_status=%s WHERE order_number=%s",
        (payment_status, order_number),
    )
    conn.commit()
    conn.close()


def create_toppings_table():
    """Create toppings table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS toppings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            in_stock BOOLEAN DEFAULT TRUE,
            deleted BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def get_toppings():
    """Fetch all active (non-deleted) toppings from the database with caching."""
    # Check cache first
    if cache:
        cached_toppings = cache.get("all_toppings")
        if cached_toppings:
            return cached_toppings

    # No cache hit, query the database
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM toppings WHERE deleted = 0 ORDER BY name")
    toppings = cursor.fetchall()
    conn.close()

    # Store in cache
    if cache:
        # Cache for 5 minutes (300 seconds)
        cache.set("all_toppings", toppings, timeout=300)

    return toppings


def add_topping(name, in_stock=True):
    """Add a new topping to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO toppings (name, in_stock) VALUES (%s, %s)",
        (name, in_stock),
    )
    conn.commit()
    conn.close()

    # Invalidate toppings cache when a new topping is added
    if cache:
        cache.delete("all_toppings")


def update_topping(topping_id, name, in_stock):
    """Update a topping's details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE toppings SET name=%s, in_stock=%s WHERE id=%s",
        (name, in_stock, topping_id),
    )
    conn.commit()
    conn.close()

    # Invalidate toppings cache when a topping is updated
    if cache:
        cache.delete("all_toppings")


def delete_topping(topping_id):
    """Soft delete a topping by setting its deleted flag to 1."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE toppings SET deleted = 1 WHERE id = %s", (topping_id,))
    conn.commit()
    conn.close()

    # Invalidate toppings cache when a topping is deleted
    if cache:
        cache.delete("all_toppings")


def populate_default_toppings():
    """Populate default toppings if table is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if we have any toppings already
    cursor.execute("SELECT COUNT(*) as count FROM toppings")
    result = cursor.fetchone()
    if result and result["count"] > 0:
        conn.close()
        return

    # Default toppings from the template
    default_toppings = [
        "No Toppings",
        "Chocolate",
        "Sweetened Choco",
        "Vanilla",
        "Cheese Foam",
        "Strawberry Popping",
        "Blueberry Popping",
        "Mint Popping",
        "Whipped Cream",
        "Biscoff Spread",
        "Caramel Syrup",
        "Grape Popping",
    ]

    # Insert default toppings
    for topping in default_toppings:
        cursor.execute(
            "INSERT INTO toppings (name, in_stock) VALUES (%s, %s)", (topping, True)
        )

    conn.commit()
    conn.close()


def get_setting(key):
    """Get a setting value by key from the settings table"""
    # Check cache first
    if cache:
        cached_setting = cache.get(f"setting_{key}")
        if cached_setting is not None:
            return cached_setting

    # No cache hit, query the database
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT setting_value FROM settings WHERE setting_key = %s", (key,))
    result = cursor.fetchone()
    conn.close()

    setting_value = (
        result["setting_value"] if result else True
    )  # Default to True if not found

    # Store in cache
    if cache:
        # Cache for 5 minutes (300 seconds)
        cache.set(f"setting_{key}", setting_value, timeout=300)

    return setting_value


def update_setting(key, value):
    """Update a setting in the settings table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO settings (setting_key, setting_value) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE setting_value = %s",
        (key, value, value),
    )
    conn.commit()
    conn.close()

    # Invalidate cache
    if cache:
        cache.delete(f"setting_{key}")

    return True


def get_cup_availability():
    """Get availability status for both cup sizes"""
    return {
        "small_cups_available": get_setting("small_cups_available"),
        "large_cups_available": get_setting("large_cups_available"),
    }
