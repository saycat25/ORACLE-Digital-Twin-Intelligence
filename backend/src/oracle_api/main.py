import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from oracle_api.config import settings
from oracle_api.db import Base, engine, get_session
from oracle_api.engine import analyze_impact
from oracle_api.models import DependencyEdge, InfrastructureNode, SimulationRecord
from oracle_api.schemas import EdgeCreate, EdgeRead, NodeCreate, NodeRead, SimulationCreate, SimulationResult


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="ORACLE Digital Twin Intelligence API",
    version="0.1.0",
    description="Explainable infrastructure topology and failure-impact simulation.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health", tags=["operations"])
def health():
    return {"status": "ok", "service": "oracle-api", "version": app.version}


@app.post(f"{settings.api_prefix}/nodes", response_model=NodeRead, status_code=status.HTTP_201_CREATED)
def create_node(payload: NodeCreate, session: Session = Depends(get_session)):
    node = InfrastructureNode(**payload.model_dump())
    session.add(node)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="A node with this name already exists.") from exc
    session.refresh(node)
    return node


@app.get(f"{settings.api_prefix}/nodes", response_model=list[NodeRead])
def list_nodes(session: Session = Depends(get_session)):
    return list(session.scalars(select(InfrastructureNode).order_by(InfrastructureNode.id)))


@app.post(f"{settings.api_prefix}/edges", response_model=EdgeRead, status_code=status.HTTP_201_CREATED)
def create_edge(payload: EdgeCreate, session: Session = Depends(get_session)):
    source = session.get(InfrastructureNode, payload.source_id)
    target = session.get(InfrastructureNode, payload.target_id)
    if source is None or target is None:
        raise HTTPException(status_code=404, detail="Both source and target nodes must exist.")
    edge = DependencyEdge(**payload.model_dump())
    session.add(edge)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="This dependency already exists.") from exc
    session.refresh(edge)
    return edge


@app.get(f"{settings.api_prefix}/edges", response_model=list[EdgeRead])
def list_edges(session: Session = Depends(get_session)):
    return list(session.scalars(select(DependencyEdge).order_by(DependencyEdge.id)))


@app.post(f"{settings.api_prefix}/simulations", response_model=SimulationResult,
          status_code=status.HTTP_201_CREATED)
def run_simulation(payload: SimulationCreate, session: Session = Depends(get_session)):
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
    session.commit()
    session.refresh(record)
    return result.model_copy(update={"simulation_id": record.id})


@app.get(f"{settings.api_prefix}/simulations/{{simulation_id}}", response_model=SimulationResult)
def get_simulation(simulation_id: int, session: Session = Depends(get_session)):
    record = session.get(SimulationRecord, simulation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Simulation was not found.")
    data = json.loads(record.result_json)
    data["simulation_id"] = record.id
    return SimulationResult(**data)
