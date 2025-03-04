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
    name, location, order_details, preferences, phone, total, order_number
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (name, location, order_details, preferences, phone, total, order_number, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            name,
            location,
            order_details,
            preferences,
            phone,
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
