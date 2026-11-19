# Contributing

Thanks for helping improve ORACLE.

## Development rules

- Python 3.11+.
- Keep domain logic independent from HTTP and persistence layers.
- Add or update tests for every behavior change.
- Use type hints and clear, domain-oriented names.
- Never commit credentials, production topology exports, or personal data.
- Keep simulations non-destructive by default.

## Local checks

```bash
cd backend
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
```

## Pull requests

Explain the problem, design decision, security impact, test evidence, and documentation changes. Mark unfinished work explicitly.
