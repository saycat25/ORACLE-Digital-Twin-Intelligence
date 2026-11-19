from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from oracle_api.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class InfrastructureNode(Base):
    __tablename__ = "infrastructure_nodes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_node_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True, default="default")
    name: Mapped[str] = mapped_column(String(120), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    criticality: Mapped[float] = mapped_column(Float, default=0.5)
    capacity_units: Mapped[float] = mapped_column(Float, default=100.0)
    current_load_units: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DependencyEdge(Base):
    __tablename__ = "dependency_edges"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_id", "target_id", name="uq_tenant_dependency_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True, default="default")
    source_id: Mapped[int] = mapped_column(ForeignKey("infrastructure_nodes.id", ondelete="CASCADE"))
    target_id: Mapped[int] = mapped_column(ForeignKey("infrastructure_nodes.id", ondelete="CASCADE"))
    criticality: Mapped[float] = mapped_column(Float, default=0.5)
    description: Mapped[str] = mapped_column(Text, default="")


class SimulationRecord(Base):
    __tablename__ = "simulation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True, default="default")
    failed_node_id: Mapped[int] = mapped_column(Integer, index=True)
    failure_mode: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="completed")
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True, default="default")
    actor: Mapped[str] = mapped_column(String(120), default="system")
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_type: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(120), default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    integrity_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class TelemetrySample(Base):
    __tablename__ = "telemetry_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True, default="default")
    node_id: Mapped[int] = mapped_column(ForeignKey("infrastructure_nodes.id", ondelete="CASCADE"), index=True)
    metric: Mapped[str] = mapped_column(String(80), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30), default="")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class TopologySnapshot(Base):
    __tablename__ = "topology_snapshots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "version", name="uq_topology_snapshot_tenant_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[int] = mapped_column(Integer)
    node_count: Mapped[int] = mapped_column(Integer)
    edge_count: Mapped[int] = mapped_column(Integer)
    snapshot_json: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(120), default="api")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
