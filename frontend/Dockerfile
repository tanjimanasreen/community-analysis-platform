# syntax=docker/dockerfile:1.7
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_API_TIMEOUT_MS=30000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_API_TIMEOUT_MS=${VITE_API_TIMEOUT_MS}
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=builder /app/dist /usr/share/nginx/html
ENV API_UPSTREAM=http://api:8000
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
