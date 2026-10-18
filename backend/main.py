from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import os
import threading
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from routers import forecast, blame, enforce, chat, vulnerable, whatif, history
from services.live_pipeline import start_background_refresh

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

app.add_middleware(
    CORSMiddleware,
    # Deployed frontends: comma-separated ALLOWED_ORIGINS. Local and LAN dev
    # servers on any port are always allowed (Next.js moves off 3000 when busy).
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|\[::1\]|10(\.\d{1,3}){3}|192\.168(\.\d{1,3}){2}|172\.(1[6-9]|2\d|3[01])(\.\d{1,3}){2})(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
