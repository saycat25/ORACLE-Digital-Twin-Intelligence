"""Introduce tenant ownership on infrastructure resources.

The migration is compatible with the previous single-tenant schema. Existing records
are assigned to the reserved tenant "default".
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_tenant_scoping"
down_revision = None
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_column(table: str, column: str) -> bool:
    return any(item["name"] == column for item in _inspector().get_columns(table))


def _has_index(table: str, name: str) -> bool:
    return any(item["name"] == name for item in _inspector().get_indexes(table))


def _has_unique(table: str, name: str) -> bool:
    return any(item.get("name") == name for item in _inspector().get_unique_constraints(table))


def upgrade() -> None:
    # Create any newer auxiliary tables on fresh installs without changing legacy tables.
    from oracle_api.db import Base
    import oracle_api.models  # noqa: F401

    Base.metadata.create_all(bind=op.get_bind())

    for table in ("infrastructure_nodes", "dependency_edges", "simulation_records"):
        if not _has_column(table, "tenant_id"):
            op.add_column(
                table,
                sa.Column(
                    "tenant_id",
                    sa.String(length=120),
                    nullable=False,
                    server_default=sa.text("'default'"),
                ),
            )

    # Older releases used a globally unique node name. Replace that rule with
    # tenant-local uniqueness while retaining a non-unique lookup index.
    node_unique_indexes = [
        item for item in _inspector().get_indexes("infrastructure_nodes")
        if item.get("unique") and item.get("column_names") == ["name"]
    ]
    node_has_new_unique = _has_unique("infrastructure_nodes", "uq_tenant_node_name")
    if node_unique_indexes or not node_has_new_unique:
        with op.batch_alter_table("infrastructure_nodes") as batch:
            for item in node_unique_indexes:
                batch.drop_index(item["name"])
            if not node_has_new_unique:
                batch.create_unique_constraint("uq_tenant_node_name", ["tenant_id", "name"])

    if not _has_index("infrastructure_nodes", "ix_infrastructure_nodes_name"):
        op.create_index("ix_infrastructure_nodes_name", "infrastructure_nodes", ["name"], unique=False)
    if not _has_index("infrastructure_nodes", "ix_infrastructure_nodes_tenant_id"):
        op.create_index(
            "ix_infrastructure_nodes_tenant_id", "infrastructure_nodes", ["tenant_id"], unique=False
        )

    edge_old_unique = _has_unique("dependency_edges", "uq_dependency_pair")
    edge_new_unique = _has_unique("dependency_edges", "uq_tenant_dependency_pair")
    if edge_old_unique or not edge_new_unique:
        with op.batch_alter_table("dependency_edges") as batch:
            if edge_old_unique:
                batch.drop_constraint("uq_dependency_pair", type_="unique")
            if not edge_new_unique:
                batch.create_unique_constraint(
                    "uq_tenant_dependency_pair", ["tenant_id", "source_id", "target_id"]
                )
    if not _has_index("dependency_edges", "ix_dependency_edges_tenant_id"):
        op.create_index(
            "ix_dependency_edges_tenant_id", "dependency_edges", ["tenant_id"], unique=False
        )
    if not _has_index("simulation_records", "ix_simulation_records_tenant_id"):
        op.create_index(
            "ix_simulation_records_tenant_id", "simulation_records", ["tenant_id"], unique=False
        )


def downgrade() -> None:
    # Tenant scoping is intentionally irreversible: a downgrade could merge records
    # from different tenants into the old globally shared namespace.
    raise RuntimeError("This tenant isolation migration is intentionally irreversible.")
