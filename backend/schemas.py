from pydantic import BaseModel
from datetime import datetime

class TelemetryBase(BaseModel):
    water_level_percent: float
    pump_state: int

class TelemetryCreate(TelemetryBase):
    pass

class Telemetry(TelemetryBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        from_attributes = True

class DashboardMetrics(BaseModel):
    current_level: float
    current_pump_state: int
    usage_past_24h_liters: float
    all_time_usage_liters: float
    hourly_avg_usage: dict[int, float]