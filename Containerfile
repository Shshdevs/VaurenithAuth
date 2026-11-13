ARG KEYCLOAK_BASE=quay.io/keycloak/keycloak:26.8.2@sha256:3879c623248408de29a5303178b5816c77e8dfef3890c361f8c0bbeaa979ba3b
FROM ${KEYCLOAK_BASE} AS builder
ENV KC_DB=postgres KC_HEALTH_ENABLED=true KC_METRICS_ENABLED=true KC_HTTP_RELATIVE_PATH=/
WORKDIR /opt/keycloak
RUN /opt/keycloak/bin/kc.sh build

FROM ${KEYCLOAK_BASE}
COPY --from=builder /opt/keycloak/ /opt/keycloak/
ENV KC_DB=postgres KC_HEALTH_ENABLED=true KC_METRICS_ENABLED=true KC_HTTP_ENABLED=true KC_PROXY_HEADERS=xforwarded KC_HOSTNAME_STRICT=true KC_HOSTNAME_STRICT_HTTPS=true
EXPOSE 8080 9000
COPY --chmod=0555 container-entrypoint.sh /opt/keycloak/bin/container-entrypoint.sh
ENTRYPOINT ["/opt/keycloak/bin/container-entrypoint.sh"]
CMD ["start", "--optimized"]
