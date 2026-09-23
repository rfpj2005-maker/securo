import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.vehicle import Vehicle, VehicleRecord, VehicleReminder
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleRead,
    VehicleRecordCreate,
    VehicleRecordRead,
    VehicleRecordUpdate,
    VehicleReminderCreate,
    VehicleReminderRead,
    VehicleReminderUpdate,
    VehicleStats,
    VehicleUpdate,
)

_ZERO = Decimal("0")


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Derived numbers
# ---------------------------------------------------------------------------


def current_odometer(vehicle: Vehicle) -> int:
    readings = [r.odometer for r in vehicle.records if r.odometer is not None]
    return max([vehicle.initial_odometer, *readings])


def compute_consumption(records: list[VehicleRecord]) -> tuple[dict[uuid.UUID, Decimal], Optional[Decimal]]:
    """Per-fill-up km/L and the overall average, using the full-tank method.

    Consumption is only measurable between two fill-ups that both topped
    the tank off: the distance between them divided by every liter put in
    after the first (partial fill-ups in between included). An interval
    with a fill-up missing its odometer or liters can't be measured, so it
    is skipped rather than guessed.
    """
    fuel = sorted(
        (r for r in records if r.kind == "fuel" and r.odometer is not None),
        key=lambda r: (r.odometer, r.date),
    )
    per_record: dict[uuid.UUID, Decimal] = {}
    total_km = 0
    total_liters = _ZERO
    anchor: Optional[int] = None
    liters_acc = _ZERO
    interval_ok = True

    for r in fuel:
        if anchor is None:
            if r.full_tank:
                anchor = r.odometer
            continue
        if r.liters is None:
            interval_ok = False
        else:
            liters_acc += Decimal(r.liters)
        if not r.full_tank:
            continue
        distance = r.odometer - anchor
        if interval_ok and distance > 0 and liters_acc > 0:
            per_record[r.id] = _q2(Decimal(distance) / liters_acc)
            total_km += distance
            total_liters += liters_acc
        anchor = r.odometer
        liters_acc = _ZERO
        interval_ok = True

    average = _q2(Decimal(total_km) / total_liters) if total_liters > 0 else None
    return per_record, average


def reminder_is_overdue(reminder: VehicleReminder, odometer: int, today: Optional[date] = None) -> bool:
    if reminder.is_done:
        return False
    today = today or date.today()
    if reminder.due_date is not None and reminder.due_date < today:
        return True
    return reminder.due_odometer is not None and odometer >= reminder.due_odometer


def compute_stats(vehicle: Vehicle) -> VehicleStats:
    odometer = current_odometer(vehicle)
    distance = odometer - vehicle.initial_odometer
    costs = {"fuel": _ZERO, "maintenance": _ZERO, "expense": _ZERO}
    total_liters = _ZERO
    for r in vehicle.records:
        costs[r.kind] = costs.get(r.kind, _ZERO) + Decimal(r.amount or 0)
        if r.kind == "fuel" and r.liters is not None:
            total_liters += Decimal(r.liters)
    total_cost = sum(costs.values(), _ZERO)
    _, average = compute_consumption(vehicle.records)
    pending = [rem for rem in vehicle.reminders if not rem.is_done]
    return VehicleStats(
        current_odometer=odometer,
        distance=distance,
        total_cost=_q2(total_cost),
        fuel_cost=_q2(costs["fuel"]),
        maintenance_cost=_q2(costs["maintenance"]),
        other_cost=_q2(costs["expense"]),
        total_liters=total_liters,
        avg_consumption=average,
        cost_per_km=_q2(total_cost / distance) if distance > 0 else None,
        pending_reminders=len(pending),
        overdue_reminders=sum(1 for rem in pending if reminder_is_overdue(rem, odometer)),
    )


def to_read(vehicle: Vehicle) -> VehicleRead:
    columns = {c.key: getattr(vehicle, c.key) for c in Vehicle.__table__.columns}
    return VehicleRead.model_validate({**columns, "stats": compute_stats(vehicle)})


def records_to_read(vehicle: Vehicle) -> list[VehicleRecordRead]:
    per_record, _ = compute_consumption(vehicle.records)
    ordered = sorted(
        vehicle.records,
        key=lambda r: (r.date, r.odometer or 0, r.created_at),
        reverse=True,
    )
    return [
        VehicleRecordRead.model_validate(r).model_copy(update={"consumption": per_record.get(r.id)})
        for r in ordered
    ]


def reminders_to_read(vehicle: Vehicle) -> list[VehicleReminderRead]:
    odometer = current_odometer(vehicle)
    ordered = sorted(
        vehicle.reminders,
        key=lambda r: (r.is_done, r.due_date is None, r.due_date or date.max, r.due_odometer or 0),
    )
    return [
        VehicleReminderRead.model_validate(r).model_copy(
            update={"is_overdue": reminder_is_overdue(r, odometer)}
        )
        for r in ordered
    ]


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------


def _with_children(stmt):
    # populate_existing: a vehicle already in the identity map (e.g. loaded
    # before a record was added) must get fresh collections, not stale ones.
    return stmt.options(selectinload(Vehicle.records), selectinload(Vehicle.reminders)).execution_options(
        populate_existing=True
    )


async def get_vehicles(
    session: AsyncSession, workspace_id: uuid.UUID, include_inactive: bool = True
) -> list[Vehicle]:
    stmt = _with_children(select(Vehicle).where(Vehicle.workspace_id == workspace_id))
    if not include_inactive:
        stmt = stmt.where(Vehicle.is_active.is_(True))
    stmt = stmt.order_by(Vehicle.is_active.desc(), Vehicle.name)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_vehicle(session: AsyncSession, vehicle_id: uuid.UUID, workspace_id: uuid.UUID) -> Optional[Vehicle]:
    result = await session.execute(
        _with_children(select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.workspace_id == workspace_id))
    )
    return result.scalar_one_or_none()


async def _reload(session: AsyncSession, vehicle: Vehicle) -> Vehicle:
    await session.refresh(vehicle)
    await session.refresh(vehicle, attribute_names=["records", "reminders"])
    return vehicle


async def create_vehicle(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID, data: VehicleCreate
) -> Vehicle:
    vehicle = Vehicle(user_id=user_id, workspace_id=workspace_id, **data.model_dump())
    session.add(vehicle)
    await session.commit()
    return await _reload(session, vehicle)


async def update_vehicle(
    session: AsyncSession, vehicle_id: uuid.UUID, workspace_id: uuid.UUID, data: VehicleUpdate
) -> Optional[Vehicle]:
    vehicle = await get_vehicle(session, vehicle_id, workspace_id)
    if not vehicle:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(vehicle, key, value)
    await session.commit()
    return await _reload(session, vehicle)


async def delete_vehicle(session: AsyncSession, vehicle_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
    vehicle = await get_vehicle(session, vehicle_id, workspace_id)
    if not vehicle:
        return False
    await session.delete(vehicle)
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


def _check_fuel_fields(record: VehicleRecord) -> None:
    # Liters and full-tank only mean something on a fill-up; clear them on
    # other kinds so they can't skew the consumption numbers.
    if record.kind != "fuel":
        record.liters = None
        record.full_tank = False


async def create_record(
    session: AsyncSession, vehicle_id: uuid.UUID, workspace_id: uuid.UUID, data: VehicleRecordCreate
) -> Optional[VehicleRecord]:
    vehicle = await get_vehicle(session, vehicle_id, workspace_id)
    if not vehicle:
        return None
    record = VehicleRecord(vehicle_id=vehicle.id, workspace_id=workspace_id, **data.model_dump())
    _check_fuel_fields(record)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def _get_record(
    session: AsyncSession, vehicle_id: uuid.UUID, record_id: uuid.UUID, workspace_id: uuid.UUID
) -> Optional[VehicleRecord]:
    result = await session.execute(
        select(VehicleRecord).where(
            VehicleRecord.id == record_id,
            VehicleRecord.vehicle_id == vehicle_id,
            VehicleRecord.workspace_id == workspace_id,
        )
    )
    return result.scalar_one_or_none()


async def update_record(
    session: AsyncSession,
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    workspace_id: uuid.UUID,
    data: VehicleRecordUpdate,
) -> Optional[VehicleRecord]:
    record = await _get_record(session, vehicle_id, record_id, workspace_id)
    if not record:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    _check_fuel_fields(record)
    await session.commit()
    await session.refresh(record)
    return record


async def delete_record(
    session: AsyncSession, vehicle_id: uuid.UUID, record_id: uuid.UUID, workspace_id: uuid.UUID
) -> bool:
    record = await _get_record(session, vehicle_id, record_id, workspace_id)
    if not record:
        return False
    await session.delete(record)
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------


async def create_reminder(
    session: AsyncSession, vehicle_id: uuid.UUID, workspace_id: uuid.UUID, data: VehicleReminderCreate
) -> Optional[VehicleReminder]:
    vehicle = await get_vehicle(session, vehicle_id, workspace_id)
    if not vehicle:
        return None
    reminder = VehicleReminder(vehicle_id=vehicle.id, workspace_id=workspace_id, **data.model_dump())
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder


async def _get_reminder(
    session: AsyncSession, vehicle_id: uuid.UUID, reminder_id: uuid.UUID, workspace_id: uuid.UUID
) -> Optional[VehicleReminder]:
    result = await session.execute(
        select(VehicleReminder).where(
            VehicleReminder.id == reminder_id,
            VehicleReminder.vehicle_id == vehicle_id,
            VehicleReminder.workspace_id == workspace_id,
        )
    )
    return result.scalar_one_or_none()


async def update_reminder(
    session: AsyncSession,
    vehicle_id: uuid.UUID,
    reminder_id: uuid.UUID,
    workspace_id: uuid.UUID,
    data: VehicleReminderUpdate,
) -> Optional[VehicleReminder]:
    reminder = await _get_reminder(session, vehicle_id, reminder_id, workspace_id)
    if not reminder:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(reminder, key, value)
    await session.commit()
    await session.refresh(reminder)
    return reminder


async def delete_reminder(
    session: AsyncSession, vehicle_id: uuid.UUID, reminder_id: uuid.UUID, workspace_id: uuid.UUID
) -> bool:
    reminder = await _get_reminder(session, vehicle_id, reminder_id, workspace_id)
    if not reminder:
        return False
    await session.delete(reminder)
    await session.commit()
    return True
