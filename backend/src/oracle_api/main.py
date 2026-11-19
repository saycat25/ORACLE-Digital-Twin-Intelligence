import json
import time
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from oracle_api.config import settings
from oracle_api.db import Base, engine, get_session
from oracle_api.engine import analyze_impact
from oracle_api.observability import record_http_request, render_prometheus_metrics
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
from oracle_api.security import Principal, get_principal, require_roles


DbSession = Annotated[Session, Depends(get_session)]
CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


def resolve_tenant(principal: CurrentPrincipal) -> str:
    return principal.tenant_id


TenantId = Annotated[str, Depends(resolve_tenant)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.oracle_env.lower() in {"production", "prod"} and not settings.api_keys.strip():
        raise RuntimeError("ORACLE_API_KEYS must be configured in production.")
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="ORACLE Digital Twin Intelligence API",
    version="0.3.0",
    description=(
        "Tenant-scoped infrastructure topology, deterministic impact simulation, "
        "telemetry, audit events and optional AI assistance."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Tenant-ID"],
)



@app.middleware("http")
async def collect_http_metrics(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        route = getattr(request.scope.get("route"), "path", "unmatched")
        record_http_request(request.method, route, 500, time.perf_counter() - started)
        raise
    route = getattr(request.scope.get("route"), "path", "unmatched")
    record_http_request(
        request.method,
        route,
        response.status_code,
        time.perf_counter() - started,
    )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith(settings.api_prefix):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get(
    "/metrics",
    tags=["operations"],
    dependencies=[Depends(require_roles("admin"))],
    include_in_schema=True,
)
def metrics_endpoint():
    return Response(
        content=render_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


def record_audit(
    session: Session,
    tenant_id: str,
    action: str,
    resource_type: str,
    resource_id: str = "",
    details: dict | None = None,
    actor: str = "api",
) -> None:
    session.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor=actor,
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
    dependencies=[Depends(require_roles("operator", "admin"))],
)
def create_node(
    payload: NodeCreate,
    principal: CurrentPrincipal,
    session: DbSession,
):
    node = InfrastructureNode(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(node)
    try:
        session.flush()
        record_audit(
            session, principal.tenant_id, "node.created", "node", node.id,
            {"name": node.name}, actor=principal.actor,
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="A node with this name already exists in this tenant."
        ) from exc
    session.refresh(node)
    return node


@app.get(
    f"{settings.api_prefix}/nodes",
    response_model=list[NodeRead],
    dependencies=[Depends(require_roles("viewer", "operator", "admin", "ingestor"))],
)
def list_nodes(tenant_id: TenantId, session: DbSession):
    query = select(InfrastructureNode).where(
        InfrastructureNode.tenant_id == tenant_id
    ).order_by(InfrastructureNode.id)
    return list(session.scalars(query))


@app.post(
    f"{settings.api_prefix}/edges",
    response_model=EdgeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("operator", "admin"))],
)
def create_edge(
    payload: EdgeCreate,
    principal: CurrentPrincipal,
    session: DbSession,
):
    source = session.scalar(
        select(InfrastructureNode).where(
            InfrastructureNode.id == payload.source_id,
            InfrastructureNode.tenant_id == principal.tenant_id,
        )
    )
    target = session.scalar(
        select(InfrastructureNode).where(
            InfrastructureNode.id == payload.target_id,
            InfrastructureNode.tenant_id == principal.tenant_id,
        )
    )
    if source is None or target is None:
        raise HTTPException(status_code=404, detail="Both nodes must exist in the authenticated tenant.")
    edge = DependencyEdge(tenant_id=principal.tenant_id, **payload.model_dump())
    session.add(edge)
    try:
        session.flush()
        record_audit(
            session, principal.tenant_id, "dependency.created", "dependency", edge.id,
            {"source_id": edge.source_id, "target_id": edge.target_id},
            actor=principal.actor,
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="This dependency already exists in this tenant.") from exc
    session.refresh(edge)
    return edge


@app.get(
    f"{settings.api_prefix}/edges",
    response_model=list[EdgeRead],
    dependencies=[Depends(require_roles("viewer", "operator", "admin", "ingestor"))],
)
def list_edges(tenant_id: TenantId, session: DbSession):
    query = select(DependencyEdge).where(
        DependencyEdge.tenant_id == tenant_id
    ).order_by(DependencyEdge.id)
    return list(session.scalars(query))


@app.get(
    f"{settings.api_prefix}/topology",
    tags=["topology"],
    dependencies=[Depends(require_roles("viewer", "operator", "admin", "ingestor"))],
)
def get_topology(tenant_id: TenantId, session: DbSession):
    nodes = list(
        session.scalars(
            select(InfrastructureNode)
            .where(InfrastructureNode.tenant_id == tenant_id)
            .order_by(InfrastructureNode.id)
        )
    )
    edges = list(
        session.scalars(
            select(DependencyEdge)
            .where(DependencyEdge.tenant_id == tenant_id)
            .order_by(DependencyEdge.id)
        )
    )
    return {
        "nodes": [NodeRead.model_validate(node).model_dump(mode="json") for node in nodes],
        "edges": [EdgeRead.model_validate(edge).model_dump(mode="json") for edge in edges],
    }


@app.post(
    f"{settings.api_prefix}/simulations",
    response_model=SimulationResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("operator", "admin"))],
)
def run_simulation(
    payload: SimulationCreate,
    principal: CurrentPrincipal,
    session: DbSession,
):
    failed_node = session.scalar(
        select(InfrastructureNode).where(
            InfrastructureNode.id == payload.failed_node_id,
            InfrastructureNode.tenant_id == principal.tenant_id,
        )
    )
    if failed_node is None:
        raise HTTPException(status_code=404, detail="Failed node was not found in this tenant.")

    nodes = [
        {"id": n.id, "name": n.name, "kind": n.kind, "criticality": n.criticality}
        for n in session.scalars(
            select(InfrastructureNode).where(InfrastructureNode.tenant_id == principal.tenant_id)
        )
    ]
    edges = [
        {"source_id": e.source_id, "target_id": e.target_id, "criticality": e.criticality}
        for e in session.scalars(
            select(DependencyEdge).where(DependencyEdge.tenant_id == principal.tenant_id)
        )
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
        tenant_id=principal.tenant_id,
        failed_node_id=payload.failed_node_id,
        failure_mode=payload.failure_mode,
        result_json=result.model_dump_json(),
    )
    session.add(record)
    session.flush()
    record_audit(
        session, principal.tenant_id, "simulation.completed", "simulation", record.id,
        {"failed_node_id": payload.failed_node_id, "failure_mode": payload.failure_mode,
         "total_impacted": len(impacted)},
        actor=principal.actor,
    )
    session.commit()
    session.refresh(record)
    return result.model_copy(update={"simulation_id": record.id})


@app.get(
    f"{settings.api_prefix}/simulations/{{simulation_id}}",
    response_model=SimulationResult,
    dependencies=[Depends(require_roles("viewer", "operator", "admin", "ingestor"))],
)
def get_simulation(simulation_id: int, tenant_id: TenantId, session: DbSession):
    record = session.scalar(
        select(SimulationRecord).where(
            SimulationRecord.id == simulation_id,
            SimulationRecord.tenant_id == tenant_id,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Simulation was not found.")
    data = json.loads(record.result_json)
    data["simulation_id"] = record.id
    return SimulationResult(**data)


@app.post(
    f"{settings.api_prefix}/telemetry",
    response_model=TelemetryRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ingestor", "admin"))],
    tags=["observability"],
)
def ingest_telemetry(
    payload: TelemetryCreate,
    principal: CurrentPrincipal,
    session: DbSession,
):
    node = session.scalar(
        select(InfrastructureNode).where(
            InfrastructureNode.id == payload.node_id,
            InfrastructureNode.tenant_id == principal.tenant_id,
        )
    )
    if node is None:
        raise HTTPException(status_code=404, detail="Telemetry node was not found in this tenant.")
    sample = TelemetrySample(
        tenant_id=principal.tenant_id,
        node_id=payload.node_id,
        metric=payload.metric,
        value=payload.value,
        unit=payload.unit,
        observed_at=payload.observed_at or utc_now(),
    )
    session.add(sample)
    session.flush()
    record_audit(
        session, principal.tenant_id, "telemetry.ingested", "telemetry", sample.id,
        {"node_id": sample.node_id, "metric": sample.metric},
        actor=principal.actor,
    )
    session.commit()
    session.refresh(sample)
    return sample


@app.get(
    f"{settings.api_prefix}/telemetry",
    response_model=list[TelemetryRead],
    tags=["observability"],
    dependencies=[Depends(require_roles("viewer", "operator", "admin", "ingestor"))],
)
def list_telemetry(
    tenant_id: TenantId,
    session: DbSession,
    node_id: int | None = Query(default=None, gt=0),
    metric: str | None = Query(default=None, min_length=1, max_length=80),
    limit: int = Query(default=100, ge=1, le=1000),
):
    query = select(TelemetrySample).where(TelemetrySample.tenant_id == tenant_id)
    if node_id is not None:
        query = query.where(TelemetrySample.node_id == node_id)
    if metric is not None:
        query = query.where(TelemetrySample.metric == metric)
    query = query.order_by(TelemetrySample.observed_at.desc()).limit(limit)
    return list(session.scalars(query))


@app.get(
    f"{settings.api_prefix}/audit",
    response_model=list[AuditEventRead],
    tags=["governance"],
    dependencies=[Depends(require_roles("admin"))],
)
def list_audit_events(
    tenant_id: TenantId,
    session: DbSession,
    limit: int = Query(default=100, ge=1, le=1000),
    action: str | None = Query(default=None, min_length=1, max_length=80),
):
    query = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
    if action is not None:
        query = query.where(AuditEvent.action == action)
    query = query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit)
    return list(session.scalars(query))


@app.get(
    f"{settings.api_prefix}/audit/export",
    tags=["governance"],
    dependencies=[Depends(require_roles("admin"))],
)
def export_audit_events(
    tenant_id: TenantId,
    session: DbSession,
    limit: int = Query(default=1000, ge=1, le=10000),
):
    query = (
        select(AuditEvent)
        .where(AuditEvent.tenant_id == tenant_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(limit)
    )
    events = list(session.scalars(query))
    payload = [AuditEventRead.model_validate(event).model_dump(mode="json") for event in events]
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="oracle-audit-export.json"'},
    )


@app.post(
    f"{settings.api_prefix}/scenarios/compare",
    response_model=ScenarioCompareResult,
    tags=["scenarios"],
    dependencies=[Depends(require_roles("operator", "admin"))],
)
def compare_scenarios(
    payload: ScenarioCompareCreate,
    principal: CurrentPrincipal,
    session: DbSession,
):
    tenant_id = principal.tenant_id
    nodes = [
        {"id": n.id, "name": n.name, "kind": n.kind, "criticality": n.criticality}
        for n in session.scalars(
            select(InfrastructureNode).where(InfrastructureNode.tenant_id == tenant_id)
        )
    ]
    node_ids = {node["id"] for node in nodes}
    for scenario in (payload.scenario_a, payload.scenario_b):
        if scenario.failed_node_id not in node_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Scenario node {scenario.failed_node_id} was not found in this tenant.",
            )

    edges = [
        {"source_id": e.source_id, "target_id": e.target_id, "criticality": e.criticality}
        for e in session.scalars(
            select(DependencyEdge).where(DependencyEdge.tenant_id == tenant_id)
        )
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
        session, tenant_id, "scenario.compared", "scenario", "",
        {
            "scenario_a_failed_node_id": payload.scenario_a.failed_node_id,
            "scenario_b_failed_node_id": payload.scenario_b.failed_node_id,
            "scenario_a_impacted": len(ids_a),
            "scenario_b_impacted": len(ids_b),
        },
        actor=principal.actor,
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
    dependencies=[Depends(require_roles("operator", "admin"))],
)
def explain_simulation_with_ai(
    payload: AIExplainRequest,
    principal: CurrentPrincipal,
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

    record = session.scalar(
        select(SimulationRecord).where(
            SimulationRecord.id == payload.simulation_id,
            SimulationRecord.tenant_id == principal.tenant_id,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Simulation was not found.")
    simulation_data = json.loads(record.result_json)
    failed_node = session.scalar(
        select(InfrastructureNode).where(
            InfrastructureNode.id == record.failed_node_id,
            InfrastructureNode.tenant_id == principal.tenant_id,
        )
    )
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
        principal.tenant_id,
        "ai.explanation.generated",
        "simulation",
        record.id,
        {"provider": "deepseek", "model": settings.deepseek_model},
        actor=principal.actor,
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
