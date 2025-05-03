from flask import Flask
from flask_wtf.csrf import CSRFProtect
from config import Config
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
import os

# Create the Flask application
app = Flask(__name__)

# Configure secret key for sessions and CSRF protection
app.config["SECRET_KEY"] = (
    Config.SECRET_KEY
)  # Make sure this exists in your Config class
app.config["WTF_CSRF_ENABLED"] = True

# Enhance session security
app.config["SESSION_COOKIE_SECURE"] = True  # HTTPS only
app.config["SESSION_COOKIE_HTTPONLY"] = True  # No JavaScript access
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # Control cross-origin usage
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)  # Session timeout

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window",
)

app.config["UPLOAD_FOLDER"] = "static/img/"

# Import and register blueprints after initializing Flask app and limiter
# This avoids circular imports
from routes import create_routes

blueprint = create_routes(limiter)
app.register_blueprint(blueprint)

if __name__ == "__main__":
    # Only use debug mode in development, not in production
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug_mode, host="0.0.0.0", port=5001)
