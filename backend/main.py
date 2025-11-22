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
    
    LITERS_PER_PERCENT = 10.0 # 1000L tank / 100%

    # Get latest reading
    latest = db.query(models.Telemetry).order_by(models.Telemetry.timestamp.desc()).first()
    
    # Get all readings for calculations (optimize this in production)
    all_readings = db.query(models.Telemetry).order_by(models.Telemetry.timestamp.asc()).all()
    
    if not latest:
        # Return empty structure
        empty_usage = schemas.DashboardUsage(
            last_24h=schemas.DashboardUsageSlice(percent=0, liters=0),
            all_time=schemas.DashboardUsageSlice(percent=0, liters=0),
            per_hour=[],
            per_day=[]
        )
        return schemas.DashboardMetrics(
            latest=None,
            sample_count=0,
            usage=empty_usage,
            water_levels=[],
            pump_state_summary=schemas.DashboardPumpStateSummary(on=0, off=0),
            leak_events=0
        )

    # Helper to calculate usage
    def calculate_usage(readings):
        usage_percent = 0.0
        for r_prev, r_curr in zip(readings, readings[1:]):
            # Only count drops when pump is OFF
            if r_curr.pump_state == 0 and r_prev.water_level_percent > r_curr.water_level_percent:
                usage_percent += (r_prev.water_level_percent - r_curr.water_level_percent)
        return usage_percent

    # 24-hour usage
    day_ago = datetime.utcnow() - timedelta(days=1)
    readings_24h = [r for r in all_readings if r.timestamp >= day_ago]
    usage_24h_percent = calculate_usage(readings_24h)
    
    # All-time usage
    usage_all_time_percent = calculate_usage(all_readings)

    # Per hour usage (last 24h)
    usage_by_hour = {}
    for r_prev, r_curr in zip(readings_24h, readings_24h[1:]):
        if r_curr.pump_state == 0 and r_prev.water_level_percent > r_curr.water_level_percent:
            hour = r_curr.timestamp.hour
            diff = r_prev.water_level_percent - r_curr.water_level_percent
            usage_by_hour[hour] = usage_by_hour.get(hour, 0.0) + diff
            
    per_hour_usage = [
        schemas.UsagePerHour(hour=h, percent=p, liters=p * LITERS_PER_PERCENT)
        for h, p in usage_by_hour.items()
    ]

    # Per day usage (all time)
    usage_by_day = {}
    for r_prev, r_curr in zip(all_readings, all_readings[1:]):
        if r_curr.pump_state == 0 and r_prev.water_level_percent > r_curr.water_level_percent:
            date_str = r_curr.timestamp.strftime('%Y-%m-%d')
            diff = r_prev.water_level_percent - r_curr.water_level_percent
            usage_by_day[date_str] = usage_by_day.get(date_str, 0.0) + diff

    per_day_usage = [
        schemas.UsagePerDay(date=d, percent=p, liters=p * LITERS_PER_PERCENT)
        for d, p in usage_by_day.items()
    ]
    
    # Pump state summary
    pump_on_count = sum(1 for r in all_readings if r.pump_state == 1)
    pump_off_count = sum(1 for r in all_readings if r.pump_state == 0)

    # Water levels (last 24h for graph)
    water_levels = [
        schemas.DashboardWaterLevel(
            timestamp=r.timestamp,
            water_level_percent=r.water_level_percent,
            water_level_liters=r.water_level_percent * LITERS_PER_PERCENT
        ) for r in readings_24h
    ]

    return schemas.DashboardMetrics(
        latest=schemas.DashboardLatest(
            timestamp=latest.timestamp,
            water_level_percent=latest.water_level_percent,
            pump_state=latest.pump_state,
            leak_detected=False, # Placeholder
            water_level_liters=latest.water_level_percent * LITERS_PER_PERCENT
        ),
        sample_count=len(all_readings),
        usage=schemas.DashboardUsage(
            last_24h=schemas.DashboardUsageSlice(
                percent=usage_24h_percent, 
                liters=usage_24h_percent * LITERS_PER_PERCENT
            ),
            all_time=schemas.DashboardUsageSlice(
                percent=usage_all_time_percent, 
                liters=usage_all_time_percent * LITERS_PER_PERCENT
            ),
            per_hour=per_hour_usage,
            per_day=per_day_usage
        ),
        water_levels=water_levels,
        pump_state_summary=schemas.DashboardPumpStateSummary(
            on=pump_on_count,
            off=pump_off_count
        ),
        leak_events=0
    )
