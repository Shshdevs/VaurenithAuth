#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
if [[ $# -ne 1 || ! -f "$1" ]]; then printf '%s\n' 'Usage: scripts/restore-test.sh PATH_TO_CUSTOM_FORMAT_DUMP' >&2; exit 2; fi
image="$(docker compose config --images | sed -n '1p')"
container="vaurenith-auth-restore-test-$$"
password="$(openssl rand -hex 32)"
cleanup() { docker rm -f "$container" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker run --detach --name "$container" --network none --env POSTGRES_PASSWORD="$password" --env POSTGRES_DB=restore_validation --health-cmd='pg_isready -U postgres -d restore_validation' --health-interval=2s --health-timeout=2s --health-retries=30 "$image" >/dev/null
for _ in $(seq 1 60); do
  state="$(docker inspect --format '{{.State.Health.Status}}' "$container")"
  [[ "$state" == healthy ]] && break
  sleep 1
done
[[ "$(docker inspect --format '{{.State.Health.Status}}' "$container")" == healthy ]]
docker cp "$1" "$container:/tmp/restore.dump"
docker exec --env PGPASSWORD="$password" "$container" pg_restore --no-password --exit-on-error --host=127.0.0.1 --username=postgres --dbname=restore_validation /tmp/restore.dump
docker exec --env PGPASSWORD="$password" "$container" psql --no-password --tuples-only --no-align --host=127.0.0.1 --username=postgres --dbname=restore_validation --command="SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema');"
printf '%s\n' 'Restore completed in a disposable, network-isolated PostgreSQL container.'
