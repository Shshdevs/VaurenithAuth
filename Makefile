.PHONY: init up down logs status health backup restore check

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
	curl --fail --silent --show-error https://$${AUTH_HOSTNAME:-auth.vaurenith.test}:$${AUTH_HTTPS_PORT:-8443}/health/ready

backup:
	./scripts/backup.sh

restore:
	./scripts/restore-test.sh $(DUMP)

check:
	./scripts/check-local.sh
