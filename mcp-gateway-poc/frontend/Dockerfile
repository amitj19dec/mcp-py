FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

ARG REACT_APP_API_URL=""
ARG REACT_APP_UI_TOKEN
ARG REACT_APP_ENABLE_DEBUG=false

ENV REACT_APP_API_URL=$REACT_APP_API_URL \
    REACT_APP_UI_TOKEN=$REACT_APP_UI_TOKEN \
    REACT_APP_ENABLE_DEBUG=$REACT_APP_ENABLE_DEBUG \
    GENERATE_SOURCEMAP=false

RUN npm run build

FROM nginx:alpine

# Install curl and create non-root user
RUN apk add --no-cache curl && \
    addgroup -g 1000 -S nginx-app && \
    adduser -u 1000 -D -S -G nginx-app nginx-app

# Copy nginx config and built assets
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/build /usr/share/nginx/html

# Fix permissions for non-root
RUN chown -R nginx-app:nginx-app /usr/share/nginx/html && \
    chown -R nginx-app:nginx-app /var/cache/nginx && \
    chown -R nginx-app:nginx-app /var/log/nginx && \
    chown -R nginx-app:nginx-app /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx-app:nginx-app /var/run/nginx.pid

USER nginx-app

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]