"""Register all CAM API routes on the shared CAM blueprint."""
from app.cam.blueprint import cam_bp

# Import modules for route registration.
from app.cam.route_handlers import session_routes  # noqa: F401
from app.cam.route_handlers import policy_routes  # noqa: F401
from app.cam.route_handlers import document_routes  # noqa: F401
from app.cam.route_handlers import mca_routes  # noqa: F401
from app.cam.route_handlers import analysis_routes  # noqa: F401
from app.cam.route_handlers import generation_routes  # noqa: F401

__all__ = ["cam_bp"]
