# Эксплуатация локального VaurenithAuth

## Локальный запуск

Нужны Docker Engine с Compose v2, `mkcert`, OpenSSL, curl и Make. Скопируйте `.env.example` в `.env` (это делает `make init`, если файл отсутствует), проверьте hostname/port/resource limits. Выполните `mkcert -install`, затем `make init`; скрипт создаёт секреты с правами владельца и сертификат с доверенным локальным CA. Не копируйте `.local` в Git, Docker build context или CI artifacts. Добавьте `127.0.0.1 auth.vaurenith.test admin.auth.vaurenith.test` в hosts-файл и выполните `make up`.

Bootstrap admin создаётся Keycloak только при первоначальном старте пустой БД. После готовности Keycloak выполните `make configure-admin-realm`, пока файлы `.local/secrets/bootstrap_admin_*` доступны скрипту, затем удалите эти файлы и храните аварийный административный доступ в менеджере секретов. При повторной инициализации существующие данные не перезаписываются. Локальные секреты не предназначены для production.

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

## Realm и аутентификация AUTH-003

Основной issuer: `https://auth.vaurenith.test:8443/realms/vaurenith`. Realm импортируется при старте из `config/realm/vaurenith-realm.json`; если realm уже существует, Keycloak пропускает импорт и не перезаписывает состояние. Изменения декларативной конфигурации существующего realm требуют отдельной контролируемой процедуры миграции через Admin API/Console, backup и review diff. `--import-realm` не является механизмом обновления. Не используйте `--override` во время работающего сервера и не удаляйте volume/realm для применения конфигурации.

Локальный admin UI/API доступен по `https://admin.auth.vaurenith.test:8444` и опубликован только на loopback. На основном endpoint Caddy отклоняет `/admin/*` и все `/realms/master/*`. После первоначального запуска выполните `make configure-admin-realm`: команда задаёт master realm Frontend URL на loopback admin endpoint, чтобы браузерная авторизация и iframe проверки Admin Console не уходили на основной hostname. Это явная административная настройка, она не переустанавливается автоматически при старте. Mailpit принимает SMTP только во внутренней Compose сети; его UI опубликован на `127.0.0.1:8025`. Добавьте оба hostname в hosts-файл, затем выполните `make init`, `make up`, `make configure-admin-realm`, `make check`. Регистрационные письма для локальной проверки смотрите в Mailpit UI. Без SMTP в production email verification и password reset не завершены.

Клиенты содержат только тестовые redirect URI: Web `http://localhost:5173/auth/callback`; Desktop `http://127.0.0.1:49152/oauth/callback`. Это не интеграция приложений. Не расширяйте allowlist до wildcard. SPA хранение токенов остаётся риском; предпочтителен BFF. Desktop токены должны храниться в OS credential storage.

Отдельный локальный hostname сам по себе не является production защитой admin surface: production требует сетевого ACL/VPN/private ingress и ограниченного доступа к Admin API, отдельного контроля операторов, MFA и аудита.

## Интеграция access token с VaurenithBackend

Для локального realm issuer должен быть `https://auth.vaurenith.test:8443/realms/vaurenith`, audience Backend — `vaurenith-backend`. Эти значения должны совпадать с `AUTH_JWT_ISSUER` и `AUTH_JWT_AUDIENCE` в `.env` Backend. Клиенты получают RS256 access tokens с `typ=at+jwt`, UUID `sub`, email, `auth_provider=local`, audience Backend и своим `client_id`.

Verifier Backend согласован с Keycloak: `jti` принимается как непустая строка до 255 символов, а `nbf` необязателен и проверяется, если присутствует. Это сохраняет уникальный Keycloak token ID и не добавляет фиктивное значение `nbf`.

После изменения realm-файла существующая база не обновится автоматически. Выполните `make up`, затем `make configure-backend-token-contract` и введите логин и пароль постоянного master-администратора. Команда применяет Login Theme, обязательный для пользователя атрибут профиля `display_name`, скрывает `firstName` и `lastName` из пользовательского контекста и применяет Backend client scope с protocol mappers через Admin API. Для нового пустого realm тема и client scope также находятся в `config/realm/vaurenith-realm.json`. Тема хранится в `themes/vaurenith/login`; имя устройства остаётся данными Client и не добавляется в профиль пользователя Keycloak.

Экспортируйте текущий RS256 verify key командой `make export-backend-key`. Скопируйте `.local/backend/jwt-public.pem` в Backend как `.local/keys/jwt-public.pem`. В `.env` Backend задайте `AUTH_JWT_ISSUER=https://auth.vaurenith.test:8443/realms/vaurenith`, `AUTH_JWT_AUDIENCE=vaurenith-backend` и `AUTH_JWT_PUBLIC_KEY_PATH=.local/keys/jwt-public.pem`. После смены активного signing key повторите экспорт, обновите PEM Backend и перезапустите его; автоматическое обновление через JWKS не настроено.

Сквозной тест должен получить новый access token по Authorization Code + PKCE и проверить его на `/api/v1/users/create` с email, совпадающим с verified email claim. Этот endpoint требует валидный RS256 Bearer token и создаёт Backend-профиль, устройство и сессию для UUID из `sub`; он не регистрирует пользователя в Keycloak.
