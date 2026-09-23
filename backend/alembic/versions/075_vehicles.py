"""add vehicles, vehicle_records and vehicle_reminders tables

Revision ID: 075
Revises: 074
Create Date: 2026-09-23

Vehicle control: register vehicles, log fill-ups / services / other
expenses against them, and track reminders due by date or odometer
(IPVA, licensing, insurance, oil change). Workspace-scoped.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "075"
down_revision: Union[str, None] = "074"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vehicles",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("plate", sa.String(length=20), nullable=True),
        sa.Column("brand", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=80), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("color", sa.String(length=30), nullable=True),
        sa.Column("fuel_type", sa.String(length=20), nullable=False, server_default="flex"),
        sa.Column("initial_odometer", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicles_workspace_id", "vehicles", ["workspace_id"])

    op.create_table(
        "vehicle_records",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="fuel"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("odometer", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0"),
        sa.Column("liters", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("full_tank", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicle_records_vehicle_id", "vehicle_records", ["vehicle_id"])
    op.create_index("ix_vehicle_records_workspace_id", "vehicle_records", ["workspace_id"])

    op.create_table(
        "vehicle_reminders",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("due_odometer", sa.Integer(), nullable=True),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicle_reminders_vehicle_id", "vehicle_reminders", ["vehicle_id"])
    op.create_index("ix_vehicle_reminders_workspace_id", "vehicle_reminders", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_vehicle_reminders_workspace_id", table_name="vehicle_reminders")
    op.drop_index("ix_vehicle_reminders_vehicle_id", table_name="vehicle_reminders")
    op.drop_table("vehicle_reminders")
    op.drop_index("ix_vehicle_records_workspace_id", table_name="vehicle_records")
    op.drop_index("ix_vehicle_records_vehicle_id", table_name="vehicle_records")
    op.drop_table("vehicle_records")
    op.drop_index("ix_vehicles_workspace_id", table_name="vehicles")
    op.drop_table("vehicles")
