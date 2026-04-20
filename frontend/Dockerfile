FROM nginx:alpine

# Copy frontend files to nginx
COPY frontend/index.html /usr/share/nginx/html/

# Copy nginx configuration
COPY frontend/nginx.conf /etc/nginx/nginx.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
