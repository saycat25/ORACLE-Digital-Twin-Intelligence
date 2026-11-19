from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator  # noqa: I001


NodeKind = Literal["service", "database", "queue", "api", "worker", "cache", "gateway", "other"]


class NodeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    kind: NodeKind
    criticality: float = Field(default=0.5, ge=0.0, le=1.0)
    description: str = Field(default="", max_length=2000)


class NodeRead(NodeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class EdgeCreate(BaseModel):
    source_id: int = Field(gt=0)
    target_id: int = Field(gt=0)
    criticality: float = Field(default=0.5, ge=0.0, le=1.0)
    description: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def distinct_nodes(self):
        if self.source_id == self.target_id:
            raise ValueError("A dependency cannot reference the same node as source and target.")
        return self


class EdgeRead(EdgeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SimulationCreate(BaseModel):
    failed_node_id: int = Field(gt=0)
    failure_mode: Literal["unavailable", "degraded"] = "unavailable"


class ImpactedNode(BaseModel):
    node_id: int
    name: str
    hop_distance: int
    impact_score: float
    path_to_failure: list[int]


class SimulationResult(BaseModel):
    simulation_id: int | None = None
    failed_node_id: int
    failure_mode: str
    impacted_nodes: list[ImpactedNode]
    total_impacted: int
    methodology: str


class TelemetryCreate(BaseModel):
    node_id: int = Field(gt=0)
    metric: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]*$")
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(default="", max_length=30)
    observed_at: datetime | None = None


class TelemetryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: str
    node_id: int
    metric: str
    value: float
    unit: str
    observed_at: datetime


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    details_json: str
    created_at: datetime


class ScenarioSpec(BaseModel):
    failed_node_id: int = Field(gt=0)
    failure_mode: Literal["unavailable", "degraded"] = "unavailable"


class ScenarioCompareCreate(BaseModel):
    scenario_a: ScenarioSpec
    scenario_b: ScenarioSpec


class ImpactDelta(BaseModel):
    node_id: int
    name: str
    score_a: float
    score_b: float
    delta: float


class ScenarioCompareResult(BaseModel):
    scenario_a: SimulationResult
    scenario_b: SimulationResult
    newly_impacted_in_a: list[int]
    newly_impacted_in_b: list[int]
    shared_impacted: list[int]
    impact_score_deltas: list[ImpactDelta]
