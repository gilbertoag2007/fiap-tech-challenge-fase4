FROM nginx:stable-alpine
COPY analise-medica-frontend/ /usr/share/nginx/html/
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
# Change the origin only inside the image, preserving direct local execution.
RUN sed -i 's|"http://127.0.0.1:8000"|window.location.origin|' /usr/share/nginx/html/assets/js/config.js
EXPOSE 80
