# ORACLE Development Roadmap

A phase is complete only when its implementation, tests, documentation and CI evidence are present. This table describes the actual repository state; a partial capability is not equivalent to enterprise readiness.

| Phase | Scope | Status |
|---|---|---|
| 1. Foundation | Graph model, deterministic simulation, REST API, persistence, containers | Baseline implemented; expanded endpoint tests are being validated in CI |
| 2. Enterprise identity | OIDC/SSO, RBAC, tenant isolation, secure sessions | Not implemented; tenant headers currently label audit/telemetry records only and are not an authorization boundary |
| 3. Governance | Audit trail, retention, data export, policy controls | Basic append-on-write audit events and tenant-filtered audit reads implemented; immutability, retention and export controls remain open |
| 4. Observability | OpenTelemetry traces/metrics, telemetry ingestion, health signals | Metric sample ingestion/query and health endpoint implemented; OpenTelemetry export, alerting and service-level signals remain open |
| 5. Digital twin evolution | Temporal topology, scenario comparison, capacity models | Deterministic comparison of two failure scenarios implemented; topology versioning and capacity models remain open |
| 6. AI assistance | Optional provider integration, grounded explanations, human review | Not implemented |
| 7. Web console | Topology visualization, scenario builder, history, administration | Starter console reads inventory; interactive topology and scenario workflows remain open |
| 8. Production readiness | Threat-model closure, load/security tests, SBOM, signed releases, backup/restore | Not production-ready; CI and operational hardening still require validation |

## Security boundary

The X-Tenant-ID header is an organizational label for audit and telemetry records only. It does **not** isolate infrastructure nodes, dependency edges or simulations, and it must not be treated as authentication or authorization. The optional INGESTION_API_KEY protects the telemetry ingestion endpoint when configured. Deployments exposed beyond localhost must configure a strong secret and add a proper identity provider and tenant-aware data model first.

Do not interpret a roadmap item as an existing feature.
