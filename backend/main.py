from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import os
import threading
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from routers import forecast, blame, enforce, chat, vulnerable, whatif, history
from services.live_pipeline import start_background_refresh
from models.forecaster import UnknownWardError, UnsupportedInterventionError

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_background_refresh()
    # Build the first snapshot and load SHAP before the first request needs them
    threading.Thread(target=_warm_up, daemon=True).start()
    yield

def _warm_up():
    from models.forecaster import get_ward_blame, get_city_overview
    overview = get_city_overview()
    if overview:
        get_ward_blame(overview[0]["ward_id"])

app = FastAPI(
    lifespan=lifespan,
    title="Atmos API",
    description="Backend for Atmos — Urban Air Quality Intelligence for Delhi",
    version="0.1.0",
)

# The API serves public, read-only data and the frontend sends no cookies, so
# any site may call it by default. Set ALLOWED_ORIGINS (comma-separated) to
# restrict it to specific frontends; local/LAN dev servers stay allowed then.
_allowed = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed or ["*"],
    allow_origin_regex=(
        r"https?://(localhost|127\.0\.0\.1|\[::1\]|10(\.\d{1,3}){3}|192\.168(\.\d{1,3}){2}|172\.(1[6-9]|2\d|3[01])(\.\d{1,3}){2})(:\d+)?"
        if _allowed else None
    ),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(UnknownWardError)
async def unknown_ward_handler(request: Request, exc: UnknownWardError):
    return JSONResponse(status_code=404, content={"detail": f"Unknown ward_id '{exc.ward_id}'"})


@app.exception_handler(UnsupportedInterventionError)
async def unsupported_intervention_handler(request: Request, exc: UnsupportedInterventionError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


app.include_router(forecast.router)
app.include_router(blame.router)
app.include_router(enforce.router)
app.include_router(chat.router)
app.include_router(vulnerable.router)
app.include_router(whatif.router)
app.include_router(history.router)

@app.get("/api/health", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
