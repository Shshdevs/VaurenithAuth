#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
admin_host="${ADMIN_AUTH_HOSTNAME:-admin.auth.vaurenith.test}"
admin_port="${ADMIN_HTTPS_PORT:-8444}"
admin_url="https://$admin_host:$admin_port"
resolve=(--resolve "$admin_host:$admin_port:127.0.0.1")
ca=(--cacert .local/tls/rootCA.pem)
token="$(curl --silent --show-error --fail "${resolve[@]}" "${ca[@]}" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=password' \
  --data-urlencode 'client_id=admin-cli' \
  --data-urlencode 'username@.local/secrets/bootstrap_admin_username' \
  --data-urlencode 'password@.local/secrets/bootstrap_admin_password' \
  "$admin_url/realms/master/protocol/openid-connect/token" | \
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
current="$(curl --silent --show-error --fail "${resolve[@]}" "${ca[@]}" \
  -H "Authorization: Bearer $token" "$admin_url/admin/realms/master")"
updated="$(printf '%s' "$current" | python3 -c 'import json,sys; r=json.load(sys.stdin); a=r.get("attributes") or {}; a["frontendUrl"]=sys.argv[1]; r["attributes"]=a; print(json.dumps(r))' "$admin_url")"
curl --silent --show-error --fail "${resolve[@]}" "${ca[@]}" \
  -X PUT -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
  --data-binary "$updated" "$admin_url/admin/realms/master"
printf '%s\n' 'Master realm Frontend URL now uses the loopback admin endpoint.'
