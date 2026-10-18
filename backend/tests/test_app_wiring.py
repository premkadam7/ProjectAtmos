"""The production app itself must expose every route the frontend and tests rely on (F22)."""
from main import app

REQUIRED_ROUTES = {
    ("GET", "/api/health"),
    ("GET", "/api/forecast/{city}"),
    ("GET", "/api/forecast/{city}/timeline"),
    ("GET", "/api/forecast/{city}/{ward_id}"),
    ("GET", "/api/history/{city}"),
    ("GET", "/api/blame/{city}/{ward_id}"),
    ("GET", "/api/enforce/{city}"),
    ("GET", "/api/vulnerable/{city}"),
    ("POST", "/api/whatif"),
    ("POST", "/api/chat"),
}


def test_production_app_has_all_routes():
    # The OpenAPI schema lists every mounted route, including nested routers
    present = {(m.upper(), path) for path, ops in app.openapi()["paths"].items() for m in ops}
    missing = REQUIRED_ROUTES - present
    assert not missing, f"Routes missing from main.app: {sorted(missing)}"
