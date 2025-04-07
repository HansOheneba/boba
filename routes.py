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
import uuid  # Add uuid module for unique identifiers
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
    upload_image_to_cloudinary,
    save_transaction_record,
    get_transaction_by_reference,
    get_transactions,
    get_transaction_details,
    get_order_by_reference,
    update_payment_status,
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
print(f"API ID: {api_id}")
print(f"API KEY: {api_key}")
credentials = f"{api_id}:{api_key}"
basic_auth = base64.b64encode(credentials.encode()).decode()
print(f"Basic Auth: {basic_auth}")
# Create a Blueprint named "app"
app = Blueprint("app", __name__)


def initiate_hubtel_payment(
    total_amount,
    description,
    callback_url,
    return_url,
    client_reference,
    customer_name=None,
    customer_phone=None,
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

    unique_id = str(uuid.uuid4()).replace("-", "")[:5]
    return "bb-" + unique_id


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


@app.route("/generate-order-number")
def generate_order_number_route():
    """Generate a unique order number using UUID"""
    unique_id = str(uuid.uuid4()).replace("-", "")[:5]  # First 8 chars of UUID
    order_number = f"bb-{unique_id}"
    return jsonify({"order_number": order_number})


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
        total = request.form.get("total")
        boba_toppings = request.form.get("boba_toppings")
        shawarma_type = request.form.get("shawarma_type")
        payment_status = request.form.get("payment_method", "paid")
        order_number = generate_order_number()
        print("Received payment method:", payment_status)

        if not name or not location or not order_details or not phone:
            return "All fields are required", 400

        # Combine boba toppings and shawarma type into order_details
        if boba_toppings:
            order_details += f" with {boba_toppings}"
        if shawarma_type:
            order_details += f", {shawarma_type}"

        payment_status = (
            "on_delivery" if payment_status == "on_delivery" else "pending_payment"
        )
        create_order(
            name,
            location,
            order_details,
            notes,
            phone,
            total,
            order_number,
            payment_status,
            "pending",
        )

        if payment_status == "on_delivery":
            customer_name = f"{name}"
            formatted_message = format_order_details(customer_name, order_details)

            # Format the phone number to international format
            formatted_phone = format_phone_number(phone)
            print(
                f"Sending SMS for pay-on-delivery order to {formatted_phone} (original: {phone})"
            )

            # Send SMS with formatted phone number
            send_sms_hubtel(formatted_phone, formatted_message)
            print(f"SMS sent successfully for pay-on-delivery order {order_number}")
        else:
            print(
                f"Skipping immediate SMS for online payment order {order_number} (will be sent on payment completion)"
            )

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
                # Format the phone number to international format
                formatted_phone = format_phone_number(customer_phone)
                print(
                    f"Sending order ready SMS to {formatted_phone} (original: {customer_phone})"
                )

                # Send SMS with formatted phone number
                send_sms_hubtel(formatted_phone, message)

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

    update_payment_status(order_number, payment_method)

    return {"message": "Payment updated successfully"}, 200


@app.route("/hubtel-payment", methods=["POST"])
def hubtel_payment():
    data = request.json
    order_number = data.get("order_number")  # Your bb-xxxx format
    total = data.get("total")
    name = data.get("name")
    phone = data.get("phone")

    if not order_number or not total:
        return jsonify({"error": "Missing required parameters"}), 400

    # Generate callback and return URLs
    base_url = request.host_url.rstrip("/")
    callback_url = "http://order.bubbleblisscafe.com/hubtel-callback"
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
        "cancellationUrl": base_url,
        "clientReference": order_number,
    }

    # Add optional parameters if provided
    if name:
        payload["payeeName"] = name
    if phone:
        payload["payeeMobileNumber"] = phone

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
        checkout_url = response_data.get("data", {}).get("checkoutUrl")

        if not checkout_url:
            return jsonify({"error": "No checkout URL received"}), 500

        return jsonify({"checkout_url": checkout_url})

    except requests.exceptions.RequestException as e:
        print(f"Hubtel API error: {e}")
        return jsonify({"error": "Payment initiation failed"}), 500


@app.route("/hubtel-callback", methods=["POST"])
def hubtel_callback():
    """Handle Hubtel payment notifications and store all data"""
    print("\n============ HUBTEL CALLBACK RECEIVED ============")

    try:
        # Capture raw request first
        raw_data = request.get_data(as_text=True)
        print(f"Raw request data: {raw_data}")

        # Parse JSON data
        data = request.json
        print(f"Parsed JSON: {json.dumps(data, indent=2)}")

        # Validate we have basic structure
        if not all(field in data for field in ["ResponseCode", "Status"]):
            print("Missing required top-level fields")
            return jsonify({"error": "Missing required fields"}), 400

        # Save everything to database (including failed transactions)
        try:
            save_transaction_record(data, raw_request=raw_data)
            print("Transaction saved to database (all fields preserved)")
        except Exception as db_error:
            print(f"DATABASE SAVE ERROR: {str(db_error)}")
            import traceback

            print(traceback.format_exc())

        # Only process successful transactions further
        if (
            data["ResponseCode"] == "0000"
            and data.get("Status", "").lower() == "success"
        ):
            transaction_data = data.get("Data", {})
            order_number = transaction_data.get("ClientReference", "")

            if order_number:
                print(f"Processing successful payment for order: {order_number}")

                try:
                    # Update order payment method to 'paid'
                    update_payment_status(order_number, "paid")
                    print("Order payment method updated to 'paid'")

                    # Get complete order details from database
                    order = get_order_by_reference(order_number)

                    if order:
                        # Format and send SMS
                        customer_name = order["name"]
                        order_details = order["order_details"]
                        phone = order["phone"]
                        formatted_message = format_order_details(
                            customer_name, order_details
                        )
                        send_sms_hubtel(phone, formatted_message)
                        print(f"SMS sent to {phone} for order {order_number}")
                    else:
                        print(f"Order {order_number} not found in database")
                except Exception as processing_error:
                    print(
                        f"Error processing successful transaction: {str(processing_error)}"
                    )
                    import traceback

                    print(traceback.format_exc())

        print("============ CALLBACK PROCESSING COMPLETE ============\n")
        return jsonify({"status": "received"}), 200

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500


# routes.py - Updated Hubtel status check endpoint
@app.route("/hubtel-status", methods=["GET"])
def hubtel_status_check():
    """Check the status of a transaction with proper error handling"""
    client_reference = request.args.get("client_reference")
    if not client_reference:
        return jsonify({"error": "client_reference is required"}), 400

    try:
        # Format the credentials exactly as required
        auth_string = f"{Config.HUBTEL_API_ID}:{Config.HUBTEL_API_KEY}"
        basic_auth = base64.b64encode(auth_string.encode()).decode()

        # Make sure merchant account is correctly formatted (no spaces)
        merchant_id = Config.HUBTEL_MERCHANT_ACCOUNT.strip()

        # Use the exact URL format provided
        url = f"https://rmsc.hubtel.com/v1/merchantaccount/merchants/{merchant_id}/transactions/status?clientReference={client_reference}"

        headers = {"Authorization": f"Basic {basic_auth}", "Accept": "application/json"}

        print(f"Making direct request to Hubtel endpoint:")
        print(f"URL: {url}")
        print(f"Auth Header: Basic {basic_auth[:5]}...")

        # Make the request directly to Hubtel
        response = requests.get(url, headers=headers, timeout=15)

        # Detailed logging for debugging
        print(f"Hubtel Response Status: {response.status_code}")
        print(f"Hubtel Response Body: {response.text[:500]}...")

        # Handle response appropriately
        if response.status_code == 403 or response.status_code == 401:
            return (
                jsonify(
                    {
                        "error": "Authentication failed",
                        "details": "Invalid API credentials or merchant account",
                        "status_code": response.status_code,
                    }
                ),
                403,
            )

        response.raise_for_status()

        # Parse the response data
        response_data = response.json()

        # Check if we have Data array with at least one item
        transaction_data = {}
        if response_data.get("Data") and len(response_data["Data"]) > 0:
            transaction_data = response_data["Data"][0]

        # Create a simplified response with proper structure without saving to database
        simplified_response = {
            "status": "success",
            "data": {
                "status": transaction_data.get("TransactionStatus", "Pending"),
                "client_reference": transaction_data.get(
                    "ClientReference", client_reference
                ),
                "amount": transaction_data.get("TransactionAmount"),
                "date": transaction_data.get("StartDate"),
                "payment_method": transaction_data.get("PaymentMethod"),
                "mobile_number": transaction_data.get("MobileNumber"),
                "provider_message": transaction_data.get("ProviderDescription"),
            },
            "source": "hubtel_api",
            "full_response": response_data,  # Include full response for debugging
        }

        return jsonify(simplified_response)

    except requests.exceptions.RequestException as e:
        print(f"Hubtel API request error: {str(e)}")
        return jsonify({"error": "Hubtel API request failed", "details": str(e)}), 502
    except json.JSONDecodeError as e:
        print(f"Invalid JSON response from Hubtel: {str(e)}")
        return (
            jsonify({"error": "Invalid response from Hubtel", "details": str(e)}),
            500,
        )
    except Exception as e:
        print(f"Internal server error: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/admin/transactions", methods=["GET"])
@login_required
def admin_transactions():
    """Admin view for transactions with Hubtel status check capability"""
    search_query = request.args.get("search", "")
    transactions = get_transactions(search_query)
    return render_template("admin_transactions.html", transactions=transactions)


@app.route("/admin/transaction-details/<int:transaction_id>", methods=["GET"])
@login_required
def transaction_details(transaction_id):
    """Get detailed information for a specific transaction"""
    transaction = get_transaction_details(transaction_id)
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404

    # Convert raw JSON fields back to Python objects
    if transaction.get("full_response"):
        transaction["full_response"] = json.loads(transaction["full_response"])
    if transaction.get("payment_details"):
        transaction["payment_details"] = json.loads(transaction["payment_details"])

    return jsonify(transaction)


@app.route("/save-order", methods=["POST"])
def save_order():
    data = request.json
    name = data.get("name")
    location = data.get("location")
    order_details = data.get("order")
    preferences = data.get("preferences", "")  # Using preferences instead of notes
    phone = data.get("phone")
    total = data.get("total")
    order_number = data.get("order_number")

    # Check required fields
    if not name or not location or not order_details or not phone or not order_number:
        return jsonify({"error": "Missing required fields"}), 400

    # Initial payment status is 'pending_payment' when using Hubtel
    create_order(
        name,
        location,
        order_details,
        preferences,
        phone,
        total,
        order_number,
        "pending_payment",
        "pending",
    )

    print(f"Order {order_number} saved with pending_payment status")

    return jsonify({"success": True, "message": "Order saved successfully"}), 200
