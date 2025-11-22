from typing import List, Optional, Dict
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

class DashboardUsageSlice(BaseModel):
    percent: float
    liters: Optional[float] = None

class UsagePerHour(DashboardUsageSlice):
    hour: int

class UsagePerDay(DashboardUsageSlice):
    date: str

class DashboardUsage(BaseModel):
    last_24h: DashboardUsageSlice
    all_time: DashboardUsageSlice
    per_hour: List[UsagePerHour]
    per_day: List[UsagePerDay]

class DashboardLatest(BaseModel):
    timestamp: datetime
    water_level_percent: float
    pump_state: int
    leak_detected: bool
    water_level_liters: Optional[float] = None

class DashboardPumpStateSummary(BaseModel):
    on: int
    off: int

class DashboardWaterLevel(BaseModel):
    timestamp: datetime
    water_level_percent: float
    water_level_liters: Optional[float] = None

class DashboardMetrics(BaseModel):
    latest: Optional[DashboardLatest]
    sample_count: int
    usage: DashboardUsage
    water_levels: List[DashboardWaterLevel]
    pump_state_summary: DashboardPumpStateSummary
    leak_events: int