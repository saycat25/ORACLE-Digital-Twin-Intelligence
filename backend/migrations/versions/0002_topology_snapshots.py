"""Add versioned topology history.

Revision ID: 0002_topology_snapshots
Revises: 0001_tenant_scoping
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_topology_snapshots"
down_revision = "0001_tenant_scoping"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "topology_snapshots" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "topology_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(length=120), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("node_count", sa.Integer(), nullable=False),
            sa.Column("edge_count", sa.Integer(), nullable=False),
            sa.Column("snapshot_json", sa.Text(), nullable=False),
            sa.Column("created_by", sa.String(length=120), nullable=False, server_default="api"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "tenant_id",
                "version",
                name="uq_topology_snapshot_tenant_version",
            ),
        )

    inspector = sa.inspect(op.get_bind())
    indexes = {item["name"] for item in inspector.get_indexes("topology_snapshots")}
    if "ix_topology_snapshots_tenant_id" not in indexes:
        op.create_index(
            "ix_topology_snapshots_tenant_id",
            "topology_snapshots",
            ["tenant_id"],
            unique=False,
        )
    if "ix_topology_snapshots_created_at" not in indexes:
        op.create_index(
            "ix_topology_snapshots_created_at",
            "topology_snapshots",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_topology_snapshots_created_at", table_name="topology_snapshots")
    op.drop_index("ix_topology_snapshots_tenant_id", table_name="topology_snapshots")
    op.drop_table("topology_snapshots")
