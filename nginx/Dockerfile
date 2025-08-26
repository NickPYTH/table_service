FROM nginx_test_auth

COPY default.conf /etc/nginx/conf.d/default.conf
COPY example.keytab /etc/example.keytab
RUN mkdir -p /etc/nginx/html
COPY build /etc/nginx/html
