FROM python:3.9.10-alpine3.15

WORKDIR /app

RUN apk add --no-cache curl && \
    apk add netcat-openbsd

COPY *.sh ./

RUN chmod 755 /app/*.sh

CMD ["/app/entrypoint.sh"]