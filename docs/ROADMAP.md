# ORACLE Development Roadmap

A phase is complete only when its implementation, tests, documentation and CI evidence are present. This table describes the actual repository state; a partial capability is not equivalent to enterprise readiness.

| Phase | Scope | Status |
|---|---|---|
| 1. Foundation | Graph model, deterministic simulation, REST API, persistence, containers | Baseline implemented; Ruff, backend tests, migration checks, frontend build and pip-audit have passed in GitHub Actions |
| 2. Enterprise identity | OIDC/SSO, RBAC, tenant isolation, secure sessions | Tenant-scoped API keys, viewer/operator/ingestor/admin role gates, tenant-owned nodes/edges/simulations and filtered queries implemented; OIDC/SSO and managed key rotation remain open |
| 3. Governance | Audit trail, retention, data export, policy controls | Basic append-on-write audit events, tenant-filtered reads and admin-only JSON export implemented; tamper-evident storage, retention policies and compliance workflows remain open |
| 4. Observability | OpenTelemetry traces/metrics, telemetry ingestion, health signals | Tenant-scoped metric sample ingestion/query, health endpoint and admin-protected Prometheus HTTP request metrics implemented; OpenTelemetry traces/export, alerting and SLOs remain open |
| 5. Digital twin evolution | Temporal topology, scenario comparison, capacity models | Deterministic comparison of two failure scenarios implemented; topology versioning, time-based replay and capacity models remain open |
| 6. AI assistance | Optional provider integration, grounded explanations, human review | Optional DeepSeek explanation endpoint implemented with explicit outbound-data opt-in and API gate; automated tests mock provider responses, live-key validation remains deployment-specific |
| 7. Web console | Topology visualization, scenario builder, history, administration | Component/dependency editors, SVG topology graph, single and comparative simulations, telemetry/audit views, session-scoped API key input and admin audit export implemented; richer history and administration remain open |
| 8. Production readiness | Threat-model closure, load/security tests, SBOM, signed releases, backup/restore | CI, dependency audit and schema migration validation implemented; load/penetration testing, SBOM, signed releases, backup/restore drills and independent security review remain open |

## Security boundary

API credentials are configured with ORACLE_API_KEYS as token|tenant-id|role entries. When credentials are configured, the tenant comes from the matched credential and a mismatching X-Tenant-ID is rejected. In development/test only, empty ORACLE_API_KEYS enables a local admin convenience mode. Production startup refuses to proceed without configured API keys. OIDC/SSO, self-service key provisioning, rotation and revocation workflows remain future work. Run `alembic upgrade head` before deploying the schema changes; existing rows migrate to tenant `default`.

Do not interpret a roadmap item as an existing feature.
