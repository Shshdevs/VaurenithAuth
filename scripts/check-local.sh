#!/usr/bin/env bash
set -euo pipefail
docker compose config --quiet
docker compose ps --status running
host="${AUTH_HOSTNAME:-auth.vaurenith.test}"
port="${AUTH_HTTPS_PORT:-8443}"
curl --fail --silent --show-error --cacert .local/tls/rootCA.pem "https://$host:$port/health/ready"
printf '\n'
status="$(curl --silent --output /dev/null --write-out '%{http_code}' --cacert .local/tls/rootCA.pem "https://$host:$port/admin/")"
[[ "$status" == 404 ]]
[[ -z "$(docker compose port postgres 5432 2>/dev/null || true)" ]]
printf '%s\n' 'Readiness, admin path, and database publication checks passed.'
