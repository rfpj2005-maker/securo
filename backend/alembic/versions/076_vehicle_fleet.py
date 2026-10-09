"""vehicle fleet: trips, daily inspections, record details, import keys

Revision ID: 076
Revises: 075
Create Date: 2026-10-09

Brings the vehicle module up to what a small fleet tracks in Drivvo:
who drove and where each record happened, trips (origin/destination,
odometer at both ends), daily pre-use inspections, and an
`external_id` on imported rows so re-importing an export is idempotent.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "076"
down_revision: Union[str, None] = "075"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RECORD_COLUMNS = (
    ("driver", sa.String(length=100)),
    ("place", sa.String(length=150)),
    ("payment_method", sa.String(length=80)),
    ("purpose", sa.String(length=50)),
    ("notes", sa.Text()),
    ("external_id", sa.String(length=64)),
)


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("tank_capacity", sa.Numeric(precision=8, scale=2), nullable=True))
    op.add_column("vehicles", sa.Column("chassis", sa.String(length=30), nullable=True))
    op.add_column("vehicles", sa.Column("renavam", sa.String(length=20), nullable=True))

    for name, type_ in _RECORD_COLUMNS:
        op.add_column("vehicle_records", sa.Column(name, type_, nullable=True))
    op.create_index("ix_vehicle_records_external_id", "vehicle_records", ["external_id"])

    op.create_table(
        "vehicle_trips",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("start_odometer", sa.Integer(), nullable=False),
        sa.Column("end_odometer", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=150), nullable=True),
        sa.Column("destination", sa.String(length=150), nullable=True),
        sa.Column("driver", sa.String(length=100), nullable=True),
        sa.Column("purpose", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicle_trips_vehicle_id", "vehicle_trips", ["vehicle_id"])
    op.create_index("ix_vehicle_trips_workspace_id", "vehicle_trips", ["workspace_id"])
    op.create_index("ix_vehicle_trips_external_id", "vehicle_trips", ["external_id"])

    op.create_table(
        "vehicle_inspections",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("inspected_at", sa.DateTime(), nullable=False),
        sa.Column("odometer", sa.Integer(), nullable=True),
        sa.Column("driver", sa.String(length=100), nullable=True),
        sa.Column("documents_ok", sa.Boolean(), nullable=True),
        sa.Column("tires_ok", sa.Boolean(), nullable=True),
        sa.Column("coolant_checked", sa.Boolean(), nullable=True),
        sa.Column("failing_items", sa.String(length=255), nullable=True),
        sa.Column("other_problem", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicle_inspections_vehicle_id", "vehicle_inspections", ["vehicle_id"])
    op.create_index("ix_vehicle_inspections_workspace_id", "vehicle_inspections", ["workspace_id"])
    op.create_index("ix_vehicle_inspections_external_id", "vehicle_inspections", ["external_id"])


def downgrade() -> None:
    for table in ("vehicle_inspections", "vehicle_trips"):
        for col in ("external_id", "workspace_id", "vehicle_id"):
            op.drop_index(f"ix_{table}_{col}", table_name=table)
        op.drop_table(table)
    op.drop_index("ix_vehicle_records_external_id", table_name="vehicle_records")
    for name, _ in reversed(_RECORD_COLUMNS):
        op.drop_column("vehicle_records", name)
    op.drop_column("vehicles", "renavam")
    op.drop_column("vehicles", "chassis")
    op.drop_column("vehicles", "tank_capacity")
