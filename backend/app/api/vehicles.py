import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import (
    WorkspaceContext,
    current_workspace,
    current_writable_workspace,
)
from app.models.vehicle import VehicleInspection, VehicleTrip
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleImportResult,
    VehicleInspectionCreate,
    VehicleInspectionRead,
    VehicleInspectionUpdate,
    VehicleRead,
    VehicleRecordCreate,
    VehicleRecordRead,
    VehicleRecordUpdate,
    VehicleReminderCreate,
    VehicleReminderRead,
    VehicleReminderUpdate,
    VehicleTripCreate,
    VehicleTripRead,
    VehicleTripUpdate,
    VehicleUpdate,
)
from app.services import drivvo_import_service, vehicle_service

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])

_VEHICLE_NOT_FOUND = "Vehicle not found"
_MAX_IMPORT_BYTES = 10 * 1024 * 1024


async def _load_vehicle(session: AsyncSession, vehicle_id: uuid.UUID, workspace_id: uuid.UUID):
    vehicle = await vehicle_service.get_vehicle(session, vehicle_id, workspace_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_VEHICLE_NOT_FOUND)
    return vehicle


# --- Import -----------------------------------------------------------------


@router.post("/import/drivvo", response_model=VehicleImportResult)
async def import_drivvo(
    file: UploadFile = File(...),
    dry_run: bool = Query(False),
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Import a Drivvo "REPORTS_DRIVVO.csv" export. `dry_run` previews counts without saving."""
    raw = await file.read(_MAX_IMPORT_BYTES + 1)
    if len(raw) > _MAX_IMPORT_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
    try:
        return await drivvo_import_service.import_drivvo(
            session, ctx.workspace.id, ctx.user_id, raw, dry_run=dry_run
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --- Vehicles ---------------------------------------------------------------


@router.get("", response_model=list[VehicleRead])
async def list_vehicles(
    include_inactive: bool = Query(True),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    vehicles = await vehicle_service.get_vehicles(session, ctx.workspace.id, include_inactive=include_inactive)
    return [vehicle_service.to_read(v) for v in vehicles]


@router.get("/{vehicle_id}", response_model=VehicleRead)
async def get_vehicle(
    vehicle_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return vehicle_service.to_read(await _load_vehicle(session, vehicle_id, ctx.workspace.id))


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    data: VehicleCreate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    vehicle = await vehicle_service.create_vehicle(session, ctx.workspace.id, ctx.user_id, data)
    return vehicle_service.to_read(vehicle)


@router.patch("/{vehicle_id}", response_model=VehicleRead)
async def update_vehicle(
    vehicle_id: uuid.UUID,
    data: VehicleUpdate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    vehicle = await vehicle_service.update_vehicle(session, vehicle_id, ctx.workspace.id, data)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_VEHICLE_NOT_FOUND)
    return vehicle_service.to_read(vehicle)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    if not await vehicle_service.delete_vehicle(session, vehicle_id, ctx.workspace.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_VEHICLE_NOT_FOUND)


# --- Records ----------------------------------------------------------------


async def _record_read(session: AsyncSession, vehicle_id: uuid.UUID, workspace_id: uuid.UUID, record_id: uuid.UUID):
    # Consumption depends on the neighbouring fill-ups, so re-read the whole
    # vehicle and pick this record out of the computed list.
    vehicle = await _load_vehicle(session, vehicle_id, workspace_id)
    return next(r for r in vehicle_service.records_to_read(vehicle) if r.id == record_id)


@router.get("/{vehicle_id}/records", response_model=list[VehicleRecordRead])
async def list_records(
    vehicle_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return vehicle_service.records_to_read(await _load_vehicle(session, vehicle_id, ctx.workspace.id))


@router.post("/{vehicle_id}/records", response_model=VehicleRecordRead, status_code=status.HTTP_201_CREATED)
async def create_record(
    vehicle_id: uuid.UUID,
    data: VehicleRecordCreate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    record = await vehicle_service.create_record(session, vehicle_id, ctx.workspace.id, data)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_VEHICLE_NOT_FOUND)
    return await _record_read(session, vehicle_id, ctx.workspace.id, record.id)


@router.patch("/{vehicle_id}/records/{record_id}", response_model=VehicleRecordRead)
async def update_record(
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    data: VehicleRecordUpdate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    record = await vehicle_service.update_record(session, vehicle_id, record_id, ctx.workspace.id, data)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return await _record_read(session, vehicle_id, ctx.workspace.id, record.id)


@router.delete("/{vehicle_id}/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    if not await vehicle_service.delete_record(session, vehicle_id, record_id, ctx.workspace.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")


# --- Reminders --------------------------------------------------------------


async def _reminder_read(
    session: AsyncSession, vehicle_id: uuid.UUID, workspace_id: uuid.UUID, reminder_id: uuid.UUID
):
    vehicle = await _load_vehicle(session, vehicle_id, workspace_id)
    return next(r for r in vehicle_service.reminders_to_read(vehicle) if r.id == reminder_id)


@router.get("/{vehicle_id}/reminders", response_model=list[VehicleReminderRead])
async def list_reminders(
    vehicle_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return vehicle_service.reminders_to_read(await _load_vehicle(session, vehicle_id, ctx.workspace.id))


@router.post("/{vehicle_id}/reminders", response_model=VehicleReminderRead, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    vehicle_id: uuid.UUID,
    data: VehicleReminderCreate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    reminder = await vehicle_service.create_reminder(session, vehicle_id, ctx.workspace.id, data)
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_VEHICLE_NOT_FOUND)
    return await _reminder_read(session, vehicle_id, ctx.workspace.id, reminder.id)


@router.patch("/{vehicle_id}/reminders/{reminder_id}", response_model=VehicleReminderRead)
async def update_reminder(
    vehicle_id: uuid.UUID,
    reminder_id: uuid.UUID,
    data: VehicleReminderUpdate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    reminder = await vehicle_service.update_reminder(session, vehicle_id, reminder_id, ctx.workspace.id, data)
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return await _reminder_read(session, vehicle_id, ctx.workspace.id, reminder.id)


@router.delete("/{vehicle_id}/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    vehicle_id: uuid.UUID,
    reminder_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    if not await vehicle_service.delete_reminder(session, vehicle_id, reminder_id, ctx.workspace.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")


# --- Trips ------------------------------------------------------------------


@router.get("/{vehicle_id}/trips", response_model=list[VehicleTripRead])
async def list_trips(
    vehicle_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return vehicle_service.trips_sorted(await _load_vehicle(session, vehicle_id, ctx.workspace.id))


@router.post("/{vehicle_id}/trips", response_model=VehicleTripRead, status_code=status.HTTP_201_CREATED)
async def create_trip(
    vehicle_id: uuid.UUID,
    data: VehicleTripCreate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    trip = await vehicle_service.create_trip(session, vehicle_id, ctx.workspace.id, data)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_VEHICLE_NOT_FOUND)
    return trip


@router.patch("/{vehicle_id}/trips/{trip_id}", response_model=VehicleTripRead)
async def update_trip(
    vehicle_id: uuid.UUID,
    trip_id: uuid.UUID,
    data: VehicleTripUpdate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        trip = await vehicle_service.update_trip(session, vehicle_id, trip_id, ctx.workspace.id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


@router.delete("/{vehicle_id}/trips/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    vehicle_id: uuid.UUID,
    trip_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    if not await vehicle_service.delete_child(session, VehicleTrip, vehicle_id, trip_id, ctx.workspace.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")


# --- Inspections ------------------------------------------------------------


@router.get("/{vehicle_id}/inspections", response_model=list[VehicleInspectionRead])
async def list_inspections(
    vehicle_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return vehicle_service.inspections_sorted(await _load_vehicle(session, vehicle_id, ctx.workspace.id))


@router.post(
    "/{vehicle_id}/inspections", response_model=VehicleInspectionRead, status_code=status.HTTP_201_CREATED
)
async def create_inspection(
    vehicle_id: uuid.UUID,
    data: VehicleInspectionCreate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    inspection = await vehicle_service.create_inspection(session, vehicle_id, ctx.workspace.id, data)
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_VEHICLE_NOT_FOUND)
    return inspection


@router.patch("/{vehicle_id}/inspections/{inspection_id}", response_model=VehicleInspectionRead)
async def update_inspection(
    vehicle_id: uuid.UUID,
    inspection_id: uuid.UUID,
    data: VehicleInspectionUpdate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    inspection = await vehicle_service.update_inspection(session, vehicle_id, inspection_id, ctx.workspace.id, data)
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    return inspection


@router.delete("/{vehicle_id}/inspections/{inspection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inspection(
    vehicle_id: uuid.UUID,
    inspection_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    if not await vehicle_service.delete_child(
        session, VehicleInspection, vehicle_id, inspection_id, ctx.workspace.id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
