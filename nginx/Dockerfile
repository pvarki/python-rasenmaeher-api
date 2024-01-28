FROM nginx:1.25-alpine as production
COPY le_entrypoint.sh /
COPY crl_watcher.sh /usr/local/bin
RUN apk add --no-cache inotify-tools bash procps
ENTRYPOINT ["/le_entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
