.PHONY: init up down logs status health backup restore check configure-admin-realm configure-backend-token-contract export-backend-key

init:
	./scripts/init-local.sh

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

status:
	docker compose ps

health:
	curl --fail --silent --show-error --cacert .local/tls/rootCA.pem https://$${AUTH_HOSTNAME:-auth.vaurenith.test}:$${AUTH_HTTPS_PORT:-8443}/health/ready

backup:
	./scripts/backup.sh

restore:
	./scripts/restore-test.sh $(DUMP)

check:
	./scripts/check-local.sh

configure-admin-realm:
	./scripts/configure-admin-realm.sh

configure-backend-token-contract:
	python3 scripts/configure-backend-token-contract.py

export-backend-key:
	python3 scripts/export-backend-public-key.py
