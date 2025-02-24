import pymysql
from config import Config


def get_db_connection():
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
    )


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
    query = (
        "SELECT * FROM orders" if not status else "SELECT * FROM orders WHERE status=%s"
    )
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
