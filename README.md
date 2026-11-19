# ORACLE — Digital Twin Intelligence

**Enterprise-oriented infrastructure digital twin for dependency modeling, controlled failure simulation, and explainable impact analysis.**

> Status: active development. This repository is not yet certified or represented as production-ready. Review the implementation status and security notes before deployment.

## What it does

ORACLE models infrastructure as a directed dependency graph. Nodes represent services or infrastructure components; edges represent consumer-to-dependency relationships. The current engine traverses reverse dependencies from a failed component and calculates deterministic, criticality-weighted impact scores.

## Current implementation

- FastAPI REST API for infrastructure nodes, dependency edges, topology snapshots, and simulations.
- Basic telemetry sample ingestion and querying by component and metric.
- Tenant-scoped audit events with per-event HMAC-SHA256 integrity checks, JSON export and admin access controls.
- Admin-protected Prometheus-compatible HTTP request metrics and optional OpenTelemetry traces with OTLP export.
- Tenant-scoped JSON audit export restricted to administrators, plus HMAC-SHA256 event-integrity verification.
- Automatic, tenant-scoped topology history snapshots on every component/dependency change.
- Deterministic capacity projections using operator-declared component capacity and current load, with warning and overload thresholds.
- Deterministic comparison of two failure scenarios, including newly impacted/shared nodes and score deltas.
- Optional DeepSeek explanations for saved simulations, protected by an explicit server-side data-sharing opt-in.
- Scenario comparison and AI explanation endpoints documented automatically through FastAPI OpenAPI.
- Operational console for creating components/dependencies, visualizing the live graph and historical topology versions, comparing failure scenarios, reviewing telemetry/audit and exporting audit data.
- SQLAlchemy persistence with SQLite by default and PostgreSQL support.
- Deterministic, explainable dependency-impact engine.
- React + TypeScript operational console.
- Docker Compose development environment.
- Pytest, Ruff, pip-audit, CodeQL and CycloneDX SBOM generation in CI.
- Tag-based release workflow with Python/frontend packages and GitHub/Sigstore provenance attestations.
- PostgreSQL backup/restore scripts with checksum verification and an operations runbook.
- Portuguese and English documentation.

## Limits and next phases

Tenant-isolated infrastructure records, role-based API authorization, telemetry ingestion and the audit trail are implemented at a baseline level. `AUDIT_HMAC_KEY` must be at least 32 random bytes in production and signs audit events with HMAC-SHA256. `ORACLE_API_KEYS` configures tenant-bound API credentials and RBAC roles (`viewer`, `operator`, `ingestor`, `admin`). In production, valid credentials are mandatory and the tenant comes from the matching credential, not from a user-selected tenant header. Development mode allows an unauthenticated local admin only when the API-key registry is empty. DeepSeek assistance requires `DEEPSEEK_API_KEY` and `AI_DATA_SHARING_ENABLED=true`; outbound sharing is disabled by default. `X-Tenant-ID` is an optional consistency check; with configured keys, the credential determines the tenant.

OIDC/SSO and managed key lifecycle, external immutable audit archive and retention policies, alerting/SLOs, richer business-level traces, historical topology replay/diff, capacity-aware failover routing and richer administration, production backup/restore drills and off-site retention, load and penetration testing, and independent security review remain open work. The release workflow can generate signed provenance attestations when a version tag is published; no release artifact is attested until that workflow runs. See the [roadmap](docs/ROADMAP.md) for the verified scope.

## Quick start

Requires Python 3.11+.

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn oracle_api.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Docker

```bash
docker compose up --build
```

## Run tests

```bash
cd backend
pytest
ruff check .
```

## Safety

The current simulator performs graph calculations only; it does not execute changes against infrastructure. Use synthetic topology data. Baseline API-key authentication, role-based authorization, tenant scoping and per-event audit HMAC checks are implemented, but they are not a production certification. Do not connect this development release to production systems without independent security review, OIDC/SSO or equivalent identity integration, managed key lifecycle, tamper-evident audit retention, backup/restore procedures, and operational/load testing.

## Documentation

- [Português (Brasil)](README.pt-BR.md)
- [Security policy](SECURITY.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Operations runbook](docs/OPERATIONS.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Attribution and license](LICENSE) and [NOTICE](NOTICE)

## License and attribution

ORACLE Attribution License (OAL) 1.0. Free use, modification, and redistribution are permitted, including commercial use, provided that the original copyright/license notice is retained and a prominent attribution with a link to the original repository is included:

**Original project:** https://github.com/saycat25/ORACLE-Digital-Twin-Intelligence

This is a custom attribution license, not MIT/Apache-2.0 and not OSI-approved open-source licensing. See [LICENSE](LICENSE) for the full terms. Third-party dependencies retain their own licenses.
