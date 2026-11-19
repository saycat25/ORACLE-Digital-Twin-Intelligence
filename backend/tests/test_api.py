from uuid import uuid4

from fastapi.testclient import TestClient

from oracle_api.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_telemetry_ingestion_and_audit_trail():
    tenant = f"pytest-{uuid4().hex}"
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/nodes",
            headers={"X-Tenant-ID": tenant},
            json={
                "name": f"telemetry-node-{uuid4().hex[:12]}",
                "kind": "service",
                "criticality": 0.8,
                "description": "API integration test",
            },
        )
        assert created.status_code == 201
        node_id = created.json()["id"]

        ingested = client.post(
            "/api/v1/telemetry",
            headers={"X-Tenant-ID": tenant},
            json={
                "node_id": node_id,
                "metric": "cpu.utilization",
                "value": 73.5,
                "unit": "percent",
            },
        )
        assert ingested.status_code == 201
        assert ingested.json()["metric"] == "cpu.utilization"
        assert ingested.json()["value"] == 73.5

        samples = client.get("/api/v1/telemetry", headers={"X-Tenant-ID": tenant})
        assert samples.status_code == 200
        assert len(samples.json()) == 1
        assert samples.json()[0]["node_id"] == node_id

        audit = client.get("/api/v1/audit", headers={"X-Tenant-ID": tenant})
        assert audit.status_code == 200
        actions = {event["action"] for event in audit.json()}
        assert {"node.created", "telemetry.ingested"} <= actions


def test_topology_endpoint_returns_nodes_and_edges():
    with TestClient(app) as client:
        response = client.get("/api/v1/topology")
    assert response.status_code == 200
    assert set(response.json()) == {"nodes", "edges"}
