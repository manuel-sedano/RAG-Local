# stable-alpine: canal estable con parches de nginx; apk upgrade aplica CVE de paquetes Alpine en build.
FROM nginx:stable-alpine
RUN apk upgrade --no-cache \
    && rm -rf /var/cache/apk/*
COPY nginx.conf /etc/nginx/conf.d/default.conf
