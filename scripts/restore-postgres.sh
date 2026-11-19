#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <backup-file.dump>" >&2
  exit 2
fi

backup_file="$1"
checksum_file="${backup_file}.sha256"
database_name="${POSTGRES_DB:-oracle}"
database_user="${POSTGRES_USER:-oracle}"

if [[ ! -f "$backup_file" || ! -f "$checksum_file" ]]; then
  echo "Backup file or checksum file not found." >&2
  exit 1
fi

if [[ "${ORACLE_CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Restore replaces objects in database '$database_name'." >&2
  echo "Set ORACLE_CONFIRM_RESTORE=YES after reviewing the backup and target." >&2
  exit 1
fi

(
  cd "$(dirname "$backup_file")"
  sha256sum -c "$(basename "$checksum_file")"
)

echo "Stopping the API to prevent writes during recovery..."
docker compose stop api

if docker compose exec -T db pg_restore \
  --username="$database_user" \
  --dbname="$database_name" \
  --clean --if-exists --no-owner --no-privileges --exit-on-error < "$backup_file"; then
  echo "Restore completed. Starting the API..."
  docker compose start api
  echo "Recovery finished. Validate health, schema version and tenant data."
else
  echo "Restore failed. API remains stopped to avoid writes to a partial database." >&2
  exit 1
fi
