# ORACLE Threat Model — Current Baseline

## Scope

This threat model covers the current development release: FastAPI REST API, tenant-scoped relational persistence, role-based API keys, infrastructure graph, deterministic simulations, topology history, telemetry ingestion, audit export, optional OpenTelemetry export, optional DeepSeek explanations, and the React web console.

This is a baseline assessment, not an independent security certification.

## Assets

- Infrastructure topology, component names, relationships and criticality.
- Telemetry samples and historical topology snapshots.
- Simulation inputs, results and AI-generated explanations.
- Audit records and exported audit files.
- API credentials, DeepSeek credentials, database credentials and OTLP endpoints.
- Database integrity, availability and backup recoverability.

## Trust boundaries

- Browser to API: API key crosses the HTTP boundary; deployments must use TLS.
- API to database: database credentials and SQL access are privileged.
- API key to tenant context: the credential selects the tenant and role.
- API to external telemetry collector: OTLP export is optional and configured by endpoint.
- API to DeepSeek: outbound simulation data sharing is disabled unless explicitly enabled.
- CI runner to repository, package registries and GitHub security analysis.

## Controls currently implemented

- API keys are assigned a tenant and one of four roles: viewer, operator, ingestor or admin.
- Production startup fails when the API-key registry is empty.
- Nodes, edges, simulations, telemetry, audit queries and topology snapshots are filtered by the authenticated tenant.
- Cross-tenant resource references are rejected by API-level validation and integration tests.
- Audit reads/exports, HMAC verification and Prometheus metrics require the admin role.
- Each new audit event is HMAC-SHA256 signed using AUDIT_HMAC_KEY; production startup requires a key of at least 32 bytes. Legacy events remain explicitly unverified.
- Telemetry ingestion requires the ingestor or admin role.
- DeepSeek explanations require both a server API key and explicit data-sharing opt-in; only the selected stored simulation result is sent.
- OpenTelemetry trace export is disabled unless an OTLP traces endpoint is configured.
- API responses include basic security headers; API responses are marked no-store.
- Alembic migrations, pytest, Ruff, pip-audit and CodeQL workflows are part of repository validation.

## Threats and remaining mitigations

| Threat | Current mitigation | Remaining work |
|---|---|---|
| Unauthenticated API exposure | API-key registry and production startup gate | OIDC/SSO, user sessions, managed credential provisioning/rotation/revocation |
| Cross-tenant data access | Credential-bound tenant, scoped API queries and integration tests | Database-level composite tenant constraints, independent penetration testing |
| Credential theft | Secrets are supplied by environment configuration; browser stores the API key in sessionStorage | Secret-manager integration, key hashing/storage strategy, automatic rotation and revocation |
| Malicious or oversized input | Pydantic validation and bounded list limits | Request-body limits, rate limiting, fuzzing and load tests |
| Audit tampering | Per-event HMAC-SHA256 signatures verified by an admin-only endpoint | External immutable archive, deletion detection, retention policy, key rotation and protected key backup |
| Database loss/corruption | PostgreSQL volume and migration framework | Automated backup/restore tooling, restore drills and recovery objectives |
| Dependency or source compromise | pip-audit and CodeQL workflows | SBOM generation, artifact signing and release provenance |
| External AI data exposure | DeepSeek outbound sharing disabled by default and explicit server opt-in | Organization-level policy approval, provider contractual review and detailed outbound audit |
| Unsafe operational integration | Simulation engine is analytical and does not modify target infrastructure | Production integrations must remain read-only by default and require explicit approvals |

## Deployment guidance

- Never run public deployments in development mode.
- Configure a unique, high-entropy API key for each tenant/role entry in ORACLE_API_KEYS.
- Keep credentials in a secret manager; do not commit them to Git.
- Put the API behind TLS and a reverse proxy with request-size and rate limits.
- Restrict database network access and use non-default production credentials.
- Leave DeepSeek and OTLP export disabled unless approved and configured.
- Apply migrations before starting the API and maintain tested backups.
- Treat snapshots and audit exports as sensitive infrastructure data.

## Production release gate

A production-ready claim requires OIDC/SSO or equivalent enterprise identity integration, managed key lifecycle, database-level tenant constraints, tamper-evident audit retention, load and penetration tests, backup/restore drills, SBOM, signed releases, operational runbooks and independent security review. Update this document whenever the architecture or trust boundaries change.
