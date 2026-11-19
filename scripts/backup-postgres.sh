#!/usr/bin/env bash
set -Eeuo pipefail

backup_dir="${BACKUP_DIR:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
database_name="${POSTGRES_DB:-oracle}"
database_user="${POSTGRES_USER:-oracle}"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"

backup_file="$backup_dir/oracle-${database_name}-${timestamp}.dump"
checksum_file="${backup_file}.sha256"
temporary_file="${backup_file}.partial"

cleanup() {
  rm -f "$temporary_file"
}
trap cleanup EXIT

echo "Creating PostgreSQL custom-format backup..."
docker compose exec -T db pg_dump -U "$database_user" -d "$database_name" -Fc > "$temporary_file"
test -s "$temporary_file"
mv "$temporary_file" "$backup_file"
(
  cd "$backup_dir"
  sha256sum "$(basename "$backup_file")" > "$(basename "$checksum_file")"
)
chmod 600 "$backup_file" "$checksum_file"

echo "Backup created: $backup_file"
echo "Checksum: $checksum_file"
