#!/usr/bin/env bash
set -euo pipefail
export KC_DB_PASSWORD="$(cat /run/secrets/postgres_password)"
if [[ -r /run/secrets/bootstrap_admin_username && -r /run/secrets/bootstrap_admin_password ]]; then
  export KC_BOOTSTRAP_ADMIN_USERNAME="$(cat /run/secrets/bootstrap_admin_username)"
  export KC_BOOTSTRAP_ADMIN_PASSWORD="$(cat /run/secrets/bootstrap_admin_password)"
fi
exec /opt/keycloak/bin/kc.sh "$@"
