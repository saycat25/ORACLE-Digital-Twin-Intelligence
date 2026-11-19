# ORACLE Operations Runbook

This runbook covers a local Docker Compose deployment. Adapt credentials, storage, monitoring and recovery targets before using a production environment.

## Configuration

1. Copy `.env.example` to `.env`.
2. Replace every development credential, especially `POSTGRES_PASSWORD` and every token in `ORACLE_API_KEYS`.
3. Set `ORACLE_ENV=production`, `AUDIT_HMAC_KEY` to at least 32 cryptographically random bytes, and one or more unique `ORACLE_API_KEYS` entries in the form `token|tenant-id|role`.
4. Keep `AI_DATA_SHARING_ENABLED=false` unless the organization has explicitly approved sharing simulation details with DeepSeek.
5. Leave `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` empty unless an approved Collector is available.
6. Restrict network exposure to the API and database. Do not publish the database port. Put the API behind TLS and a reverse proxy with request-size and rate limits.

The default PostgreSQL password in Compose is for local development only. Set a strong `POSTGRES_PASSWORD` in `.env` for any non-local environment. Do not commit `.env`.

## Start and migrate

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f api
```

The API container applies Alembic migrations before serving requests. Back up `AUDIT_HMAC_KEY` separately from the database: without the same key, existing HMAC signatures cannot be verified. Check `GET /health` and the migration version before sending writes. A legacy single-tenant database is assigned to tenant `default` by the first migration; review ownership before enabling real tenant credentials.

## Backup

Create a checksum-protected PostgreSQL custom-format backup:

```bash
bash scripts/backup-postgres.sh
```

The default output directory is `./backups`; set `BACKUP_DIR` to override it. Backup files are sensitive: protect access, encrypt them at rest and copy them to a separate durable storage system. The repository script does not configure off-site storage or retention. Back up the audit HMAC key separately from the database; without the same key, existing HMAC signatures cannot be validated.

## Restore

Restoring replaces database objects. First validate the target, the backup provenance and available recovery point. Then run:

```bash
ORACLE_CONFIRM_RESTORE=YES bash scripts/restore-postgres.sh ./backups/oracle-oracle-YYYYMMDDTHHMMSSZ.dump
```

The restore script verifies the adjacent SHA-256 file, stops the API to prevent concurrent writes, restores with `pg_restore --clean`, and starts the API only after a successful restore. On failure, the API remains stopped. After recovery, verify:

- API health and Alembic head revision.
- Expected tenant IDs, node/edge counts, telemetry and topology snapshot history.
- The audit integrity report at GET /api/v1/audit/verify; pre-HMAC legacy events will be shown as unverified.
- A sample simulation, capacity assessment and a read from each expected tenant.
- Database logs and application errors.

Perform periodic restore drills in an isolated environment. Define and test organization-specific RPO/RTO objectives; the existence of a backup file alone is not proof of recoverability.

## Release provenance and SBOM

Every CI backend run generates a CycloneDX JSON SBOM for the installed Python environment and publishes it as an Actions artifact.

Pushing a tag matching `v*` runs `.github/workflows/release.yml`: it builds Python wheel/source distributions, builds the web console, packages the SBOM and creates GitHub artifact attestations using Sigstore. The workflow then creates a GitHub Release with the artifacts. Check the Actions run and verify attestations before distributing release files.

## Remaining production work

This repository does not yet provide automated off-site backup storage, backup retention/rotation, database encryption-key management, restore SLO guarantees, OIDC/SSO, managed API-key provisioning/rotation, immutable audit storage, load/penetration testing or independent security certification. These remain release gates.
