# Changelog

All notable ORACLE changes are documented here. This project is under active development; entries describe repository capabilities, not a production-readiness certification.

## 0.4.0 — Development milestone

### Added
- Tenant-bound API keys with viewer, operator, ingestor and admin roles.
- Tenant filtering for nodes, dependencies, simulations, telemetry, audit records and topology snapshots.
- Alembic schema migrations for tenant ownership, topology history and component capacity.
- Automatic, tenant-scoped topology snapshots on component/dependency creation.
- Historical topology snapshot listing and read-only graph inspection.
- Side-by-side scenario comparison with impacted-node sets and score deltas.
- Capacity projection from operator-declared capacity/current load and configurable demand multiplier.
- Basic telemetry ingestion/query, audit trail, admin-only audit JSON export.
- Prometheus-compatible HTTP metrics and optional OpenTelemetry OTLP/HTTP spans.
- Optional DeepSeek simulation explanation with explicit outbound-data opt-in.
- React console workflows for topology editing, graph visualization, simulations, snapshots, capacity, telemetry and audit.
- CycloneDX backend SBOM, CodeQL workflows, release build-provenance workflow and PostgreSQL backup/restore scripts.
- Portuguese and English documentation, threat model and operations runbook.

### Security and limitations
- Production startup requires ORACLE_API_KEYS; development mode without keys remains a local convenience only.
- The custom OAL 1.0 attribution license is not OSI-approved.
- OIDC/SSO, managed API-key lifecycle, tamper-evident audit retention, alerts/SLOs, capacity-aware failover routing, load/penetration testing, off-site backup retention, restore drills and independent security review remain incomplete.
- No v0.4.0 release has been published by this changelog entry alone. Release artifacts and Sigstore attestations are created only after a matching version tag triggers the release workflow.
