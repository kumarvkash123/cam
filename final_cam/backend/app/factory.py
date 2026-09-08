import os
from flask import Flask, request

from app.config import BASE_DIR
from app.database import SessionLocal, init_db
from app.main_routes import main_bp
from app.cam.routes import cam_bp
from app.applications_routes import applications_bp


def create_app():
    app = Flask(
        __name__,
        static_folder=str(BASE_DIR / "static"),
        template_folder=str(BASE_DIR / "templates"),
    )
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "200")) * 1024 * 1024

    frontend_origins = {
        origin.strip().rstrip("/")
        for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    }

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin", "").rstrip("/")
        if origin in frontend_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    app.register_blueprint(main_bp)
    app.register_blueprint(cam_bp)
    app.register_blueprint(applications_bp)

    with app.app_context():
        init_db()

    @app.teardown_appcontext
    def remove_session(exception=None):
        SessionLocal.remove()

    return app


app = create_app()
