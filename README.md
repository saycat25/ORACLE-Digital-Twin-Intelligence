# ORACLE — Digital Twin Intelligence

**Enterprise-oriented infrastructure digital twin for dependency modeling, controlled failure simulation, and explainable impact analysis.**

> Status: active development. This repository is not yet certified or represented as production-ready. Review the implementation status and security notes before deployment.

## What it does

ORACLE models infrastructure as a directed dependency graph. Nodes represent services or infrastructure components; edges represent consumer-to-dependency relationships. The current engine traverses reverse dependencies from a failed component and calculates deterministic, criticality-weighted impact scores.

## Current implementation

- FastAPI REST API for infrastructure nodes, dependency edges, topology snapshots, and simulations.
- Basic telemetry sample ingestion and querying by component and metric.
- Basic audit events for component/dependency creation, simulations, and telemetry ingestion.
- Deterministic comparison of two failure scenarios, including newly impacted/shared nodes and score deltas.
- Operational console for creating components/dependencies and running failure simulations.
- SQLAlchemy persistence with SQLite by default and PostgreSQL support.
- Deterministic, explainable dependency-impact engine.
- React + TypeScript console starter.
- Docker Compose development environment.
- Pytest and Ruff CI workflow.
- Portuguese and English documentation.

## Limits and next phases

Telemetry ingestion and the audit trail are implemented at a basic level. When configured, `INGESTION_API_KEY` requires an `X-API-Key` header for telemetry writes. `X-Tenant-ID` currently labels audit and telemetry records only; it does **not** isolate infrastructure nodes, dependency edges, or simulations, and is not an authentication mechanism.

OIDC/SSO, RBAC, true tenant isolation, audit retention/export and tamper protection, OpenTelemetry export, alerting, temporal topology and capacity models, optional DeepSeek integration, full console workflows, load/security testing, SBOM, signed releases, and backup recovery remain open work. See the [roadmap](docs/ROADMAP.md) for the verified scope.

## Quick start

Requires Python 3.11+.

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
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

The current simulator performs graph calculations only; it does not execute changes against infrastructure. Use synthetic topology data. Do not connect this development release to production systems without a security review, authentication/authorization controls, tenant isolation, backup/restore procedures, and operational testing.

## Documentation

- [Português (Brasil)](README.pt-BR.md)
- [Security policy](SECURITY.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Contributing](CONTRIBUTING.md)
- [Attribution and license](LICENSE) and [NOTICE](NOTICE)

## License and attribution

ORACLE Attribution License (OAL) 1.0. Free use, modification, and redistribution are permitted, including commercial use, provided that the original copyright/license notice is retained and a prominent attribution with a link to the original repository is included:

**Original project:** https://github.com/saycat25/ORACLE-Digital-Twin-Intelligence

This is a custom attribution license, not MIT/Apache-2.0 and not OSI-approved open-source licensing. See [LICENSE](LICENSE) for the full terms. Third-party dependencies retain their own licenses.
