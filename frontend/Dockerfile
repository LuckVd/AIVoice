FROM nginx:alpine

# Copy custom nginx configuration
COPY ./frontend/nginx.conf /etc/nginx/nginx.conf

# Create storage directories
RUN mkdir -p /usr/share/nginx/html/storage/audio /usr/share/nginx/html/storage/uploads /usr/share/nginx/html/storage/temp

# Copy the HTML frontend file
COPY ./storage/*.html /usr/share/nginx/html/

# Copy storage content
COPY ./storage/audio/ /usr/share/nginx/html/storage/audio/
COPY ./storage/uploads/ /usr/share/nginx/html/storage/uploads/
COPY ./storage/temp/ /usr/share/nginx/html/storage/temp/

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]