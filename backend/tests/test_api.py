from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from oracle_api.config import Settings, settings
from oracle_api import main as oracle_main
from oracle_api.main import app


def test_oracle_api_keys_environment_alias_is_loaded():
    configured = Settings(_env_file=None, ORACLE_API_KEYS="opaque-token|tenant-a|admin")
    assert configured.api_keys == "opaque-token|tenant-a|admin"


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        nodes = client.get("/api/v1/nodes")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert nodes.headers["cache-control"] == "no-store"

def test_prometheus_metrics_endpoint_returns_request_counters():
    with TestClient(app) as client:
        health = client.get("/health")
        metrics = client.get("/metrics")
    assert health.status_code == 200
    assert metrics.status_code == 200
    assert "text/plain" in metrics.headers["content-type"]
    assert "oracle_http_requests_total" in metrics.text
    assert 'route="/health"' in metrics.text



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


def test_scenario_comparison_reports_impact_differences():
    tenant = f"scenario-{uuid4().hex}"
    with TestClient(app) as client:
        consumer = client.post(
            "/api/v1/nodes",
            headers={"X-Tenant-ID": tenant},
            json={"name": f"consumer-{uuid4().hex[:10]}", "kind": "service", "criticality": 0.9},
        )
        dependency = client.post(
            "/api/v1/nodes",
            headers={"X-Tenant-ID": tenant},
            json={"name": f"dependency-{uuid4().hex[:10]}", "kind": "database", "criticality": 1.0},
        )
        isolated = client.post(
            "/api/v1/nodes",
            headers={"X-Tenant-ID": tenant},
            json={"name": f"isolated-{uuid4().hex[:10]}", "kind": "worker", "criticality": 0.3},
        )
        assert consumer.status_code == dependency.status_code == isolated.status_code == 201
        edge = client.post(
            "/api/v1/edges",
            headers={"X-Tenant-ID": tenant},
            json={
                "source_id": consumer.json()["id"],
                "target_id": dependency.json()["id"],
                "criticality": 0.95,
            },
        )
        assert edge.status_code == 201

        compared = client.post(
            "/api/v1/scenarios/compare",
            headers={"X-Tenant-ID": tenant},
            json={
                "scenario_a": {"failed_node_id": dependency.json()["id"], "failure_mode": "unavailable"},
                "scenario_b": {"failed_node_id": isolated.json()["id"], "failure_mode": "unavailable"},
            },
        )
        assert compared.status_code == 200
        result = compared.json()
        assert result["newly_impacted_in_a"] == [consumer.json()["id"]]
        assert result["newly_impacted_in_b"] == []
        assert result["impact_score_deltas"][0]["score_a"] > 0
        events = client.get("/api/v1/audit", headers={"X-Tenant-ID": tenant}).json()
        assert "scenario.compared" in {event["action"] for event in events}



def test_ai_explanation_is_disabled_without_explicit_opt_in(monkeypatch):
    monkeypatch.setattr(settings, "ai_data_sharing_enabled", False)
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/explain", json={"simulation_id": 999999})
    assert response.status_code == 403


def test_ai_explanation_requires_server_side_api_key(monkeypatch):
    monkeypatch.setattr(settings, "ai_data_sharing_enabled", True)
    monkeypatch.setattr(settings, "deepseek_api_key", "")
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/explain", json={"simulation_id": 999999})
    assert response.status_code == 503


def test_api_key_rbac_and_tenant_isolation(monkeypatch):
    monkeypatch.setattr(
        settings,
        "api_keys",
        "viewer-a|tenant-a|viewer;operator-a|tenant-a|operator;"
        "admin-a|tenant-a|admin;admin-b|tenant-b|admin",
    )
    with TestClient(app) as client:
        denied_write = client.post(
            "/api/v1/nodes",
            headers={"X-API-Key": "viewer-a"},
            json={"name": "blocked-by-rbac", "kind": "service"},
        )
        assert denied_write.status_code == 403

        created = client.post(
            "/api/v1/nodes",
            headers={"Authorization": "Bearer operator-a"},
            json={"name": "isolated-component", "kind": "service", "criticality": 0.7},
        )
        assert created.status_code == 201
        assert created.json()["tenant_id"] == "tenant-a"

        same_name_other_tenant = client.post(
            "/api/v1/nodes",
            headers={"X-API-Key": "admin-b"},
            json={"name": "isolated-component", "kind": "database", "criticality": 0.5},
        )
        assert same_name_other_tenant.status_code == 201
        assert same_name_other_tenant.json()["tenant_id"] == "tenant-b"

        tenant_a_nodes = client.get("/api/v1/nodes", headers={"X-API-Key": "viewer-a"})
        tenant_b_nodes = client.get("/api/v1/nodes", headers={"X-API-Key": "admin-b"})
        assert [node["tenant_id"] for node in tenant_a_nodes.json()] == ["tenant-a"]
        assert [node["tenant_id"] for node in tenant_b_nodes.json()] == ["tenant-b"]

        forged_tenant = client.get(
            "/api/v1/nodes",
            headers={"X-API-Key": "viewer-a", "X-Tenant-ID": "tenant-b"},
        )
        assert forged_tenant.status_code == 403
        audit_denied = client.get("/api/v1/audit", headers={"X-API-Key": "viewer-a"})
        assert audit_denied.status_code == 403
        metrics_denied = client.get("/metrics", headers={"X-API-Key": "viewer-a"})
        assert metrics_denied.status_code == 403

        cross_tenant_edge = client.post(
            "/api/v1/edges",
            headers={"X-API-Key": "operator-a"},
            json={
                "source_id": created.json()["id"],
                "target_id": same_name_other_tenant.json()["id"],
                "criticality": 0.5,
            },
        )
        assert cross_tenant_edge.status_code == 404

        foreign_simulation = client.post(
            "/api/v1/simulations",
            headers={"X-API-Key": "operator-a"},
            json={
                "failed_node_id": same_name_other_tenant.json()["id"],
                "failure_mode": "unavailable",
            },
        )
        assert foreign_simulation.status_code == 404

        tenant_b_simulation = client.post(
            "/api/v1/simulations",
            headers={"X-API-Key": "admin-b"},
            json={
                "failed_node_id": same_name_other_tenant.json()["id"],
                "failure_mode": "unavailable",
            },
        )
        assert tenant_b_simulation.status_code == 201
        foreign_simulation_read = client.get(
            f"/api/v1/simulations/{tenant_b_simulation.json()['simulation_id']}",
            headers={"X-API-Key": "viewer-a"},
        )
        assert foreign_simulation_read.status_code == 404


def test_audit_export_is_admin_only_and_tenant_scoped(monkeypatch):
    monkeypatch.setattr(
        settings,
        "api_keys",
        "admin-a|tenant-a|admin;admin-b|tenant-b|admin;viewer-a|tenant-a|viewer",
    )
    with TestClient(app) as client:
        for token, name in (("admin-a", "event-for-a"), ("admin-b", "event-for-b")):
            created = client.post(
                "/api/v1/nodes",
                headers={"X-API-Key": token},
                json={"name": f"{name}-{uuid4().hex[:8]}", "kind": "service"},
            )
            assert created.status_code == 201

        forbidden = client.get(
            "/api/v1/audit/export",
            headers={"X-API-Key": "viewer-a"},
        )
        assert forbidden.status_code == 403

        export = client.get(
            "/api/v1/audit/export",
            headers={"X-API-Key": "admin-a"},
        )
        assert export.status_code == 200
        assert "attachment;" in export.headers["content-disposition"]
        assert "event-for-a" in export.text
        assert "event-for-b" not in export.text


def test_invalid_api_key_is_rejected_when_credentials_are_configured(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", "valid-token|tenant-a|viewer")
    with TestClient(app) as client:
        response = client.get("/api/v1/nodes", headers={"X-API-Key": "invalid-token"})
    assert response.status_code == 401



def test_production_startup_fails_without_api_credentials(monkeypatch):
    monkeypatch.setattr(settings, "oracle_env", "production")
    monkeypatch.setattr(settings, "api_keys", "")
    with pytest.raises(RuntimeError, match="ORACLE_API_KEYS"), TestClient(app):
        pass


def test_deepseek_explanation_success_is_mocked_and_audited(monkeypatch):
    monkeypatch.setattr(settings, "oracle_env", "development")
    monkeypatch.setattr(settings, "api_keys", "")
    monkeypatch.setattr(settings, "ai_data_sharing_enabled", True)
    monkeypatch.setattr(settings, "deepseek_api_key", "test-deepseek-key")
    monkeypatch.setattr(settings, "deepseek_model", "deepseek-flash")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {"message": {"content": "A simulação identificou um consumidor dependente."}}
                ]
            }

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def post(self, endpoint, json, headers):
            captured["endpoint"] = endpoint
            captured["payload"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(oracle_main.httpx, "Client", FakeClient)
    tenant = f"deepseek-{uuid4().hex}"
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/nodes",
            headers={"X-Tenant-ID": tenant},
            json={
                "name": f"deepseek-node-{uuid4().hex[:10]}",
                "kind": "service",
                "criticality": 0.7,
            },
        )
        assert created.status_code == 201
        simulation = client.post(
            "/api/v1/simulations",
            headers={"X-Tenant-ID": tenant},
            json={"failed_node_id": created.json()["id"], "failure_mode": "unavailable"},
        )
        assert simulation.status_code == 201
        explained = client.post(
            "/api/v1/ai/explain",
            headers={"X-Tenant-ID": tenant},
            json={"simulation_id": simulation.json()["simulation_id"]},
        )
        assert explained.status_code == 200
        assert "consumidor dependente" in explained.json()["explanation"]
        audit = client.get("/api/v1/audit", headers={"X-Tenant-ID": tenant})
        assert "ai.explanation.generated" in {event["action"] for event in audit.json()}

    assert captured["endpoint"].endswith("/chat/completions")
    assert captured["payload"]["model"] == "deepseek-flash"
    assert captured["headers"]["Authorization"] == "Bearer test-deepseek-key"
    assert captured["payload"]["stream"] is False


def test_topology_snapshots_capture_each_graph_change_and_are_tenant_scoped():
    tenant_a = f"history-a-{uuid4().hex}"
    tenant_b = f"history-b-{uuid4().hex}"
    headers_a = {"X-Tenant-ID": tenant_a}
    headers_b = {"X-Tenant-ID": tenant_b}

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/nodes",
            headers=headers_a,
            json={"name": f"history-a-one-{uuid4().hex[:8]}", "kind": "service"},
        )
        second = client.post(
            "/api/v1/nodes",
            headers=headers_a,
            json={"name": f"history-a-two-{uuid4().hex[:8]}", "kind": "database"},
        )
        assert first.status_code == second.status_code == 201

        edge = client.post(
            "/api/v1/edges",
            headers=headers_a,
            json={
                "source_id": first.json()["id"],
                "target_id": second.json()["id"],
                "criticality": 0.9,
            },
        )
        assert edge.status_code == 201

        other = client.post(
            "/api/v1/nodes",
            headers=headers_b,
            json={"name": f"history-b-one-{uuid4().hex[:8]}", "kind": "worker"},
        )
        assert other.status_code == 201

        history_a = client.get("/api/v1/topology/snapshots", headers=headers_a)
        history_b = client.get("/api/v1/topology/snapshots", headers=headers_b)
        assert history_a.status_code == history_b.status_code == 200
        versions_a = [item["version"] for item in history_a.json()]
        versions_b = [item["version"] for item in history_b.json()]
        assert len(versions_a) == 3
        assert versions_a == sorted(versions_a, reverse=True)
        assert len(set(versions_a)) == 3
        assert all(item["version"] == item["id"] for item in history_a.json())
        assert all(item["tenant_id"] == tenant_a for item in history_a.json())
        assert len(versions_b) == 1
        assert versions_b[0] > versions_a[0]

        latest_id = history_a.json()[0]["id"]
        latest = client.get(f"/api/v1/topology/snapshots/{latest_id}", headers=headers_a)
        assert latest.status_code == 200
        assert latest.json()["node_count"] == 2
        assert latest.json()["edge_count"] == 1
        assert len(latest.json()["edges"]) == 1
        assert {"capacity_units", "current_load_units"} <= set(latest.json()["nodes"][0])


        foreign = client.get(
            f"/api/v1/topology/snapshots/{latest_id}",
            headers=headers_b,
        )
        assert foreign.status_code == 404



def test_capacity_assessment_uses_only_authenticated_tenant_nodes():
    tenant_a = f"capacity-a-{uuid4().hex}"
    tenant_b = f"capacity-b-{uuid4().hex}"
    with TestClient(app) as client:
        a = client.post(
            "/api/v1/nodes",
            headers={"X-Tenant-ID": tenant_a},
            json={
                "name": f"capacity-a-{uuid4().hex[:8]}",
                "kind": "service",
                "capacity_units": 100,
                "current_load_units": 85,
            },
        )
        b = client.post(
            "/api/v1/nodes",
            headers={"X-Tenant-ID": tenant_b},
            json={
                "name": f"capacity-b-{uuid4().hex[:8]}",
                "kind": "database",
                "capacity_units": 200,
                "current_load_units": 25,
            },
        )
        assert a.status_code == b.status_code == 201

        assessment = client.get(
            "/api/v1/capacity/assessment?demand_multiplier=1.2",
            headers={"X-Tenant-ID": tenant_a},
        )
        assert assessment.status_code == 200
        result = assessment.json()
        assert result["components_assessed"] == 1
        assert result["over_capacity"] == 1
        assert result["components"][0]["node_id"] == a.json()["id"]
        assert result["components"][0]["projected_load_units"] == 102.0
        assert result["components"][0]["utilization_ratio"] == 1.02
