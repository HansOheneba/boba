from flask import Flask, session, flash, redirect, url_for
from routes import app as routes_app
from config import Config
from flask_caching import Cache

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Configure caching
app.config["CACHE_TYPE"] = "SimpleCache"  # Simple in-memory cache
app.config["CACHE_DEFAULT_TIMEOUT"] = 300  # Default cache timeout (5 minutes)
cache = Cache(app)

app.config["UPLOAD_FOLDER"] = "static/img/"
# Register routes
app.register_blueprint(routes_app)

# Make cache available to routes
from routes import set_cache
set_cache(cache)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
