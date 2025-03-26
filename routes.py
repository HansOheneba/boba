from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from urllib.parse import urljoin
import requests
import json  # Add this missing import
from models import (
    create_order,
    get_orders,
    update_order_status,
    confirm_order,
    cancel_order,
    get_admin_by_username,
    create_admin,
    get_products,
    add_product,
    update_product,
    delete_product,
    update_payment_method,
    upload_image_to_cloudinary,  # Updated function name
)
from werkzeug.security import check_password_hash
import random
import string
from werkzeug.utils import secure_filename
from flask import current_app
from functools import wraps
from config import Config
import base64


HUBTEL_CLIENT_ID = Config.HUBTEL_CLIENT_ID
HUBTEL_CLIENT_SECRET = Config.HUBTEL_CLIENT_SECRET
HUBTEL_SENDER_ID = Config.HUBTEL_SENDER_ID
HUBTEL_API_URL = "https://smsc.hubtel.com/v1/messages/send"

api_id = Config.HUBTEL_API_ID
api_key = Config.HUBTEL_API_KEY

# api id and api key converted to base 65 like so api_id:api_key
auth_string = f"{api_id}:{api_key}"
basic_auth = base64.b64encode(auth_string.encode()).decode("utf-8")
print(f"Basic Auth: {basic_auth}")
# Create a Blueprint named "app"
app = Blueprint("app", __name__)

# print("Mercant:",Config.HUBTEL_MERCHANT_ACCOUNT)


def initiate_hubtel_payment(
    total_amount,
    description,
    callback_url,
    return_url,
    client_reference,
    customer_name=None,
    customer_phone=None,
    customer_email=None,
):
    """Initiate Hubtel payment with bb-xxxx reference according to official Hubtel documentation"""
    # Debug configuration
    Config.print_hubtel_config()

    # Format the API credentials - remove any whitespace
    api_id = Config.HUBTEL_API_ID.strip() if Config.HUBTEL_API_ID else ""
    api_key = Config.HUBTEL_API_KEY.strip() if Config.HUBTEL_API_KEY else ""
    merchant_account = (
        Config.HUBTEL_MERCHANT_ACCOUNT.strip() if Config.HUBTEL_MERCHANT_ACCOUNT else ""
    )

    # Prepare headers
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {basic_auth}",
        "Cache-Control": "no-cache",
    }

    print(headers)

    # Prepare payload
    payload = {
        "totalAmount": float(total_amount),
        "description": description,
        "callbackUrl": callback_url,
        "returnUrl": return_url,
        "merchantAccountNumber": merchant_account,
        "cancellationUrl": return_url,
        "clientReference": client_reference,
    }

    # Add optional parameters if provided
    if customer_name:
        payload["payeeName"] = customer_name
    if customer_phone:
        payload["payeeMobileNumber"] = customer_phone
    if customer_email:
        payload["payeeEmail"] = customer_email

    try:
        print(f"Making Hubtel API request to: {Config.HUBTEL_CHECKOUT_URL}")
        print(f"Payload: {json.dumps(payload)}")

        response = requests.post(
            Config.HUBTEL_CHECKOUT_URL, json=payload, headers=headers
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code == 401:
            print("Authentication failed. Check your Hubtel API credentials.")
            return None

        response.raise_for_status()

        response_data = response.json()
        return response_data.get("data", {}).get("checkoutDirectUrl")

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def check_hubtel_payment_status(client_reference):
    """Check payment status using bb-xxxx reference"""
    auth_string = f"{Config.HUBTEL_API_ID}:{Config.HUBTEL_API_KEY}"
    basic_auth = base64.b64encode(auth_string.encode()).decode()

    headers = {"Authorization": f"Basic {basic_auth}"}

    try:
        url = f"{Config.HUBTEL_STATUS_URL}/{Config.HUBTEL_MERCHANT_ACCOUNT}/transactions/status?clientReference={client_reference}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("data", {})
    except Exception as e:
        print(f"Hubtel status check failed: {e}")
        return None


def generate_order_number():
    chars = string.ascii_lowercase + string.digits
    return "bb-" + "".join(random.choice(chars) for _ in range(4))


def login_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "admin_id" not in session:
            flash("You must be logged in to access this page.", "error")
            return redirect(url_for("app.login"))
        return view(*args, **kwargs)

    return wrapped_view


def format_order_details(customer_name, order_details):
    # Map product names to their respective emojis
    product_icons = {
        "Blueberry Boba": "🧋",
        "Brown Sugar Boba": "🧋",
        "Caramel Milk": "🧋",
        "Classic Boba": "🧋",
        "Coconut Milk": "🧋",
        "Coffee": "🧋",
        "Taro Boba": "🧋",
        "Vanilla Boba": "🧋",
        "Lilac (Grape)": "🧋",
        "Dew Drop-Honeydew": "🧋",
        "Strawberry-Rosey Rush": "🧋",
        "Banana Breeze": "🧋",
        "Lotus-Bliss": "🧋",
        "Matcha-Emerald": "🧋",
        "Chocolate Delight": "🧋",
        "Oreoreo": "🧋",
        "Piñata-Pineapple": "🧋",
        "Pudding (Custard)": "🧋",
        "Xenotherev": "🧋",
        "H2O2": "🧋",
        "Lemon Ice Tea": "☕",
        "Chicken Shawarma": "🍗",
        "Beef Shawarma": "🍔",
    }

    # Process and format each item in the order
    items = order_details.split(", ")
    formatted_items = "\n".join(
        [
            f"{product_icons.get(item.strip().split(' (')[0], '🧋')} {item.strip()}"  # Strip spaces & remove sizes
            for item in items
        ]
    )

    # Final SMS message
    sms_message = f"""Hello {customer_name}, Your order for: 

{formatted_items}  

Has been placed and is being processed. You should hear from us shortly.
"""

    return sms_message


def format_phone_number(phone):
    """Convert local Ghana phone numbers (059XXXXXXX) to international format (23359XXXXXXX)."""
    if phone.startswith("0"):
        return "233" + phone[1:]  # Replace leading "0" with "233"
    return phone


def send_sms_hubtel(to, message):
    """Send an SMS using Hubtel API"""
    url = f"{HUBTEL_API_URL}?clientsecret={HUBTEL_CLIENT_SECRET}&clientid={HUBTEL_CLIENT_ID}&from={HUBTEL_SENDER_ID}&to={to}&content={message}"

    try:
        response = requests.get(url)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("status") == "Success":
            print(f"✅ SMS sent successfully to {to}")
        else:
            print(f"❌ Failed to send SMS: {response_data}")

    except Exception as e:
        print(f"❌ Error sending SMS: {e}")


@app.route("/", methods=["GET", "POST"])
def index():
    all_products = get_products()
    boba_items = [
        product
        for product in all_products
        if product["category"] == "Bubble Tea" and product["in_stock"]
    ]
    ice_tea_items = [
        product
        for product in all_products
        if product["category"] == "Ice Tea" and product["in_stock"]
    ]
    shawarma_items = [
        product
        for product in all_products
        if product["category"] == "Shawarma" and product["in_stock"]
    ]

    if request.method == "POST":
        name = request.form.get("name")
        location = request.form.get("location")
        order_details = request.form.get("order")
        notes = request.form.get("notes")
        phone = request.form.get("phone")
        email = request.form.get("email")
        total = request.form.get("total")
        boba_toppings = request.form.get("boba_toppings")
        shawarma_type = request.form.get("shawarma_type")
        payment_method = request.form.get("payment_method", "paid")
        order_number = generate_order_number()
        print("Received payment method:", payment_method)

        if not name or not location or not order_details or not phone:
            return "All fields are required", 400

        # Combine boba toppings and shawarma type into order_details
        if boba_toppings:
            order_details += f" with {boba_toppings}"
        if shawarma_type:
            order_details += f", {shawarma_type}"

        create_order(
            name,
            location,
            order_details,
            notes,
            phone,
            email,
            total,
            order_number,
            payment_method,
        )
        customer_name = f"{name}"
        formatted_message = format_order_details(customer_name, order_details)

        send_sms_hubtel(phone, formatted_message)
        return redirect(
            url_for("app.order_confirmation", total=total, order_number=order_number)
        )

    return render_template(
        "index.html",
        boba_items=boba_items,
        ice_tea_items=ice_tea_items,
        shawarma_items=shawarma_items,
    )


@app.route("/order-confirmation")
def order_confirmation():
    total = request.args.get("total")
    order_number = request.args.get("order_number")
    return render_template(
        "order_confirmation.html", total=total, order_number=order_number
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        admin = get_admin_by_username(username)
        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_id"] = admin["id"]
            session["username"] = admin["username"]
            flash("Logged in successfully!", "success")
            return redirect("/admin")
        else:
            flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("app.login"))


# @app.route("/create_admin", methods=["GET", "POST"])
# def create_admin_route():
#     if request.method == "POST":
#         username = request.form.get("username")
#         password = request.form.get("password")

#         if not username or not password:
#             flash("Username and password are required.", "error")
#         else:
#             create_admin(username, password)
#             flash("Admin created successfully!", "success")
#             return redirect(url_for("app.login"))

#     return render_template("create_admin.html")


@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if request.method == "POST":
        order_id = request.form.get("order_id")
        action = request.form.get("action")

        if action == "confirm":
            order = confirm_order(order_id)  # Get order details
            if order:
                # Format SMS
                customer_name = order["name"]
                customer_phone = order["phone"]
                order_number = order["order_number"]

                message = f"""Heyyy {customer_name}, 
your order is ready for delivery! 
A rider will call you soon. 📞  

🛍️ Order Reference: {order_number}

Your taste buds are in for a treat! 😋🎉  

Need help? Chat with us on WhatsApp: (https://wa.me/233592076527)  
"""

                # Send SMS
                send_sms_hubtel(customer_phone, message)

        elif action == "cancel":
            cancel_order(order_id)

        return redirect("/admin")

    status_filter = request.args.get("status", "")
    search_query = request.args.get("search", "")

    orders = get_orders(status=status_filter)

    if search_query:
        orders = [
            order
            for order in orders
            if search_query.lower() in order["order_number"].lower()
        ]

    return render_template("admin.html", orders=orders)


@app.route("/admin/products", methods=["GET", "POST"])
@login_required
def admin_products():
    if request.method == "POST":
        product_id = request.form.get("product_id")  # If editing
        name = request.form["name"]
        category = request.form["category"]
        in_stock = request.form.get("in_stock") == "on"

        file = request.files.get("image")  # Get the uploaded file
        image_url = None
        if file and file.filename:  # Ensure file is uploaded
            print(file)
            image_url = upload_image_to_cloudinary(file)  # Updated function call
            if image_url:
                print(f"Image uploaded successfully: {image_url}")
            else:
                print("Image upload failed.")

        if product_id:  # If updating a product
            update_product(product_id, name, category, in_stock, image_url)
        else:  # If adding a new product
            add_product(name, image_url, category, in_stock)

        return redirect(url_for("app.admin_products"))

    products = get_products()
    return render_template("admin_products.html", products=products)


@app.route("/admin/delete_product/<int:product_id>", methods=["POST"])
def delete_product_route(product_id):
    delete_product(product_id)
    return redirect(url_for("app.admin_products"))


@app.route("/update-payment", methods=["POST"])
def update_payment():
    data = request.json
    order_number = data.get("order_number")
    payment_method = data.get("payment_method")

    update_payment_method(order_number, payment_method)

    return {"message": "Payment updated successfully"}, 200


@app.route("/hubtel-payment", methods=["POST"])
def hubtel_payment():
    data = request.json
    order_number = data.get("order_number")  # Your bb-xxxx format
    total = data.get("total")
    name = data.get("name")
    phone = data.get("phone")
    email = data.get("email")

    if not order_number or not total:
        return jsonify({"error": "Missing required parameters"}), 400

    # Generate callback and return URLs
    base_url = request.host_url.rstrip("/")
    callback_url = urljoin(base_url, url_for("app.hubtel_callback"))
    return_url = urljoin(
        base_url,
        url_for("app.order_confirmation", order_number=order_number, total=total),
    )

    # Prepare auth header
    auth_string = f"{Config.HUBTEL_API_ID}:{Config.HUBTEL_API_KEY}"
    basic_auth = base64.b64encode(auth_string.encode()).decode()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {basic_auth}",
        "Cache-Control": "no-cache",
    }

    payload = {
        "totalAmount": float(total),
        "description": f"Order {order_number}",
        "callbackUrl": callback_url,
        "returnUrl": return_url,
        "merchantAccountNumber": Config.HUBTEL_MERCHANT_ACCOUNT,
        "cancellationUrl": return_url,
        "clientReference": order_number,
    }

    # Add optional parameters if provided
    if name:
        payload["payeeName"] = name
    if phone:
        payload["payeeMobileNumber"] = phone
    if email:
        payload["payeeEmail"] = email

    try:
        # Log the full request details
        print("=== Hubtel API Request ===")
        print(f"URL: {Config.HUBTEL_CHECKOUT_URL}")
        print(f"Headers: {json.dumps(headers, indent=2)}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print("==========================")

        response = requests.post(
            Config.HUBTEL_CHECKOUT_URL,
            json=payload,
            headers=headers,
        )

        # Log the response details
        print("=== Hubtel API Response ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        print("==========================")

        response.raise_for_status()

        response_data = response.json()
        checkout_url = response_data.get("data", {}).get("checkoutDirectUrl")

        if not checkout_url:
            return jsonify({"error": "No checkout URL received"}), 500

        return jsonify({"checkout_url": checkout_url})

    except requests.exceptions.RequestException as e:
        print(f"Hubtel API error: {e}")
        return jsonify({"error": "Payment initiation failed"}), 500


@app.route("/hubtel-callback", methods=["POST"])
def hubtel_callback():
    """Handle Hubtel payment notifications"""
    data = request.json
    client_reference = data.get("clientReference")
    status = data.get("status", "").lower()

    # Verify the payment status
    if status == "success" and client_reference:
        # Double-check with status API
        auth_string = f"{Config.HUBTEL_API_ID}:{Config.HUBTEL_API_KEY}"
        basic_auth = base64.b64encode(auth_string.encode()).decode()
        headers = {"Authorization": f"Basic {basic_auth}"}

        try:
            url = f"https://rmsc.hubtel.com/v1/merchantaccount/merchants/{Config.HUBTEL_MERCHANT_ACCOUNT}/transactions/status?clientReference={client_reference}"
            verify_response = requests.get(url, headers=headers)
            verify_response.raise_for_status()

            verify_data = verify_response.json()
            if verify_data.get("status") == "Paid":
                update_payment_method(client_reference, "paid")
                return jsonify({"status": "verified"}), 200

        except Exception as e:
            print(f"Verification failed: {e}")

    return jsonify({"status": "unverified"}), 400


@app.route("/hubtel-status", methods=["GET"])
def hubtel_status_check():
    client_reference = request.args.get("clientReference")
    if not client_reference:
        return jsonify({"error": "clientReference is required"}), 400

    # Prepare auth header
    auth_string = f"{Config.HUBTEL_API_ID}:{Config.HUBTEL_API_KEY}"
    basic_auth = base64.b64encode(auth_string.encode()).decode()

    headers = {"Authorization": f"Basic {basic_auth}"}

    try:
        url = f"https://rmsc.hubtel.com/v1/merchantaccount/merchants/{Config.HUBTEL_MERCHANT_ACCOUNT}/transactions/status?clientReference={client_reference}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        response_data = response.json()
        return jsonify(
            {"status": response_data.get("status", "Unknown"), "data": response_data}
        )

    except requests.exceptions.RequestException as e:
        print(f"Hubtel status check error: {e}")
        return jsonify({"error": "Status check failed"}), 500
