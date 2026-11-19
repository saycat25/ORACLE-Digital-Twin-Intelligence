from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from oracle_api.config import settings


def test_legacy_single_tenant_database_is_migrated(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy-oracle.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    legacy_engine = create_engine(database_url)

    with legacy_engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE infrastructure_nodes (
                id INTEGER PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                kind VARCHAR(40) NOT NULL,
                criticality FLOAT NOT NULL,
                description TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
        """))
        connection.execute(text(
            "CREATE UNIQUE INDEX ix_infrastructure_nodes_name ON infrastructure_nodes (name)"
        ))
        connection.execute(text("""
            CREATE TABLE dependency_edges (
                id INTEGER PRIMARY KEY,
                source_id INTEGER NOT NULL REFERENCES infrastructure_nodes(id) ON DELETE CASCADE,
                target_id INTEGER NOT NULL REFERENCES infrastructure_nodes(id) ON DELETE CASCADE,
                criticality FLOAT NOT NULL,
                description TEXT NOT NULL,
                CONSTRAINT uq_dependency_pair UNIQUE (source_id, target_id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE simulation_records (
                id INTEGER PRIMARY KEY,
                failed_node_id INTEGER NOT NULL,
                failure_mode VARCHAR(40) NOT NULL,
                status VARCHAR(30) NOT NULL,
                result_json TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
        """))
        now = datetime.now(timezone.utc).isoformat()
        connection.execute(
            text("""
                INSERT INTO infrastructure_nodes
                (id, name, kind, criticality, description, created_at)
                VALUES (1, 'legacy-component', 'service', 0.8, '', :created_at)
            """),
            {"created_at": now},
        )
        connection.execute(
            text("""
                INSERT INTO dependency_edges
                (id, source_id, target_id, criticality, description)
                VALUES (1, 1, 1, 0.5, 'legacy edge')
            """)
            .execution_options(no_parameters=True)
        )
        connection.execute(
            text("""
                INSERT INTO simulation_records
                (id, failed_node_id, failure_mode, status, result_json, created_at)
                VALUES (1, 1, 'unavailable', 'completed', '{}', :created_at)
            """),
            {"created_at": now},
        )

    monkeypatch.setattr(settings, "database_url", database_url)
    migration_config = Config("alembic.ini")
    command.upgrade(migration_config, "head")

    migrated_engine = create_engine(database_url)
    inspector = inspect(migrated_engine)
    for table in ("infrastructure_nodes", "dependency_edges", "simulation_records"):
        assert "tenant_id" in {column["name"] for column in inspector.get_columns(table)}

    with migrated_engine.begin() as connection:
        assert connection.scalar(
            text("SELECT tenant_id FROM infrastructure_nodes WHERE id = 1")
        ) == "default"
        assert connection.scalar(
            text("SELECT tenant_id FROM dependency_edges WHERE id = 1")
        ) == "default"
        assert connection.scalar(
            text("SELECT tenant_id FROM simulation_records WHERE id = 1")
        ) == "default"

        # Same component name is permitted in another tenant after migration.
        connection.execute(
            text("""
                INSERT INTO infrastructure_nodes
                (tenant_id, name, kind, criticality, description, created_at)
                VALUES ('tenant-b', 'legacy-component', 'database', 0.5, '', :created_at)
            """),
            {"created_at": datetime.now(timezone.utc).isoformat()},
        )

    migrated_engine.dispose()
    legacy_engine.dispose()
