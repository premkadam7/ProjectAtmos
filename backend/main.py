from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import uvicorn

from routers import forecast, blame, enforce, chat, vulnerable, whatif

app = FastAPI(
    title="Atmos API",
    description="Backend for Atmos — Urban Air Quality Intelligence for Delhi",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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

@app.get("/api/health", tags=["health"])
def health_check():
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
