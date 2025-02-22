from flask import Blueprint, render_template, request, redirect, url_for
from models import create_order, get_orders, update_order_status

app = Blueprint("app", __name__)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        location = request.form["location"]
        order_details = request.form["order"]
        preferences = request.form["preferences"]
        phone = request.form["phone"]
        create_order(name, location, order_details, preferences, phone)
        return "Order placed! Await payment confirmation."
    return render_template("index.html")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        order_id = request.form["order_id"]
        update_order_status(order_id, "confirmed")
    orders = get_orders("pending")
    return render_template("admin.html", orders=orders)
