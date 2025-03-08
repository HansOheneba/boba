import pymysql
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash



def get_db_connection():
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
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


def create_order(
    name, location, order_details, preferences, phone, email, total, order_number
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (name, location, order_details, preferences, phone, email, total, order_number, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            name,
            location,
            order_details,
            preferences,
            phone,
            email,
            total,
            order_number,
            "pending",
        ),
    )
    conn.commit()
    conn.close()


def get_orders(status=None):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Base query
    query = "SELECT * FROM orders"

    # Add status filter if provided
    if status:
        query += " WHERE status = %s"

    # Sort by latest first (assuming `id` is auto-incremented)
    query += " ORDER BY id DESC"

    # Execute the query
    cursor.execute(query, (status,) if status else ())
    orders = cursor.fetchall()

    conn.close()
    return orders


def update_order_status(order_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))
    conn.commit()
    conn.close()


def confirm_order(order_id):
    update_order_status(order_id, "confirmed")


def cancel_order(order_id):
    update_order_status(order_id, "canceled")


def get_products():
    """Fetch all products from the database."""
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM products ORDER BY id")
    products = cursor.fetchall()
    conn.close()
    return products


def add_product(name, image, category, in_stock):
    """Add a new product to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, image, category, in_stock) VALUES (%s, %s, %s, %s)",
        (name, image, category, in_stock),
    )
    conn.commit()
    conn.close()


def update_product(product_id, name, category, in_stock, image=None):
    """Update a product’s details, including optional image update."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if image:
        cursor.execute(
            "UPDATE products SET name=%s, category=%s, in_stock=%s, image=%s WHERE id=%s",
            (name, category, in_stock, image, product_id),
        )
    else:
        cursor.execute(
            "UPDATE products SET name=%s, category=%s, in_stock=%s WHERE id=%s",
            (name, category, in_stock, product_id),
        )

    conn.commit()
    conn.close()


def delete_product(product_id):
    """Delete a product from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=%s", (product_id,))
    conn.commit()
    conn.close()
