"""Add declared capacity and current load to infrastructure nodes.

Revision ID: 0003_node_capacity
Revises: 0002_topology_snapshots
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_node_capacity"
down_revision = "0002_topology_snapshots"
branch_labels = None
depends_on = None


def _columns():
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns("infrastructure_nodes")}


def upgrade() -> None:
    columns = _columns()
    if "capacity_units" not in columns:
        op.add_column(
            "infrastructure_nodes",
            sa.Column(
                "capacity_units",
                sa.Float(),
                nullable=False,
                server_default=sa.text("100.0"),
            ),
        )
    if "current_load_units" not in columns:
        op.add_column(
            "infrastructure_nodes",
            sa.Column(
                "current_load_units",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0.0"),
            ),
        )


def downgrade() -> None:
    columns = _columns()
    if "current_load_units" in columns:
        op.drop_column("infrastructure_nodes", "current_load_units")
    if "capacity_units" in columns:
        op.drop_column("infrastructure_nodes", "capacity_units")
