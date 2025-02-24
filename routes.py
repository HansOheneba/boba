from flask import Blueprint, render_template, request, redirect, url_for
from models import (
    create_order,
    get_orders,
    update_order_status,
    confirm_order,
    cancel_order,
)
import random
import string

app = Blueprint("app", __name__)


def generate_order_number():
    chars = string.ascii_lowercase + string.digits
    return "boba-" + "".join(random.choice(chars) for _ in range(4))


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name")
        location = request.form.get("location")
        order_details = request.form.get("order")
        notes = request.form.get("notes")
        phone = request.form.get("phone")
        total = request.form.get("total")
        order_number = generate_order_number()

        if not name or not location or not order_details or not phone:
            return "All fields are required", 400

        create_order(name, location, order_details, notes, phone, total, order_number)
        return redirect(
            url_for("app.order_confirmation", total=total, order_number=order_number)
        )

    return render_template("index.html")


@app.route("/order-confirmation")
def order_confirmation():
    total = request.args.get("total")
    order_number = request.args.get("order_number")
    return render_template(
        "order_confirmation.html", total=total, order_number=order_number
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        order_id = request.form.get("order_id")
        action = request.form.get("action")
        if action == "confirm":
            confirm_order(order_id)
        elif action == "cancel":
            cancel_order(order_id)

    orders = get_orders("pending")
    return render_template("admin.html", orders=orders)
