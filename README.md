# ORACLE — Digital Twin Intelligence

Enterprise-oriented digital twin platform for modeling software infrastructure, simulating controlled failures, and analyzing dependency impact.

The first foundation release provides a typed infrastructure model, deterministic dependency-impact simulation, a FastAPI service, SQLAlchemy persistence, automated tests, Docker setup, and a React dashboard starter.

See [README.pt-BR.md](README.pt-BR.md) for the Portuguese documentation.

## Status

This is an early development foundation, not a production-ready deployment. Authentication, authorization, tenant isolation, audit controls, telemetry ingestion, and production hardening remain on the roadmap.

## Quick start

```bash
cd backend
python -m venv .venv
pip install -e ".[dev]"
uvicorn oracle_api.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

## Docker

```bash
docker compose up --build
```

## Safety

Simulations are read-only graph calculations. Do not connect this initial release to production infrastructure. Use synthetic topology data until security controls have been reviewed.

## License

MIT. See [LICENSE](LICENSE).
