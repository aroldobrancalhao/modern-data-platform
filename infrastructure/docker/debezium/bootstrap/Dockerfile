FROM alpine:3.22

RUN apk add --no-cache \
    bash \
    curl \
    jq

COPY debezium/bootstrap/register-connectors.sh /register-connectors.sh

RUN chmod +x /register-connectors.sh

ENTRYPOINT ["/register-connectors.sh"]