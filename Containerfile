ARG KEYCLOAK_BASE=quay.io/keycloak/keycloak:26.8.2-3@sha256:7e66a96e4739239070aeaf72e4c5decf0f7f682cfc725b9f7ea2b336eaba38b3
FROM ${KEYCLOAK_BASE} AS builder
ENV KC_DB=postgres KC_HEALTH_ENABLED=true KC_METRICS_ENABLED=true KC_HTTP_RELATIVE_PATH=/
WORKDIR /opt/keycloak
RUN /opt/keycloak/bin/kc.sh build

FROM ${KEYCLOAK_BASE}
COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY --chown=keycloak:keycloak config/realm/vaurenith-realm.json /opt/keycloak/data/import/vaurenith-realm.json
COPY --chown=keycloak:keycloak themes/vaurenith/ /opt/keycloak/themes/vaurenith/
ENV KC_DB=postgres KC_HEALTH_ENABLED=true KC_METRICS_ENABLED=true KC_HTTP_ENABLED=true KC_PROXY_HEADERS=xforwarded KC_HOSTNAME_STRICT=true
EXPOSE 8080 9000
COPY --chmod=0555 container-entrypoint.sh /opt/keycloak/bin/container-entrypoint.sh
ENTRYPOINT ["/opt/keycloak/bin/container-entrypoint.sh"]
CMD ["start", "--optimized"]
