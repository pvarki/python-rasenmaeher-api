# syntax=docker/dockerfile:1.1.7-experimental
FROM python:3.11-alpine3.17 as production
COPY ./fakewerk.py /fakewerk.py
COPY ./docker-entrypoint.sh /docker-entrypoint.sh
WORKDIR /app
RUN --mount=type=ssh apk add --no-cache \
        bash \
        tini \
        openssl \
    && chmod a+x /docker-entrypoint.sh \
    && pip install libadvian multikeyjwt \
    # Do whatever else you need to
    && true
ENTRYPOINT ["/sbin/tini", "--", "/docker-entrypoint.sh"]
