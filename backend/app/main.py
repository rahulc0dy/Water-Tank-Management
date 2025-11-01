"""FastAPI backend serving telemetry saved by the automation script."""
import os
from datetime import datetime
from typing import Dict, List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from .analytics import compute_dashboard_metrics
from .db import (
    authenticate_user,
    create_user,
    ensure_default_user,
    get_db_path,
    get_user,
    init_db,
)
from .storage import FileBackedTelemetryStore, default_store

MAX_HISTORY = int(os.getenv("WATERTANK_HISTORY_SIZE", "0"))

app = FastAPI(title="Water Tank Backend", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust when you know the frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

security = HTTPBasic()


class TelemetrySample(BaseModel):
    timestamp: datetime
    water_level_percent: float
    pump_state: int
    leak_detected: bool
    raw_payload: str


class UserCredentials(BaseModel):
    username: str
    password: str


telemetry_store: FileBackedTelemetryStore = default_store(MAX_HISTORY)


def require_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    username = credentials.username or ""
    password = credentials.password or ""
    if not authenticate_user(username, password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return username


@app.on_event("startup")
async def startup_event() -> None:
    init_db()
    ensure_default_user()


@app.get("/health")
async def healthcheck() -> Dict[str, str]:
    return {
        "status": "ok",
        "data_file": str(telemetry_store.path),
        "database_file": str(get_db_path()),
    }


@app.post("/auth/register")
async def register_user(payload: UserCredentials) -> Dict[str, str]:
    try:
        create_user(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"message": "User registered", "username": payload.username.strip().lower()}


@app.post("/auth/login")
async def login_user(payload: UserCredentials) -> Dict[str, str]:
    if not authenticate_user(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    user = get_user(payload.username)
    return {
        "message": "Login successful",
        "username": user["username"] if user else payload.username,
        "last_login": user["last_login"] if user else None,
    }


@app.get("/telemetry/latest", response_model=TelemetrySample)
async def latest_sample(_: str = Depends(require_user)) -> TelemetrySample:
    latest_raw = telemetry_store.latest()
    if latest_raw is None:
        raise HTTPException(status_code=404, detail="No telemetry available yet")
    return TelemetrySample.model_validate(latest_raw)


@app.get("/telemetry/history", response_model=List[TelemetrySample])
async def history(limit: int = 100, _: str = Depends(require_user)) -> List[TelemetrySample]:
    samples = telemetry_store.history(limit if limit > 0 else None)
    return [TelemetrySample.model_validate(sample) for sample in samples]


@app.post("/telemetry/ingest", response_model=TelemetrySample)
async def ingest(sample: TelemetrySample, _: str = Depends(require_user)) -> TelemetrySample:
    telemetry_store.append(sample.model_dump(mode="json"))
    return sample


@app.get("/dashboard/metrics")
async def dashboard_metrics(_: str = Depends(require_user)) -> Dict[str, object]:
    samples = telemetry_store.history(None)
    return compute_dashboard_metrics(samples)


@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Water Tank backend is running"}
