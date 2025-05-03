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
import json
import uuid
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
    create_toppings_table,
    get_toppings,
    add_topping,
    update_topping,
    delete_topping,
    populate_default_toppings,
)
from werkzeug.security import check_password_hash
import random
import string
from werkzeug.utils import secure_filename
from functools import wraps
from config import Config
import base64
import urllib.parse
from forms import LoginForm
import logging

# Set up a proper logger instead of using print statements
logger = logging.getLogger("boba_app")
logger.setLevel(logging.INFO)


# Create a factory function that returns a blueprint with limiter applied
def create_routes(limiter):
    # Create a Blueprint named "app"
    app = Blueprint("app", __name__)

    HUBTEL_CLIENT_ID = Config.HUBTEL_CLIENT_ID
    HUBTEL_CLIENT_SECRET = Config.HUBTEL_CLIENT_SECRET
    HUBTEL_SENDER_ID = Config.HUBTEL_SENDER_ID
    HUBTEL_API_URL = "https://smsc.hubtel.com/v1/messages/send"

    api_id = Config.HUBTEL_API_ID
    api_key = Config.HUBTEL_API_KEY

    # api id and api key converted to base64
    credentials = f"{api_id}:{api_key}"
    basic_auth = base64.b64encode(credentials.encode()).decode()

    def initiate_hubtel_payment(
        total_amount,
        description,
        callback_url,
        return_url,
        client_reference,
        customer_name=None,
        customer_phone=None,
    ):
        """Initiate Hubtel payment with reference according to official Hubtel documentation"""
        # Format the API credentials - remove any whitespace
        api_id = Config.HUBTEL_API_ID.strip() if Config.HUBTEL_API_ID else ""
        api_key = Config.HUBTEL_API_KEY.strip() if Config.HUBTEL_API_KEY else ""
        merchant_account = (
            Config.HUBTEL_MERCHANT_ACCOUNT.strip()
            if Config.HUBTEL_MERCHANT_ACCOUNT
            else ""
        )

        # Prepare headers
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {basic_auth}",
            "Cache-Control": "no-cache",
        }

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
            response = requests.post(
                Config.HUBTEL_CHECKOUT_URL, json=payload, headers=headers
            )

            if response.status_code == 401:
                logger.error("Authentication failed with Hubtel API")
                return None

            response.raise_for_status()

            response_data = response.json()
            return response_data.get("data", {}).get("checkoutDirectUrl")

        except requests.exceptions.RequestException as e:
            logger.error(f"Payment request error: {e}")
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
            logger.error(f"Payment status check failed: {e}")
            return None

    def generate_order_number():
        """Generate a unique numeric order number for Hubtel compatibility"""
        # Generate a random 8-digit number
        numeric_id = "".join(random.choices(string.digits, k=8))
        return numeric_id

    def login_required(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "admin_id" not in session:
                flash("You must be logged in to access this page.", "error")
                return redirect(url_for("app.login"))
            return view(*args, **kwargs)

        return wrapped_view

    def format_order_details(customer_name, order_details):
        # Process and format each item in the order - no emojis
        items = order_details.split(", ")
        formatted_items = "\n".join([item.strip() for item in items])

        # Final SMS message without emojis
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
        # Read credentials directly from the Config object to ensure they match .env values
        client_id = Config.HUBTEL_CLIENT_ID.strip()
        client_secret = Config.HUBTEL_CLIENT_SECRET.strip()
        sender_id = Config.HUBTEL_SENDER_ID.strip()

        # Make sure we're using sms.hubtel.com
        url = "https://sms.hubtel.com/v1/messages/send"

        # URL encode the message content
        encoded_message = urllib.parse.quote_plus(message)

        # Build the request URL with the correct credentials from .env
        full_url = f"{url}?clientsecret={client_secret}&clientid={client_id}&from={sender_id}&to={to}&content={encoded_message}"

        try:
            response = requests.get(full_url)
            # Parse response data
            response_data = response.json()

            # Check for successful SMS submission based on Hubtel's actual response format
            if (response.status_code in [200, 201]) and response_data.get(
                "status"
            ) == 0:
                logger.info(f"SMS sent successfully to {to}")
                return True
            else:
                error_description = response_data.get(
                    "statusDescription", "Unknown error"
                )
                logger.error(f"Failed to send SMS: {error_description}")
                return False

        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False

    @app.route("/generate-order-number")
    def generate_order_number_route():
        """Generate a unique numeric order number (for Hubtel compatibility)"""
        order_number = "".join(
            random.choices(string.digits, k=8)
        )  # 8-digit random number
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
        hq_special_items = [
            product
            for product in all_products
            if product["category"] == "HQ Special" and product["in_stock"]
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
            logger.info(
                f"New order {order_number} received with payment method: {payment_status}"
            )

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
                # Send SMS with formatted phone number
                send_sms_hubtel(formatted_phone, formatted_message)
                logger.info(f"SMS sent for pay-on-delivery order {order_number}")
            else:
                logger.info(f"SMS deferred for online payment order {order_number}")

            return redirect(
                url_for(
                    "app.order_confirmation", total=total, order_number=order_number
                )
            )

        return render_template(
            "index.html",
            boba_items=boba_items,
            ice_tea_items=ice_tea_items,
            shawarma_items=shawarma_items,
            hq_special_items=hq_special_items,
        )

    @app.route("/order-confirmation")
    def order_confirmation():
        total = request.args.get("total")
        order_number = request.args.get("order_number")
        return render_template(
            "order_confirmation.html", total=total, order_number=order_number
        )

    @app.route("/login", methods=["GET", "POST"])
    # Apply strict rate limiting to the login route to prevent brute force attacks
    @limiter.limit("5 per minute, 20 per hour")
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data

            admin = get_admin_by_username(username)
            if admin and check_password_hash(admin["password_hash"], password):
                session["admin_id"] = admin["id"]
                session["username"] = admin["username"]
                flash("Logged in successfully!", "success")
                return redirect("/admin")
            else:
                flash("Invalid username or password.", "error")

        return render_template("login.html", form=form)

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
    A rider will call you soon.

    Order Reference: {order_number}

    Your taste buds are in for a treat!

    Need help? Chat with us on WhatsApp: (https://wa.me/233536440126)  
    """
                    # Format the phone number to international format
                    formatted_phone = format_phone_number(customer_phone)
                    logger.info(
                        f"Sending order ready SMS to {formatted_phone} (original: {customer_phone})"
                    )

                    # Send SMS with formatted phone number
                    send_sms_hubtel(formatted_phone, message)

            elif action == "cancel":
                cancel_order(order_id)
                logger.info(f"Order {order_id} cancelled")

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
                image_url = upload_image_to_cloudinary(file)  # Updated function call
                if image_url:
                    logger.info(f"Image uploaded successfully: {image_url}")
                else:
                    logger.error("Image upload failed")

            if product_id:  # If updating a product
                update_product(product_id, name, category, in_stock, image_url)
                logger.info(f"Product {name} (ID: {product_id}) updated")
            else:  # If adding a new product
                add_product(name, image_url, category, in_stock)
                logger.info(f"New product {name} added")

            return redirect(url_for("app.admin_products"))

        products = get_products()
        return render_template("admin_products.html", products=products)

    @app.route("/admin/delete_product/<int:product_id>", methods=["POST"])
    def delete_product_route(product_id):
        delete_product(product_id)
        logger.info(f"Product {product_id} deleted")
        return redirect(url_for("app.admin_products"))

    @app.route("/update-payment", methods=["POST"])
    def update_payment():
        data = request.json
        order_number = data.get("order_number")
        payment_method = data.get("payment_method")

        update_payment_status(order_number, payment_method)
        logger.info(
            f"Payment status for order {order_number} updated to {payment_method}"
        )

        return {"message": "Payment updated successfully"}, 200

    @app.route("/hubtel-payment", methods=["POST"])
    def hubtel_payment():
        data = request.json
        order_number = data.get("order_number")
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
            "clientReference": order_number,  # Use the numeric order number directly
        }

        # Add optional parameters if provided
        if name:
            payload["payeeName"] = name
        if phone:
            payload["payeeMobileNumber"] = phone

        try:
            logger.info(f"Initiating payment for order {order_number}")

            response = requests.post(
                Config.HUBTEL_CHECKOUT_URL,
                json=payload,
                headers=headers,
            )

            response.raise_for_status()

            response_data = response.json()
            checkout_url = response_data.get("data", {}).get("checkoutUrl")

            if not checkout_url:
                logger.error(f"No checkout URL received for order {order_number}")
                return jsonify({"error": "No checkout URL received"}), 500

            logger.info(f"Payment initiated for order {order_number}")
            return jsonify({"checkout_url": checkout_url})

        except requests.exceptions.RequestException as e:
            logger.error(f"Hubtel API error for order {order_number}: {e}")
            return jsonify({"error": "Payment initiation failed"}), 500

    @app.route("/hubtel-callback", methods=["POST"])
    def hubtel_callback():
        """Handle Hubtel payment notifications and store all data"""
        logger.info("Hubtel payment callback received")

        try:
            # Capture raw request first
            raw_data = request.get_data(as_text=True)

            # Parse JSON data
            data = request.json

            # Validate we have basic structure
            if not all(field in data for field in ["ResponseCode", "Status"]):
                logger.error("Missing required top-level fields in callback data")
                return jsonify({"error": "Missing required fields"}), 400

            # Save everything to database (including failed transactions)
            try:
                save_transaction_record(data, raw_request=raw_data)
                logger.info("Transaction saved to database")
            except Exception as db_error:
                logger.error(f"Database save error: {str(db_error)}")

            # Only process successful transactions further
            if (
                data["ResponseCode"] == "0000"
                and data.get("Status", "").lower() == "success"
            ):
                transaction_data = data.get("Data", {})
                order_number = transaction_data.get("ClientReference", "")

                if order_number:
                    logger.info(
                        f"Processing successful payment for order: {order_number}"
                    )

                    try:
                        # Update order payment method to 'paid'
                        update_payment_status(order_number, "paid")
                        logger.info(
                            f"Order {order_number} payment status updated to 'paid'"
                        )

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
                            logger.info(
                                f"Payment confirmation SMS sent for order {order_number}"
                            )
                        else:
                            logger.error(f"Order {order_number} not found in database")
                    except Exception as processing_error:
                        logger.error(
                            f"Error processing transaction: {str(processing_error)}"
                        )

            return jsonify({"status": "received"}), 200

        except Exception as e:
            logger.error(f"Critical error in hubtel callback: {str(e)}")
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

            headers = {
                "Authorization": f"Basic {basic_auth}",
                "Accept": "application/json",
            }

            logger.info(f"Checking payment status for order {client_reference}")

            # Make the request directly to Hubtel
            response = requests.get(url, headers=headers, timeout=15)

            # Handle response appropriately
            if response.status_code == 403 or response.status_code == 401:
                logger.error(
                    f"Authentication failed for payment status check: {response.status_code}"
                )
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
            }

            return jsonify(simplified_response)

        except requests.exceptions.RequestException as e:
            logger.error(f"Hubtel API request error: {str(e)}")
            return (
                jsonify({"error": "Hubtel API request failed", "details": str(e)}),
                502,
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Hubtel: {str(e)}")
            return (
                jsonify({"error": "Invalid response from Hubtel", "details": str(e)}),
                500,
            )
        except Exception as e:
            logger.error(f"Internal server error: {str(e)}")
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
        if (
            not name
            or not location
            or not order_details
            or not phone
            or not order_number
        ):
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

        logger.info(f"Order {order_number} saved with pending_payment status")

        return jsonify({"success": True, "message": "Order saved successfully"}), 200

    @app.route("/admin/pending-orders-count")
    @login_required
    def pending_orders_count():
        """Return the count of pending orders as JSON."""
        orders = get_orders(status="pending")
        return jsonify({"count": len(orders)})

    @app.route("/admin/toppings", methods=["GET", "POST"])
    @login_required
    def admin_toppings():
        """Admin view for managing toppings"""
        # Create toppings table if it doesn't exist
        create_toppings_table()

        # On first load, populate default toppings

        populate_default_toppings()

        if request.method == "POST":
            topping_id = request.form.get("topping_id")  # If editing
            name = request.form.get("name")
            in_stock = request.form.get("in_stock") == "on"

            if topping_id:  # If updating
                update_topping(topping_id, name, in_stock)
            else:  # If adding new
                add_topping(name, in_stock)

            return redirect(url_for("app.admin_toppings"))

        toppings = get_toppings()
        return render_template("admin_toppings.html", toppings=toppings)

    @app.route("/admin/delete_topping/<int:topping_id>", methods=["POST"])
    @login_required
    def delete_topping_route(topping_id):
        """Delete a topping"""
        delete_topping(topping_id)
        return redirect(url_for("app.admin_toppings"))

    @app.route("/get_available_toppings", methods=["GET"])
    def get_available_toppings():
        """API endpoint to get all available (in stock) toppings"""
        try:
            # Get all toppings first
            all_toppings = get_toppings()

            # Filter to only in-stock ones
            available_toppings = [
                topping for topping in all_toppings if topping["in_stock"]
            ]

            return jsonify(available_toppings)
        except Exception as e:
            logger.error(f"Error in get_available_toppings: {str(e)}")
            # Return an empty list rather than an error to prevent breaking the UI
            return jsonify([])

    return app
