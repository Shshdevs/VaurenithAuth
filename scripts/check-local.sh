#!/usr/bin/env bash
set -euo pipefail
docker compose config --quiet
docker compose ps --status running
host="${AUTH_HOSTNAME:-auth.vaurenith.test}"
port="${AUTH_HTTPS_PORT:-8443}"
ready=false
for attempt in $(seq 1 90); do
  if curl --fail --silent --cacert .local/tls/rootCA.pem "https://$host:$port/health/ready" >/dev/null; then ready=true; break; fi
  sleep 2
done
[[ "$ready" == true ]]
curl --fail --silent --show-error --cacert .local/tls/rootCA.pem "https://$host:$port/health/ready"
printf '\n'
openssl x509 -in .local/tls/auth.crt -noout -ext subjectAltName | grep -q 'DNS:auth.vaurenith.test'
openssl x509 -in .local/tls/auth.crt -noout -ext subjectAltName | grep -q 'DNS:admin.auth.vaurenith.test'
admin_host="${ADMIN_AUTH_HOSTNAME:-admin.auth.vaurenith.test}"
admin_port="${ADMIN_HTTPS_PORT:-8444}"
admin_status="$(curl --silent --output /dev/null --write-out '%{http_code}' --resolve "$admin_host:$admin_port:127.0.0.1" --cacert .local/tls/rootCA.pem "https://$admin_host:$admin_port/admin/master/console/")"
[[ "$admin_status" == 200 || "$admin_status" == 302 ]]
admin_redirect="$(curl --silent --output /dev/null --write-out '%{redirect_url}' --resolve "$admin_host:$admin_port:127.0.0.1" --cacert .local/tls/rootCA.pem "https://$admin_host:$admin_port/admin/master/console")"
[[ "$admin_redirect" == "https://$admin_host:$admin_port/admin/master/console/" ]]
admin_api_status="$(curl --silent --output /dev/null --write-out '%{http_code}' --resolve "$admin_host:$admin_port:127.0.0.1" --cacert .local/tls/rootCA.pem "https://$admin_host:$admin_port/admin/serverinfo")"
[[ "$admin_api_status" == 401 ]]
for path in /admin/ /admin/realms/master /realms/master/ /realms/master/protocol/openid-connect/auth /realms/master/.well-known/openid-configuration; do
  status="$(curl --silent --output /dev/null --write-out '%{http_code}' --cacert .local/tls/rootCA.pem "https://$host:$port$path")"
  [[ "$status" == 404 ]]
done
for path in '/%61dmin/serverinfo' '/admin%2fserverinfo' '//admin/serverinfo' '/realms/%6daster/protocol/openid-connect/auth' '/realms/master%2fprotocol/openid-connect/auth' '/realms//master/protocol/openid-connect/auth'; do
  status="$(curl --silent --path-as-is --output /dev/null --write-out '%{http_code}' --cacert .local/tls/rootCA.pem "https://$host:$port$path")"
  [[ "$status" == 404 ]]
done
python3 scripts/check-realm.py
postgres_id="$(docker compose ps -q postgres)"

[[ -n "$postgres_id" ]]

published_ports="$(docker inspect \
  --format '{{json .HostConfig.PortBindings}}' \
  "$postgres_id")"

[[ "$published_ports" == "null" || "$published_ports" == "{}" ]]
proxy_id="$(docker compose ps -q proxy)"
proxy_bindings="$(docker inspect --format '{{json .HostConfig.PortBindings}}' "$proxy_id")"
[[ "$proxy_bindings" == *'127.0.0.1'* ]]
printf '%s\n' 'Readiness, realm, admin route, and publication checks passed.'
