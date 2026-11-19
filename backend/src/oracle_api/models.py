from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from oracle_api.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InfrastructureNode(Base):
    __tablename__ = "infrastructure_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    criticality: Mapped[float] = mapped_column(Float, default=0.5)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DependencyEdge(Base):
    __tablename__ = "dependency_edges"
    __table_args__ = (UniqueConstraint("source_id", "target_id", name="uq_dependency_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("infrastructure_nodes.id", ondelete="CASCADE"))
    target_id: Mapped[int] = mapped_column(ForeignKey("infrastructure_nodes.id", ondelete="CASCADE"))
    criticality: Mapped[float] = mapped_column(Float, default=0.5)
    description: Mapped[str] = mapped_column(Text, default="")


class SimulationRecord(Base):
    __tablename__ = "simulation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    failed_node_id: Mapped[int] = mapped_column(Integer, index=True)
    failure_mode: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="completed")
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
