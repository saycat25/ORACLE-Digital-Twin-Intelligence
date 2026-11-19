# ORACLE API

FastAPI service for infrastructure inventory, dependency topology, deterministic failure simulations, telemetry samples and audit events.

## Run locally

```bash
pip install -e ".[dev]"
alembic upgrade head
uvicorn oracle_api.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

## Main endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Service health |
| GET | /metrics | Authenticated Prometheus-compatible HTTP request metrics (admin role) |
| POST/GET | /api/v1/nodes | Infrastructure components |
| POST/GET | /api/v1/edges | Directed dependency edges |
| GET | /api/v1/topology | Current graph snapshot (nodes and edges) |
| GET | /api/v1/topology/snapshots | Tenant-scoped topology version history |
| GET | /api/v1/topology/snapshots/{id} | Read a historical topology version |
| GET | /api/v1/capacity/assessment | Project component capacity under a demand multiplier |
| POST | /api/v1/scenarios/compare | Compare impacted components and impact-score deltas across two failure scenarios |
| POST | /api/v1/ai/explain | Generate an optional DeepSeek explanation for a saved simulation |
| POST/GET | /api/v1/simulations, /api/v1/simulations/{id} | Failure impact simulations and result retrieval |
| POST/GET | /api/v1/telemetry | Ingest and query metric samples |
| GET | /api/v1/audit | Query audit events (admin only) |
| GET | /api/v1/audit/export | Download tenant-scoped audit events as JSON (admin only) |
| GET | /api/v1/audit/verify | Verify event HMAC integrity (admin only) |

## HTTP metrics and telemetry ingestion

The `/metrics` endpoint exports request totals and duration summaries in Prometheus text format. It is restricted to the admin role. Labels use route templates to avoid exposing request IDs or unbounded URL values. HTTP requests also create OpenTelemetry spans. Set `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` to a Collector's OTLP/HTTP traces endpoint to enable export; leave it empty to disable outbound tracing.

## Capacity assessment

Nodes accept `capacity_units` and `current_load_units`. `GET /api/v1/capacity/assessment?demand_multiplier=1.25` calculates projected utilization and headroom; values at or above 80% are warnings and values at or above 100% are marked over capacity. This model uses operator-declared capacity/load only. It does not assume automatic failover, traffic routing or unobserved spare capacity.

## Audit integrity and credentials

Set AUDIT_HMAC_KEY to at least 32 cryptographically random bytes; production startup requires it and uses it to HMAC-sign each audit event. Keep the key outside the database and repository. Existing audit events from before this migration have no digest and are reported as legacy/unverified. Use GET /api/v1/audit/verify to detect changes to signed records.

Set ORACLE_API_KEYS to a semicolon-separated list of API credentials in the format token|tenant-id|role. Supported roles are viewer, operator, admin and ingestor. Send the token with X-API-Key or Authorization: Bearer. The tenant is taken from the credential; an optional X-Tenant-ID must match it. A credential cannot select another tenant.

Viewer: read inventory/topology, simulations and telemetry. Operator: viewer access plus inventory changes, simulations, scenario comparison and AI explanation. Ingestor: read access plus telemetry ingestion. Admin: all operations including audit events.

In development/test mode only, when ORACLE_API_KEYS is empty, requests are treated as an admin in the tenant supplied by X-Tenant-ID (or default). In production, ORACLE_API_KEYS is mandatory and the API refuses to start without it. Do not use development mode on a public deployment.

Every component or dependency creation records a new topology version. Historical snapshots can be listed and read, but are not restored by this release. Run `alembic upgrade head` before starting the service; migration `0003_node_capacity` adds capacity fields with conservative defaults for existing nodes. Migration 0001 assigns existing legacy records to tenant `default`; migrations 0002–0004 add topology history, capacity fields and audit integrity hashes. Legacy audit events retain an empty digest and are reported as unverified. HMAC signatures detect modifications to signed records, but do not by themselves detect deletion/reordering; use an external append-only archive for that guarantee.

## Telemetry ingestion

The `POST /api/v1/telemetry` endpoint accepts `node_id`, `metric`, `value`, `unit` and optional `observed_at`.

## Optional DeepSeek assistance

Set DEEPSEEK_API_KEY, and explicitly set AI_DATA_SHARING_ENABLED=true to permit sending the selected saved simulation result to DeepSeek. The integration uses DEEPSEEK_BASE_URL (default https://api.deepseek.com), DEEPSEEK_MODEL (default deepseek-flash) and a configurable timeout. Without the opt-in flag, the endpoint returns 403 and sends no data. Review the data-sharing implications before enabling this feature.

## Operations

See the [operations runbook](../docs/OPERATIONS.md) for Docker Compose setup, configuration, PostgreSQL backup/restore, and release artifact verification.

## Validation

```bash
pytest
ruff check .
```
