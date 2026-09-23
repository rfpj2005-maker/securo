import uuid
from datetime import date as _Date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

FUEL_TYPES = ("flex", "gasoline", "ethanol", "diesel", "cng", "electric", "hybrid")
RECORD_KINDS = ("fuel", "maintenance", "expense")


def _check_fuel_type(v: Optional[str]) -> Optional[str]:
    if v is not None and v not in FUEL_TYPES:
        raise ValueError(f"fuel_type must be one of {FUEL_TYPES}")
    return v


def _check_kind(v: Optional[str]) -> Optional[str]:
    if v is not None and v not in RECORD_KINDS:
        raise ValueError(f"kind must be one of {RECORD_KINDS}")
    return v


def _normalize_plate(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip().upper()
    return v or None


# --- Vehicles ---------------------------------------------------------------


class VehicleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    plate: Optional[str] = Field(None, max_length=20)
    brand: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=80)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    color: Optional[str] = Field(None, max_length=30)
    fuel_type: str = "flex"
    initial_odometer: int = Field(0, ge=0)
    notes: Optional[str] = None
    is_active: bool = True

    @field_validator("fuel_type")
    @classmethod
    def validate_fuel_type(cls, v: Optional[str]) -> Optional[str]:
        return _check_fuel_type(v)

    @field_validator("plate")
    @classmethod
    def validate_plate(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_plate(v)


class VehicleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    plate: Optional[str] = Field(None, max_length=20)
    brand: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=80)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    color: Optional[str] = Field(None, max_length=30)
    fuel_type: Optional[str] = None
    initial_odometer: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("fuel_type")
    @classmethod
    def validate_fuel_type(cls, v: Optional[str]) -> Optional[str]:
        return _check_fuel_type(v)

    @field_validator("plate")
    @classmethod
    def validate_plate(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_plate(v)


class VehicleStats(BaseModel):
    current_odometer: int
    distance: int  # km driven since initial_odometer
    total_cost: Decimal
    fuel_cost: Decimal
    maintenance_cost: Decimal
    other_cost: Decimal
    total_liters: Decimal
    # Average km/L across full-tank intervals; None until two full fill-ups
    # with odometer readings exist.
    avg_consumption: Optional[Decimal] = None
    cost_per_km: Optional[Decimal] = None
    pending_reminders: int
    overdue_reminders: int


class VehicleRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    plate: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    fuel_type: str
    initial_odometer: int
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    stats: VehicleStats

    model_config = ConfigDict(from_attributes=True)


# --- Records ----------------------------------------------------------------


class VehicleRecordCreate(BaseModel):
    kind: str = "fuel"
    date: _Date
    odometer: Optional[int] = Field(None, ge=0)
    amount: Decimal = Field(Decimal("0"), ge=0)
    liters: Optional[Decimal] = Field(None, gt=0)
    full_tank: bool = True
    description: Optional[str] = Field(None, max_length=255)

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: Optional[str]) -> Optional[str]:
        return _check_kind(v)


class VehicleRecordUpdate(BaseModel):
    kind: Optional[str] = None
    date: Optional[_Date] = None
    odometer: Optional[int] = Field(None, ge=0)
    amount: Optional[Decimal] = Field(None, ge=0)
    liters: Optional[Decimal] = Field(None, gt=0)
    full_tank: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=255)

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: Optional[str]) -> Optional[str]:
        return _check_kind(v)


class VehicleRecordRead(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    kind: str
    date: _Date
    odometer: Optional[int] = None
    amount: Decimal
    liters: Optional[Decimal] = None
    full_tank: bool
    description: Optional[str] = None
    # km/L for this fill-up, when it closes a full-tank interval.
    consumption: Optional[Decimal] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Reminders --------------------------------------------------------------


class VehicleReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    due_date: Optional[_Date] = None
    due_odometer: Optional[int] = Field(None, ge=0)
    is_done: bool = False


class VehicleReminderUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    due_date: Optional[_Date] = None
    due_odometer: Optional[int] = Field(None, ge=0)
    is_done: Optional[bool] = None


class VehicleReminderRead(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    title: str
    due_date: Optional[_Date] = None
    due_odometer: Optional[int] = None
    is_done: bool
    is_overdue: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
