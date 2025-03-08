from flask import Flask, session, flash, redirect, url_for
from routes import app as routes_app
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)


app.config["UPLOAD_FOLDER"] = "static/img/"
# Register routes
app.register_blueprint(routes_app)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
