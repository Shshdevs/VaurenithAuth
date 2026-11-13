#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir=".local/backups"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
umask 077
docker compose exec -T postgres sh -ec 'PGPASSWORD="$(cat "$POSTGRES_PASSWORD_FILE")" pg_dump --no-password --format=custom --host=127.0.0.1 --username="$POSTGRES_USER" "$POSTGRES_DB"' > "$backup_dir/vaurenith-auth-$timestamp.dump"
printf 'Created %s\n' "$backup_dir/vaurenith-auth-$timestamp.dump"
