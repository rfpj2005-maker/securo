import uuid
from datetime import date as _Date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    tank_capacity: Optional[Decimal] = Field(None, gt=0)
    chassis: Optional[str] = Field(None, max_length=30)
    renavam: Optional[str] = Field(None, max_length=20)
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
    tank_capacity: Optional[Decimal] = Field(None, gt=0)
    chassis: Optional[str] = Field(None, max_length=30)
    renavam: Optional[str] = Field(None, max_length=20)
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
    trip_count: int = 0
    # Inspections where the driver flagged something (document missing,
    # tyres, coolant, broken items) — the latest one per vehicle matters most.
    last_inspection_at: Optional[datetime] = None
    last_inspection_has_issue: bool = False


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
    tank_capacity: Optional[Decimal] = None
    chassis: Optional[str] = None
    renavam: Optional[str] = None
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
    driver: Optional[str] = Field(None, max_length=100)
    place: Optional[str] = Field(None, max_length=150)
    payment_method: Optional[str] = Field(None, max_length=80)
    purpose: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None

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
    driver: Optional[str] = Field(None, max_length=100)
    place: Optional[str] = Field(None, max_length=150)
    payment_method: Optional[str] = Field(None, max_length=80)
    purpose: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None

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
    driver: Optional[str] = None
    place: Optional[str] = None
    payment_method: Optional[str] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None
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


# --- Trips ------------------------------------------------------------------


class VehicleTripCreate(BaseModel):
    started_at: datetime
    ended_at: Optional[datetime] = None
    start_odometer: int = Field(..., ge=0)
    end_odometer: int = Field(..., ge=0)
    origin: Optional[str] = Field(None, max_length=150)
    destination: Optional[str] = Field(None, max_length=150)
    driver: Optional[str] = Field(None, max_length=100)
    purpose: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def check_odometers(self) -> "VehicleTripCreate":
        if self.end_odometer < self.start_odometer:
            raise ValueError("end_odometer must be greater than or equal to start_odometer")
        return self


class VehicleTripUpdate(BaseModel):
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    start_odometer: Optional[int] = Field(None, ge=0)
    end_odometer: Optional[int] = Field(None, ge=0)
    origin: Optional[str] = Field(None, max_length=150)
    destination: Optional[str] = Field(None, max_length=150)
    driver: Optional[str] = Field(None, max_length=100)
    purpose: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class VehicleTripRead(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    start_odometer: int
    end_odometer: int
    distance: int
    origin: Optional[str] = None
    destination: Optional[str] = None
    driver: Optional[str] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Inspections ------------------------------------------------------------


class VehicleInspectionCreate(BaseModel):
    inspected_at: datetime
    odometer: Optional[int] = Field(None, ge=0)
    driver: Optional[str] = Field(None, max_length=100)
    documents_ok: Optional[bool] = None
    tires_ok: Optional[bool] = None
    coolant_checked: Optional[bool] = None
    failing_items: Optional[str] = Field(None, max_length=255)
    other_problem: Optional[str] = None
    notes: Optional[str] = None


class VehicleInspectionUpdate(BaseModel):
    inspected_at: Optional[datetime] = None
    odometer: Optional[int] = Field(None, ge=0)
    driver: Optional[str] = Field(None, max_length=100)
    documents_ok: Optional[bool] = None
    tires_ok: Optional[bool] = None
    coolant_checked: Optional[bool] = None
    failing_items: Optional[str] = Field(None, max_length=255)
    other_problem: Optional[str] = None
    notes: Optional[str] = None


class VehicleInspectionRead(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    inspected_at: datetime
    odometer: Optional[int] = None
    driver: Optional[str] = None
    documents_ok: Optional[bool] = None
    tires_ok: Optional[bool] = None
    coolant_checked: Optional[bool] = None
    failing_items: Optional[str] = None
    other_problem: Optional[str] = None
    notes: Optional[str] = None
    has_issue: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Import -----------------------------------------------------------------


class VehicleImportSectionResult(BaseModel):
    created: int = 0
    skipped: int = 0  # already imported earlier (same external_id)


class VehicleImportResult(BaseModel):
    dry_run: bool
    vehicles_created: list[str] = []
    vehicles_matched: list[str] = []
    records: VehicleImportSectionResult = VehicleImportSectionResult()
    trips: VehicleImportSectionResult = VehicleImportSectionResult()
    inspections: VehicleImportSectionResult = VehicleImportSectionResult()
    warnings: list[str] = []
