FROM haproxy:2.9-alpine as production
USER root
COPY le_entrypoint.sh /usr/local/bin
COPY crl_watcher.sh /usr/local/bin
RUN apk add --no-cache inotify-tools bash procps
USER haproxy
ENTRYPOINT ["le_entrypoint.sh"]
CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]
