import os
from datetime import timedelta
from flask import Flask
from dotenv import load_dotenv
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from flask_socketio import SocketIO

load_dotenv()

from config import Config, get_db
from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.communities_routes import communities_bp
from routes.communities_routes import register_chat_socket_handlers
from routes.requests_routes import requests_bp
from routes.ratings_routes import ratings_bp
from routes.messaging_routes import messaging_bp
from routes.analytics_routes import analytics_bp
from models.user_model import get_user_object_by_id


socketio = SocketIO(async_mode="threading", cors_allowed_origins="*")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

    # Initialize shared database handle for all blueprints.
    app.db = get_db()

    oauth = OAuth(app)
    app.oauth = oauth
    if app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET"):
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return get_user_object_by_id(app.db, user_id)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(communities_bp)
    app.register_blueprint(ratings_bp)
    app.register_blueprint(messaging_bp)
    app.register_blueprint(analytics_bp)

    socketio.init_app(app)
    register_chat_socket_handlers(socketio)

    os.makedirs("static/generated", exist_ok=True)

    return app


if __name__ == "__main__":
    flask_app = create_app()
    socketio.run(flask_app, debug=True)
