"""Add integrity hashes to audit events.

Revision ID: 0004_audit_integrity
Revises: 0003_node_capacity
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_audit_integrity"
down_revision = "0003_node_capacity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns("audit_events")
    }
    if "integrity_hash" not in columns:
        op.add_column(
            "audit_events",
            sa.Column(
                "integrity_hash",
                sa.String(length=64),
                nullable=False,
                server_default="",
            ),
        )


def downgrade() -> None:
    columns = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns("audit_events")
    }
    if "integrity_hash" in columns:
        op.drop_column("audit_events", "integrity_hash")
