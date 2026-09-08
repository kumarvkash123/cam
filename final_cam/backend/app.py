"""WSGI/CLI entry point for the modular CAM backend."""
import os
from app import app


if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "1") == "1",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
