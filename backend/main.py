from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List
import secrets

from . import models, schemas
from .database import SessionLocal, engine, get_db

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Water Tank Management API")

# --- CORS Middleware ---
# Allows the Next.js frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust for your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authentication ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBasic()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_current_user(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user

# --- API Routes ---

@app.post("/users/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/users/login")
def login(user_login: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == user_login.username).first()
    if not user or not verify_password(user_login.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"username": user.username, "last_login": None}

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """A simple endpoint to verify credentials."""
    return current_user

@app.post("/telemetry/", response_model=schemas.Telemetry, status_code=status.HTTP_201_CREATED)
def create_telemetry_reading(telemetry: schemas.TelemetryCreate, db: Session = Depends(get_db)):
    """Endpoint for automation.py to post new data."""
    db_telemetry = models.Telemetry(**telemetry.model_dump())
    db.add(db_telemetry)
    db.commit()
    db.refresh(db_telemetry)
    return db_telemetry

@app.get("/telemetry/history", response_model=List[schemas.Telemetry])
def get_telemetry_history(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Get historical data for graphs."""
    return db.query(models.Telemetry).order_by(models.Telemetry.timestamp.desc()).offset(skip).limit(limit).all()

@app.get("/dashboard/metrics", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Provides aggregated data for the dashboard UI."""
    
    # Get latest reading
    latest = db.query(models.Telemetry).order_by(models.Telemetry.timestamp.desc()).first()
    if not latest:
        return schemas.DashboardMetrics(
            current_level=0, current_pump_state=0, usage_past_24h_liters=0, all_time_usage_liters=0, hourly_avg_usage={}
        )

    # Calculate usage (assuming 1% drop = 10 liters for a 1000L tank)
    # This is a simplification; real usage depends on tank geometry.
    LITERS_PER_PERCENT = 10 

    # 24-hour usage
    day_ago = datetime.utcnow() - timedelta(days=1)
    readings_24h = db.query(models.Telemetry).filter(models.Telemetry.timestamp >= day_ago).order_by(models.Telemetry.timestamp.asc()).all()
    usage_24h = sum(max(0, r_prev.water_level_percent - r_curr.water_level_percent) * LITERS_PER_PERCENT 
                    for r_prev, r_curr in zip(readings_24h, readings_24h[1:]) if r_curr.pump_state == 0)

    # All-time usage
    all_readings = db.query(models.Telemetry).order_by(models.Telemetry.timestamp.asc()).all()
    all_time_usage = sum(max(0, r_prev.water_level_percent - r_curr.water_level_percent) * LITERS_PER_PERCENT 
                         for r_prev, r_curr in zip(all_readings, all_readings[1:]) if r_curr.pump_state == 0)

    # Hourly average usage
    hourly_usage = {h: 0.0 for h in range(24)}
    hourly_counts = {h: 0 for h in range(24)}
    # This is a simplified approach. A real implementation might use more advanced SQL grouping.
    for r_prev, r_curr in zip(all_readings, all_readings[1:]):
        if r_curr.pump_state == 0:
            usage = max(0, r_prev.water_level_percent - r_curr.water_level_percent) * LITERS_PER_PERCENT
            if usage > 0:
                hour = r_curr.timestamp.hour
                hourly_usage[hour] += usage
                hourly_counts[hour] += 1
    
    hourly_avg = {h: (hourly_usage[h] / hourly_counts[h]) if hourly_counts[h] > 0 else 0 for h in range(24)}

    return schemas.DashboardMetrics(
        current_level=latest.water_level_percent,
        current_pump_state=latest.pump_state,
        usage_past_24h_liters=usage_24h,
        all_time_usage_liters=all_time_usage,
        hourly_avg_usage=hourly_avg,
    )
