# Эксплуатация локального VaurenithAuth

## Локальный запуск

Нужны Docker Engine с Compose v2, `mkcert`, OpenSSL, curl и Make. Скопируйте `.env.example` в `.env` (это делает `make init`, если файл отсутствует), проверьте hostname/port/resource limits. Выполните `mkcert -install`, затем `make init`; скрипт создаёт секреты с правами владельца и сертификат с доверенным локальным CA. Не копируйте `.local` в Git, Docker build context или CI artifacts. Добавьте `127.0.0.1 auth.vaurenith.test` в hosts-файл, выполните `make up`.

Bootstrap admin создаётся Keycloak только при первоначальном старте пустой БД. После создания первого администратора удалите локальные bootstrap файлы `.local/secrets/bootstrap_admin_*`; храните аварийный административный доступ в менеджере секретов. При повторной инициализации существующие данные не перезаписываются. Локальные секреты не предназначены для production.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `AUTH_HOSTNAME` | Фиксированное имя issuer host для локального запуска: `auth.vaurenith.test` |
| `AUTH_HTTPS_PORT` | HTTPS host port, по умолчанию `8443`; привязка только к loopback |
| `POSTGRES_DB`, `POSTGRES_USER` | Имя отдельной Auth базы и роли |
| `KEYCLOAK_IMAGE`, `POSTGRES_IMAGE`, `CADDY_IMAGE` | Локальные/зафиксированные теги контейнеров |
| `KEYCLOAK_MEMORY_LIMIT`, `POSTGRES_MEMORY_LIMIT` | Ограничения памяти контейнеров |

Пароли и TLS private key передаются отдельными Compose secrets из `.local`, не через `.env`. Отсутствующие обязательные значения останавливают Compose interpolation или entrypoint. В production secrets должны поступать из secret manager/runtime secret mounts; локальный генератор использовать нельзя.

## Health и диагностика

`make health` обращается к HTTPS readiness endpoint; `make check` проверяет конфигурацию Compose, работающие сервисы, readiness, отказ admin URL и отсутствие публикации порта БД. Keycloak health и metrics слушают management port 9000 внутри контейнера и наружу не публикуются. Смотрите `make logs`, `docker compose ps` и `docker compose logs keycloak postgres proxy`. Логи не должны содержать credential values; не прикладывайте сырые логи к публичным issue.

Если hostname не разрешается — проверьте hosts-файл. Если браузер не доверяет TLS — повторите `mkcert -install` тем же локальным пользователем и проверьте системное хранилище CA. Если Compose сообщает об отсутствующем secret — повторите `make init`. Для проблем DB сначала проверьте health состояния PostgreSQL и Keycloak. Не удаляйте volume при диагностике.

## Backup и restore

`make backup` сохраняет custom-format dump в `.local/backups` с правами владельца. Защищайте резервные копии как пользовательские данные и шифруйте при переносе/внешнем хранении. Команда `make restore DUMP=.local/backups/file.dump` восстанавливает dump во временный контейнер PostgreSQL с `--network none`, отдельной случайной парой credentials и уничтожает его при завершении. Этот drill не затрагивает рабочий volume. Для production: согласуйте RPO/RTO, шифрование и срок хранения; регулярно проверяйте restore до допуска обновления.

## Обновление Keycloak

Сверьте upstream release notes, security advisories и CVE; закрепите новую версию и digest образа в `Containerfile`, прогоните CI, разверните копию базы, проверьте realm export/import и restore, затем выполните контролируемое обновление с сохранением volume. Снимите backup перед upgrade и подготовьте rollback план. Не понижайте версию на изменённой базе без поддерживаемой upstream процедуры. После обновления пересмотрите миграции, image vulnerabilities и release notes.

## Production boundary

Этот Compose предназначен для локального окружения одного разработчика. Он не задаёт production DNS, certificates/ACME, ingress ACL/WAF, external secret manager, HA/replicas, production admin VPN/network, backup encryption/retention, alerting, disaster recovery, capacity targets, SMTP, realm/client configuration или incident response. Production deployment требует отдельного reviewed overlay/platform design, частной admin plane, firewall/security group и операционного владельца. Не используйте `auth.vaurenith.local` как production issuer.
