"""Import a Drivvo export ("REPORTS_DRIVVO.csv") into the vehicle module.

The export is one CSV file holding several tables, each introduced by a
`#Section` line followed by its own header row:

    #Veículo / #Abastecimento / #Serviço / #Despesa / #Percurso /
    #Inspeção Diária do veículo

It comes in Latin-1 from the Drivvo web app, uses `.` as the decimal
separator and `dd/mm/yyyy HH:MM` dates, and the inspection table is not
quoted, so a comma in free text spills into extra columns.

Columns are looked up by (accent-insensitive) header name, never by
position, so reordered or extra columns in a future export don't shift
the mapping. Every imported row gets an `external_id` derived from its
identifying fields; re-importing the same export (or a newer one that
overlaps) skips rows that are already here.
"""
from __future__ import annotations

import csv
import hashlib
import io
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle import Vehicle, VehicleInspection, VehicleRecord, VehicleTrip
from app.schemas.vehicle import VehicleImportResult

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _norm(text: str) -> str:
    """Lower-case, accent-free, whitespace-collapsed — for matching headers."""
    stripped = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(stripped.lower().split())


def decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unreadable file encoding")  # latin-1 never fails; kept for clarity


def parse_decimal(value: str) -> Optional[Decimal]:
    value = (value or "").strip()
    if not value:
        return None
    if "," in value and "." in value:
        # Whichever separator comes last is the decimal one.
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_int(value: str) -> Optional[int]:
    number = parse_decimal(value)
    return int(number) if number is not None else None


def parse_odometer(value: str) -> Optional[int]:
    """Drivvo stores a blank reading as 0; treat it as unknown, not as km 0."""
    reading = parse_int(value)
    return reading if reading and reading > 0 else None


def parse_datetime(value: str) -> Optional[datetime]:
    value = (value or "").strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_bool(value: str) -> Optional[bool]:
    v = _norm(value or "")
    if v in ("sim", "yes", "s", "true", "1"):
        return True
    if v in ("nao", "no", "n", "false", "0"):
        return False
    return None


def _text(value: Optional[str], limit: Optional[int] = None) -> Optional[str]:
    value = (value or "").strip()
    if not value:
        return None
    return value[:limit] if limit else value


def _plate_key(plate: Optional[str]) -> Optional[str]:
    if not plate:
        return None
    key = "".join(ch for ch in plate.upper() if ch.isalnum())
    return key or None


def _external_id(*parts: object) -> str:
    raw = "|".join("" if p is None else str(p) for p in ("drivvo", *parts))
    return hashlib.sha1(raw.encode()).hexdigest()


@dataclass
class Table:
    name: str
    header: list[str]
    rows: list[list[str]]
    _index: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # First occurrence wins: the fuel table repeats "Valor total"/"Volume"
        # for a second and third fuel, and the first one is the main fill-up.
        for i, name in enumerate(self.header):
            self._index.setdefault(_norm(name), i)

    def col(self, *names: str) -> Optional[int]:
        """Index of the first header that equals — or starts with — one of `names`."""
        for name in names:
            key = _norm(name)
            if key in self._index:
                return self._index[key]
        for name in names:
            key = _norm(name)
            for header, i in self._index.items():
                if header.startswith(key):
                    return i
        return None

    def get(self, row: list[str], *names: str) -> str:
        i = self.col(*names)
        return row[i].strip() if i is not None and i < len(row) else ""


def split_tables(content: str) -> dict[str, Table]:
    """Split the export into its `#Section` tables, keyed by normalized name."""
    tables: dict[str, Table] = {}
    current: Optional[str] = None
    # skipinitialspace: the fuel header has `,  "Valor total"`, which would
    # otherwise keep its quotes as part of the name.
    for row in csv.reader(io.StringIO(content), skipinitialspace=True):
        if not row or all(not cell.strip() for cell in row):
            continue
        first = row[0].strip()
        if first.startswith("#"):
            current = first[1:].strip()
            continue
        if current is None:
            continue
        key = _norm(current)
        if key not in tables:
            tables[key] = Table(current, [c.strip() for c in row], [])
        else:
            tables[key].rows.append(row)
    return tables


def _find_table(tables: dict[str, Table], prefix: str) -> Optional[Table]:
    for key, table in tables.items():
        if key.startswith(prefix):
            return table
    return None


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


class _VehicleResolver:
    """Maps Drivvo vehicle names to Securo vehicles, creating missing ones."""

    def __init__(self, existing: list[Vehicle], workspace_id: uuid.UUID, user_id: uuid.UUID):
        self.by_plate = {k: v for v in existing if (k := _plate_key(v.plate))}
        self.by_name = {_norm(v.name): v for v in existing}
        self.by_drivvo_name: dict[str, Vehicle] = {}
        self.created: list[Vehicle] = []
        self.matched: list[Vehicle] = []
        self.workspace_id = workspace_id
        self.user_id = user_id

    def register(self, drivvo_name: str, plate: Optional[str], **fields) -> Vehicle:
        vehicle = self.by_plate.get(_plate_key(plate) or "") or self.by_name.get(_norm(drivvo_name))
        if vehicle is not None:
            if vehicle not in self.matched and vehicle not in self.created:
                self.matched.append(vehicle)
        else:
            vehicle = Vehicle(
                id=uuid.uuid4(),
                workspace_id=self.workspace_id,
                user_id=self.user_id,
                name=drivvo_name[:100],
                plate=(plate or "").strip().upper()[:20] or None,
                **{"fuel_type": "flex", "initial_odometer": 0, "is_active": True, **fields},
            )
            self.created.append(vehicle)
            if key := _plate_key(vehicle.plate):
                self.by_plate[key] = vehicle
            self.by_name[_norm(drivvo_name)] = vehicle
        self.by_drivvo_name[_norm(drivvo_name)] = vehicle
        return vehicle

    def lookup(self, drivvo_name: str) -> Vehicle:
        vehicle = self.by_drivvo_name.get(_norm(drivvo_name))
        return vehicle or self.register(drivvo_name, None)


async def import_drivvo(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    raw: bytes,
    dry_run: bool = False,
) -> VehicleImportResult:
    tables = split_tables(decode(raw))
    result = VehicleImportResult(dry_run=dry_run)
    if not tables:
        raise ValueError("No Drivvo sections (#Veículo, #Abastecimento, …) found in the file")

    existing = list(
        (await session.execute(select(Vehicle).where(Vehicle.workspace_id == workspace_id))).scalars().all()
    )
    vehicles = _VehicleResolver(existing, workspace_id, user_id)

    # --- Vehicles ---------------------------------------------------------
    if table := _find_table(tables, "veiculo"):
        for row in table.rows:
            name = table.get(row, "Nome do veículo")
            if not name:
                continue
            vehicles.register(
                name,
                table.get(row, "Placa"),
                brand=_text(table.get(row, "Marca"), 50),
                model=_text(table.get(row, "Modelo"), 80),
                year=parse_int(table.get(row, "Ano")),
                tank_capacity=parse_decimal(table.get(row, "Vol. do tanque")),
                chassis=_text(table.get(row, "Chassi"), 30),
                renavam=_text(table.get(row, "Renavam"), 20),
                notes=_text(table.get(row, "Observação")),
                is_active=parse_bool(table.get(row, "Ativo")) is not False,
            )

    # Owner of each new row, kept outside the ORM relationship so building a
    # row never cascades it into the session (a dry run must write nothing).
    owners: dict[int, Vehicle] = {}

    def own(vehicle: Vehicle, item):
        owners[id(item)] = vehicle
        return item

    new_records: list[VehicleRecord] = []
    new_trips: list[VehicleTrip] = []
    new_inspections: list[VehicleInspection] = []

    # --- Fill-ups -----------------------------------------------------------
    if table := _find_table(tables, "abastecimento"):
        amount_cols = [i for i, h in enumerate(table.header) if _norm(h) == "valor total"]
        volume_cols = [i for i, h in enumerate(table.header) if _norm(h) == "volume"]
        for n, row in enumerate(table.rows, start=1):
            name = table.get(row, "Nome do veículo")
            when = parse_datetime(table.get(row, "Data"))
            if not name or when is None:
                result.warnings.append(f"Abastecimento linha {n}: sem veículo ou data, ignorada")
                continue
            # Up to three fuels per fill-up; fold the extras into one record.
            amount = sum((parse_decimal(row[i]) or Decimal(0) for i in amount_cols if i < len(row)), Decimal(0))
            liters = sum((parse_decimal(row[i]) or Decimal(0) for i in volume_cols if i < len(row)), Decimal(0))
            odometer = parse_odometer(table.get(row, "Odômetro"))
            new_records.append(
                own(vehicles.lookup(name), VehicleRecord(
                    workspace_id=workspace_id,
                    kind="fuel",
                    date=when.date(),
                    odometer=odometer,
                    amount=amount,
                    liters=liters or None,
                    full_tank=parse_bool(table.get(row, "Completou o tanque")) is not False,
                    description=_text(table.get(row, "Combustível"), 255),
                    place=_text(table.get(row, "Posto de combustível"), 150),
                    driver=_text(table.get(row, "Motorista"), 100),
                    payment_method=_text(table.get(row, "Forma de pagamento"), 80),
                    purpose=_text(table.get(row, "Motivo"), 50),
                    notes=_text(table.get(row, "Observação")),
                    external_id=_external_id("fuel", _norm(name), when.isoformat(), odometer, amount),
                ))
            )

    # --- Services and expenses ---------------------------------------------
    for prefix, kind, type_col, place_col in (
        ("servico", "maintenance", "Tipo de serviço", "Local do serviço"),
        ("despesa", "expense", "Tipo de despesa", "Local da despesa"),
    ):
        table = _find_table(tables, prefix)
        if not table:
            continue
        for n, row in enumerate(table.rows, start=1):
            name = table.get(row, "Nome do veículo")
            when = parse_datetime(table.get(row, "Data"))
            if not name or when is None:
                result.warnings.append(f"{table.name} linha {n}: sem veículo ou data, ignorada")
                continue
            amount = parse_decimal(table.get(row, "Valor total", "Valor")) or Decimal(0)
            odometer = parse_odometer(table.get(row, "Odômetro"))
            description = _text(table.get(row, type_col, "Tipo"), 255)
            new_records.append(
                own(vehicles.lookup(name), VehicleRecord(
                    workspace_id=workspace_id,
                    kind=kind,
                    date=when.date(),
                    odometer=odometer,
                    amount=amount,
                    liters=None,
                    full_tank=False,
                    description=description,
                    place=_text(table.get(row, place_col, "Local"), 150),
                    driver=_text(table.get(row, "Motorista"), 100),
                    payment_method=_text(table.get(row, "Forma de pagamento"), 80),
                    purpose=_text(table.get(row, "Motivo"), 50),
                    notes=_text(table.get(row, "Observação")),
                    external_id=_external_id(kind, _norm(name), when.isoformat(), odometer, amount, description),
                ))
            )

    if _find_table(tables, "receita"):
        result.warnings.append("Receitas do Drivvo não são importadas (o módulo controla apenas custos)")

    # --- Trips --------------------------------------------------------------
    if table := _find_table(tables, "percurso"):
        for n, row in enumerate(table.rows, start=1):
            name = table.get(row, "Nome do veículo")
            started = parse_datetime(table.get(row, "Data inicial"))
            start_odo = parse_int(table.get(row, "Odômetro inicial"))
            end_odo = parse_int(table.get(row, "Odômetro final"))
            if not name or started is None or start_odo is None or end_odo is None:
                result.warnings.append(f"Percurso linha {n}: dados incompletos, ignorado")
                continue
            if end_odo < start_odo:
                result.warnings.append(f"Percurso linha {n}: odômetro final menor que o inicial, ignorado")
                continue
            new_trips.append(
                own(vehicles.lookup(name), VehicleTrip(
                    workspace_id=workspace_id,
                    started_at=started,
                    ended_at=parse_datetime(table.get(row, "Data final")),
                    start_odometer=start_odo,
                    end_odometer=end_odo,
                    origin=_text(table.get(row, "Origem"), 150),
                    destination=_text(table.get(row, "Destino"), 150),
                    driver=_text(table.get(row, "Motorista"), 100),
                    purpose=_text(table.get(row, "Motivo"), 50),
                    notes=_text(table.get(row, "Observação")),
                    external_id=_external_id("trip", _norm(name), started.isoformat(), start_odo, end_odo),
                ))
            )

    # --- Daily inspections ----------------------------------------------------
    if table := _find_table(tables, "inspecao"):
        free_text = table.col("Outro problema")
        for n, row in enumerate(table.rows, start=1):
            extra = len(row) - len(table.header)
            if extra > 0 and free_text is not None:
                # Unquoted export: a comma in "Outro problema" split it. Glue it back
                # (the reader drops the space that followed the comma).
                row = row[:free_text] + [", ".join(row[free_text : free_text + extra + 1])] + row[free_text + extra + 1 :]
            name = table.get(row, "Nome do veículo")
            when = parse_datetime(table.get(row, "Data"))
            if not name or when is None:
                result.warnings.append(f"Inspeção linha {n}: sem veículo ou data, ignorada")
                continue
            odometer = parse_odometer(table.get(row, "Odômetro"))
            new_inspections.append(
                own(vehicles.lookup(name), VehicleInspection(
                    workspace_id=workspace_id,
                    inspected_at=when,
                    odometer=odometer,
                    driver=_text(table.get(row, "Motorista"), 100),
                    documents_ok=parse_bool(table.get(row, "Documento do veículo")),
                    tires_ok=parse_bool(table.get(row, "Pneus")),
                    coolant_checked=parse_bool(table.get(row, "Foi verificado o nível")),
                    failing_items=_text(table.get(row, "Quais destes itens"), 255),
                    other_problem=_text(table.get(row, "Outro problema")),
                    notes=_text(table.get(row, "Observação")),
                    external_id=_external_id("inspection", _norm(name), when.isoformat(), odometer),
                ))
            )

    # --- New vehicles start at their lowest odometer reading -----------------
    for vehicle in vehicles.created:
        readings = [r.odometer for r in new_records if owners[id(r)] is vehicle and r.odometer is not None]
        readings += [t.start_odometer for t in new_trips if owners[id(t)] is vehicle]
        readings += [i.odometer for i in new_inspections if owners[id(i)] is vehicle and i.odometer is not None]
        vehicle.initial_odometer = min(readings, default=0)

    # --- Skip rows imported before -------------------------------------------
    matched_ids = [v.id for v in vehicles.matched]

    async def _known(model) -> set[str]:
        if not matched_ids:
            return set()
        rows = await session.execute(
            select(model.external_id).where(model.vehicle_id.in_(matched_ids), model.external_id.is_not(None))
        )
        return set(rows.scalars().all())

    def _keep(items: list, known: set[str], section) -> list:
        seen: set[str] = set()
        fresh = []
        for item in items:
            if item.external_id in known or item.external_id in seen:
                section.skipped += 1
                continue
            seen.add(item.external_id)
            fresh.append(item)
        section.created = len(fresh)
        return fresh

    records = _keep(new_records, await _known(VehicleRecord), result.records)
    trips = _keep(new_trips, await _known(VehicleTrip), result.trips)
    inspections = _keep(new_inspections, await _known(VehicleInspection), result.inspections)

    result.vehicles_created = [v.name for v in vehicles.created]
    result.vehicles_matched = [v.name for v in vehicles.matched]

    if dry_run:
        return result

    for vehicle in vehicles.created:
        session.add(vehicle)
    for item in (*records, *trips, *inspections):
        item.vehicle_id = owners[id(item)].id
        session.add(item)
    await session.commit()
    return result
