import json
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from oracle_api.config import settings
from oracle_api.db import Base, engine, get_session
from oracle_api.engine import analyze_impact
from oracle_api.models import (
    AuditEvent,
    DependencyEdge,
    InfrastructureNode,
    SimulationRecord,
    TelemetrySample,
    utc_now,
)
from oracle_api.schemas import (
    AIExplainRequest,
    AIExplainResponse,
    AuditEventRead,
    EdgeCreate,
    EdgeRead,
    NodeCreate,
    NodeRead,
    ScenarioCompareCreate,
    ScenarioCompareResult,
    SimulationCreate,
    SimulationResult,
    TelemetryCreate,
    TelemetryRead,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="ORACLE Digital Twin Intelligence API",
    version="0.2.0",
    description="Explainable infrastructure topology, telemetry and failure-impact simulation.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Tenant-ID"],
)


def resolve_tenant(x_tenant_id: str = Header(default="default", alias="X-Tenant-ID")) -> str:
    tenant = x_tenant_id.strip()
    if not tenant or len(tenant) > 120:
        raise HTTPException(status_code=400, detail="Invalid tenant identifier.")
    return tenant


DbSession = Annotated[Session, Depends(get_session)]
TenantId = Annotated[str, Depends(resolve_tenant)]


def require_ingestion_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = settings.ingestion_api_key
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing ingestion API key.")


def record_audit(
    session: Session,
    tenant_id: str,
    action: str,
    resource_type: str,
    resource_id: str = "",
    details: dict | None = None,
) -> None:
    session.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor="api",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            details_json=json.dumps(details or {}, sort_keys=True),
        )
    )


@app.get("/health", tags=["operations"])
def health():
    return {"status": "ok", "service": "oracle-api", "version": app.version}


@app.post(
    f"{settings.api_prefix}/nodes",
    response_model=NodeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_node(
    payload: NodeCreate,
    tenant_id: TenantId,
    session: DbSession,
):
    node = InfrastructureNode(**payload.model_dump())
    session.add(node)
    try:
        session.flush()
        record_audit(session, tenant_id, "node.created", "node", node.id, {"name": node.name})
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="A node with this name already exists.") from exc
    session.refresh(node)
    return node


@app.get(f"{settings.api_prefix}/nodes", response_model=list[NodeRead])
def list_nodes(session: DbSession):
    return list(session.scalars(select(InfrastructureNode).order_by(InfrastructureNode.id)))


@app.post(
    f"{settings.api_prefix}/edges",
    response_model=EdgeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_edge(
    payload: EdgeCreate,
    tenant_id: TenantId,
    session: DbSession,
):
    source = session.get(InfrastructureNode, payload.source_id)
    target = session.get(InfrastructureNode, payload.target_id)
    if source is None or target is None:
        raise HTTPException(status_code=404, detail="Both source and target nodes must exist.")
    edge = DependencyEdge(**payload.model_dump())
    session.add(edge)
    try:
        session.flush()
        record_audit(
            session, tenant_id, "dependency.created", "dependency", edge.id,
            {"source_id": edge.source_id, "target_id": edge.target_id},
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="This dependency already exists.") from exc
    session.refresh(edge)
    return edge


@app.get(f"{settings.api_prefix}/edges", response_model=list[EdgeRead])
def list_edges(session: DbSession):
    return list(session.scalars(select(DependencyEdge).order_by(DependencyEdge.id)))


@app.get(f"{settings.api_prefix}/topology", tags=["topology"])
def get_topology(session: DbSession):
    nodes = list(session.scalars(select(InfrastructureNode).order_by(InfrastructureNode.id)))
    edges = list(session.scalars(select(DependencyEdge).order_by(DependencyEdge.id)))
    return {
        "nodes": [NodeRead.model_validate(node).model_dump(mode="json") for node in nodes],
        "edges": [EdgeRead.model_validate(edge).model_dump(mode="json") for edge in edges],
    }


@app.post(
    f"{settings.api_prefix}/simulations",
    response_model=SimulationResult,
    status_code=status.HTTP_201_CREATED,
)
def run_simulation(
    payload: SimulationCreate,
    tenant_id: TenantId,
    session: DbSession,
):
    if session.get(InfrastructureNode, payload.failed_node_id) is None:
        raise HTTPException(status_code=404, detail="Failed node was not found.")

    nodes = [
        {"id": n.id, "name": n.name, "kind": n.kind, "criticality": n.criticality}
        for n in session.scalars(select(InfrastructureNode))
    ]
    edges = [
        {"source_id": e.source_id, "target_id": e.target_id, "criticality": e.criticality}
        for e in session.scalars(select(DependencyEdge))
    ]
    impacted = analyze_impact(nodes, edges, payload.failed_node_id, payload.failure_mode)
    result = SimulationResult(
        failed_node_id=payload.failed_node_id,
        failure_mode=payload.failure_mode,
        impacted_nodes=impacted,
        total_impacted=len(impacted),
        methodology="Reverse dependency traversal; criticality-weighted, hop-decayed deterministic score.",
    )
    record = SimulationRecord(
        failed_node_id=payload.failed_node_id,
        failure_mode=payload.failure_mode,
        result_json=result.model_dump_json(),
    )
    session.add(record)
    session.flush()
    record_audit(
        session, tenant_id, "simulation.completed", "simulation", record.id,
        {"failed_node_id": payload.failed_node_id, "failure_mode": payload.failure_mode,
         "total_impacted": len(impacted)},
    )
    session.commit()
    session.refresh(record)
    return result.model_copy(update={"simulation_id": record.id})


@app.get(f"{settings.api_prefix}/simulations/{{simulation_id}}", response_model=SimulationResult)
def get_simulation(simulation_id: int, session: DbSession):
    record = session.get(SimulationRecord, simulation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Simulation was not found.")
    data = json.loads(record.result_json)
    data["simulation_id"] = record.id
    return SimulationResult(**data)


@app.post(
    f"{settings.api_prefix}/telemetry",
    response_model=TelemetryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_ingestion_key)],
    tags=["observability"],
)
def ingest_telemetry(
    payload: TelemetryCreate,
    tenant_id: TenantId,
    session: DbSession,
):
    if session.get(InfrastructureNode, payload.node_id) is None:
        raise HTTPException(status_code=404, detail="Telemetry node was not found.")
    sample = TelemetrySample(
        tenant_id=tenant_id,
        node_id=payload.node_id,
        metric=payload.metric,
        value=payload.value,
        unit=payload.unit,
        observed_at=payload.observed_at or utc_now(),
    )
    session.add(sample)
    session.flush()
    record_audit(
        session, tenant_id, "telemetry.ingested", "telemetry", sample.id,
        {"node_id": sample.node_id, "metric": sample.metric},
    )
    session.commit()
    session.refresh(sample)
    return sample


@app.get(f"{settings.api_prefix}/telemetry", response_model=list[TelemetryRead], tags=["observability"])
def list_telemetry(
    node_id: int | None = Query(default=None, gt=0),
    metric: str | None = Query(default=None, min_length=1, max_length=80),
    limit: int = Query(default=100, ge=1, le=1000),
    tenant_id: TenantId,
    session: DbSession,
):
    query = select(TelemetrySample).where(TelemetrySample.tenant_id == tenant_id)
    if node_id is not None:
        query = query.where(TelemetrySample.node_id == node_id)
    if metric is not None:
        query = query.where(TelemetrySample.metric == metric)
    query = query.order_by(TelemetrySample.observed_at.desc()).limit(limit)
    return list(session.scalars(query))


@app.get(f"{settings.api_prefix}/audit", response_model=list[AuditEventRead], tags=["governance"])
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=1000),
    action: str | None = Query(default=None, min_length=1, max_length=80),
    tenant_id: TenantId,
    session: DbSession,
):
    query = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
    if action is not None:
        query = query.where(AuditEvent.action == action)
    query = query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit)
    return list(session.scalars(query))



@app.post(
    f"{settings.api_prefix}/scenarios/compare",
    response_model=ScenarioCompareResult,
    tags=["scenarios"],
)
def compare_scenarios(
    payload: ScenarioCompareCreate,
    tenant_id: TenantId,
    session: DbSession,
):
    nodes = [
        {"id": n.id, "name": n.name, "kind": n.kind, "criticality": n.criticality}
        for n in session.scalars(select(InfrastructureNode))
    ]
    node_ids = {node["id"] for node in nodes}
    for scenario in (payload.scenario_a, payload.scenario_b):
        if scenario.failed_node_id not in node_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Scenario node {scenario.failed_node_id} was not found.",
            )

    edges = [
        {"source_id": e.source_id, "target_id": e.target_id, "criticality": e.criticality}
        for e in session.scalars(select(DependencyEdge))
    ]

    def evaluate(spec):
        impacted = analyze_impact(nodes, edges, spec.failed_node_id, spec.failure_mode)
        return SimulationResult(
            failed_node_id=spec.failed_node_id,
            failure_mode=spec.failure_mode,
            impacted_nodes=impacted,
            total_impacted=len(impacted),
            methodology=(
                "Reverse dependency traversal; criticality-weighted, "
                "hop-decayed deterministic score."
            ),
        )

    result_a = evaluate(payload.scenario_a)
    result_b = evaluate(payload.scenario_b)
    scores_a = {item.node_id: item.impact_score for item in result_a.impacted_nodes}
    scores_b = {item.node_id: item.impact_score for item in result_b.impacted_nodes}
    ids_a = set(scores_a)
    ids_b = set(scores_b)
    names = {node["id"]: node["name"] for node in nodes}
    deltas = [
        {
            "node_id": node_id,
            "name": names[node_id],
            "score_a": scores_a.get(node_id, 0.0),
            "score_b": scores_b.get(node_id, 0.0),
            "delta": round(scores_b.get(node_id, 0.0) - scores_a.get(node_id, 0.0), 6),
        }
        for node_id in sorted(ids_a | ids_b)
    ]
    record_audit(
        session,
        tenant_id,
        "scenario.compared",
        "scenario",
        "",
        {
            "scenario_a_failed_node_id": payload.scenario_a.failed_node_id,
            "scenario_b_failed_node_id": payload.scenario_b.failed_node_id,
            "scenario_a_impacted": len(ids_a),
            "scenario_b_impacted": len(ids_b),
        },
    )
    session.commit()
    return ScenarioCompareResult(
        scenario_a=result_a,
        scenario_b=result_b,
        newly_impacted_in_a=sorted(ids_a - ids_b),
        newly_impacted_in_b=sorted(ids_b - ids_a),
        shared_impacted=sorted(ids_a & ids_b),
        impact_score_deltas=deltas,
    )



@app.post(
    f"{settings.api_prefix}/ai/explain",
    response_model=AIExplainResponse,
    tags=["ai-assistance"],
)
def explain_simulation_with_ai(
    payload: AIExplainRequest,
    tenant_id: TenantId,
    session: DbSession,
):
    if not settings.ai_data_sharing_enabled:
        raise HTTPException(
            status_code=403,
            detail="AI data sharing is disabled. Enable it explicitly in server configuration.",
        )
    if not settings.deepseek_api_key:
        raise HTTPException(
            status_code=503,
            detail="DeepSeek is not configured. Set DEEPSEEK_API_KEY on the API server.",
        )

    record = session.get(SimulationRecord, payload.simulation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Simulation was not found.")
    simulation_data = json.loads(record.result_json)
    failed_node = session.get(InfrastructureNode, record.failed_node_id)
    prompt_data = {
        "failed_node": {
            "id": record.failed_node_id,
            "name": failed_node.name if failed_node is not None else "unknown",
        },
        "failure_mode": record.failure_mode,
        "total_impacted": simulation_data.get("total_impacted", 0),
        "impacted_nodes": simulation_data.get("impacted_nodes", []),
        "methodology": simulation_data.get("methodology", ""),
    }
    request_body = {
        "model": settings.deepseek_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an infrastructure resilience analyst. Explain only what is "
                    "supported by the supplied deterministic simulation data. Separate "
                    "observed graph facts from hypotheses. Do not claim to predict outage "
                    "probability, root cause, real capacity, or real-world availability. "
                    "Provide concise prioritized validation and mitigation suggestions. "
                    "State that this is decision support and requires human review."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Explain this ORACLE simulation in Brazilian Portuguese. "
                    "Use the supplied component names, impact scores, paths and hop distances. "
                    "Do not invent topology or telemetry. Data: "
                    + json.dumps(prompt_data, ensure_ascii=False)
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 900,
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    endpoint = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    try:
        with httpx.Client(timeout=settings.deepseek_timeout_seconds) as client:
            upstream = client.post(
                endpoint,
                json=request_body,
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            )
            upstream.raise_for_status()
            response_data = upstream.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"DeepSeek returned HTTP {exc.response.status_code}.",
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="DeepSeek request failed.") from exc

    try:
        explanation = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="DeepSeek returned an unexpected response.") from exc
    if not isinstance(explanation, str) or not explanation.strip():
        raise HTTPException(status_code=502, detail="DeepSeek returned an empty explanation.")

    record_audit(
        session,
        tenant_id,
        "ai.explanation.generated",
        "simulation",
        record.id,
        {"provider": "deepseek", "model": settings.deepseek_model},
    )
    session.commit()
    return AIExplainResponse(
        simulation_id=record.id,
        provider="DeepSeek",
        model=settings.deepseek_model,
        explanation=explanation.strip(),
        disclaimer=(
            "Análise gerada por IA a partir do resultado da simulação; não é previsão, "
            "diagnóstico de causa raiz ou substituto de validação por um especialista."
        ),
    )
