# ORACLE Development Roadmap

A phase is complete only when its implementation, tests, documentation and CI evidence are present. This table describes the actual repository state; a partial capability is not equivalent to enterprise readiness.

| Phase | Scope | Status |
|---|---|---|
| 1. Foundation | Graph model, deterministic simulation, REST API, persistence, containers | Baseline implemented; expanded endpoint tests are being validated in CI |
| 2. Enterprise identity | OIDC/SSO, RBAC, tenant isolation, secure sessions | Tenant-scoped API keys, viewer/operator/ingestor/admin role gates, tenant-owned nodes/edges/simulations and filtered queries implemented; OIDC/SSO and managed key rotation remain open |
| 3. Governance | Audit trail, retention, data export, policy controls | Basic append-on-write audit events and tenant-filtered audit reads implemented; immutability, retention and export controls remain open |
| 4. Observability | OpenTelemetry traces/metrics, telemetry ingestion, health signals | Metric sample ingestion/query and health endpoint implemented; OpenTelemetry export, alerting and service-level signals remain open |
| 5. Digital twin evolution | Temporal topology, scenario comparison, capacity models | Deterministic comparison of two failure scenarios implemented; topology versioning and capacity models remain open |
| 6. AI assistance | Optional provider integration, grounded explanations, human review | Optional DeepSeek explanation endpoint implemented with explicit outbound-data opt-in and API gate; provider success path still requires live-key validation |
| 7. Web console | Topology visualization, scenario builder, history, administration | Starter console reads inventory; interactive topology and scenario workflows remain open |
| 8. Production readiness | Threat-model closure, load/security tests, SBOM, signed releases, backup/restore | Not production-ready; CI and operational hardening still require validation |

## Security boundary

API credentials are configured with ORACLE_API_KEYS as token|tenant-id|role entries. When credentials are configured, the tenant comes from the matched credential and a mismatching X-Tenant-ID is rejected. In development/test only, empty ORACLE_API_KEYS enables a local admin convenience mode. Production startup refuses to proceed without configured API keys. OIDC/SSO, self-service key provisioning, rotation and revocation workflows remain future work. Run `alembic upgrade head` before deploying the schema changes; existing rows migrate to tenant `default`.

Do not interpret a roadmap item as an existing feature.
