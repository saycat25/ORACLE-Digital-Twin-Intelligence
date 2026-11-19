# ORACLE Development Roadmap

A phase is complete only when its implementation, tests, documentation and CI evidence are present. This table describes the actual repository state; a partial capability is not equivalent to enterprise readiness.

| Phase | Scope | Status |
|---|---|---|
| 1. Foundation | Graph model, deterministic simulation, REST API, persistence, containers | Baseline implemented; Ruff, backend tests, migration checks, frontend build and pip-audit have passed in GitHub Actions |
| 2. Enterprise identity | OIDC/SSO, RBAC, tenant isolation, secure sessions | Tenant-scoped API keys, viewer/operator/ingestor/admin role gates, tenant-owned nodes/edges/simulations and filtered queries implemented; OIDC/SSO and managed key rotation remain open |
| 3. Governance | Audit trail, retention, data export, policy controls | Basic append-on-write audit events, tenant-filtered reads and admin-only JSON export implemented; tamper-evident storage, retention policies and compliance workflows remain open |
| 4. Observability | OpenTelemetry traces/metrics, telemetry ingestion, health signals | Tenant-scoped metric sample ingestion/query, health endpoint, admin-protected Prometheus HTTP metrics and optional OpenTelemetry HTTP spans with OTLP/HTTP export implemented; alerting, SLOs and richer business-level traces remain open |
| 5. Digital twin evolution | Temporal topology, scenario comparison, capacity models | Automatic tenant-scoped topology snapshots on every node/edge change and two-scenario impact comparison implemented; time-based replay, snapshot diff and capacity models remain open |
| 6. AI assistance | Optional provider integration, grounded explanations, human review | Optional DeepSeek explanation endpoint implemented with explicit outbound-data opt-in and API gate; automated tests mock provider responses, live-key validation remains deployment-specific |
| 7. Web console | Topology visualization, scenario builder, history, administration | Component/dependency editors, SVG topology graph, single and comparative simulations, telemetry/audit views, session-scoped API key input, admin audit export and historical topology snapshot browsing implemented; richer administration remains open |
| 8. Production readiness | Threat-model closure, load/security tests, SBOM, signed releases, backup/restore | CI, pip-audit, tenant migration checks, response security headers and CodeQL workflows for Python/TypeScript implemented; load/penetration testing, SBOM, signed releases, backup/restore drills and independent security review remain open |

## Security boundary

API credentials are configured with ORACLE_API_KEYS as token|tenant-id|role entries. When credentials are configured, the tenant comes from the matched credential and a mismatching X-Tenant-ID is rejected. In development/test only, empty ORACLE_API_KEYS enables a local admin convenience mode. Production startup refuses to proceed without configured API keys. OIDC/SSO, self-service key provisioning, rotation and revocation workflows remain future work. Run `alembic upgrade head` before deploying the schema changes; existing rows migrate to tenant `default`.

Do not interpret a roadmap item as an existing feature.
