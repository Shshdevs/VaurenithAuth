#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
if [[ ! -f .env ]]; then cp .env.example .env; fi
command -v mkcert >/dev/null 2>&1 || { printf '%s\n' 'Install mkcert and run mkcert -install first.' >&2; exit 1; }
mkdir -p .local/secrets .local/tls
chmod 700 .local .local/secrets .local/tls
create_secret() {
  local path="$1"
  if [[ ! -s "$path" ]]; then openssl rand -base64 48 | tr -d '\n' > "$path"; chmod 600 "$path"; fi
}
create_secret .local/secrets/postgres_password
create_secret .local/secrets/bootstrap_admin_password
if [[ ! -s .local/secrets/bootstrap_admin_username ]]; then openssl rand -hex 12 > .local/secrets/bootstrap_admin_username; chmod 600 .local/secrets/bootstrap_admin_username; fi
if [[ ! -s .local/tls/auth.crt || ! -s .local/tls/auth.key ]]; then mkcert -cert-file .local/tls/auth.crt -key-file .local/tls/auth.key auth.vaurenith.test; chmod 644 .local/tls/auth.crt; chmod 600 .local/tls/auth.key; fi
cp "$(mkcert -CAROOT)/rootCA.pem" .local/tls/rootCA.pem
chmod 644 .local/tls/rootCA.pem
printf '%s\n' 'Local secrets and trusted certificate are ready.' 'Add 127.0.0.1 auth.vaurenith.test to your hosts file, then run: make up'
