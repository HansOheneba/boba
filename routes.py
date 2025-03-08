from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import os
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
)
from werkzeug.security import check_password_hash
import random
import string
from werkzeug.utils import secure_filename
from flask import current_app
from functools import wraps


# Create a Blueprint named "app"
app = Blueprint("app", __name__)


def generate_order_number():
    chars = string.ascii_lowercase + string.digits
    return "boba-" + "".join(random.choice(chars) for _ in range(4))


def login_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "admin_id" not in session:
            flash("You must be logged in to access this page.", "error")
            return redirect(url_for("app.login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/", methods=["GET", "POST"])
def index():
    all_products = get_products()
    boba_items = [
        product
        for product 
        in all_products
        if product["category"] == "Bubble Tea" 
        and product["in_stock"]
    ]
    ice_tea_items = [
        product 
        for product in all_products 
        if product["category"] == "Ice Tea" 
        and product["in_stock"]
    ]
    shawarma_items = [
        product 
        for product 
        in all_products 
        if product["category"] == "Shawarma" 
        and product["in_stock"]
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
        order_number = generate_order_number()

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
        )
        return redirect(
            url_for("app.order_confirmation", total=total, order_number=order_number)
        )

    return render_template("index.html", boba_items=boba_items, ice_tea_items=ice_tea_items, shawarma_items=shawarma_items)


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
            confirm_order(order_id)
        elif action == "cancel":
            cancel_order(order_id)

        return redirect("/admin")

    # Handle filtering and search
    status_filter = request.args.get("status", "")
    search_query = request.args.get("search", "")

    # Fetch orders sorted by latest first
    orders = get_orders(status=status_filter)

    # Filter by search query
    if search_query:
        orders = [
            order
            for order in orders
            if search_query.lower() in order["order_number"].lower()
        ]

    return render_template("admin.html", orders=orders)

UPLOAD_FOLDER = "static/img/"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/admin/products", methods=["GET", "POST"])
@login_required
def admin_products():
    if request.method == "POST":
        product_id = request.form.get("product_id")  # If editing

        name = request.form["name"]
        category = request.form["category"]
        in_stock = request.form.get("in_stock") == "on"

        # File handling
        file = request.files["image"]
        image_path = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
            image_path = f"img/{filename}"

        if product_id:  # Edit existing product
            update_product(product_id, name, category, in_stock, image_path)
        else:  # Add new product
            add_product(name, image_path, category, in_stock)

        return redirect(url_for("app.admin_products"))

    products = get_products()
    return render_template("admin_products.html", products=products)


@app.route("/admin/delete_product/<int:product_id>", methods=["POST"])
def delete_product_route(product_id):
    delete_product(product_id)
    return redirect(url_for("admin_products"))
