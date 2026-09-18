# ==============================================================================
# Build Stage: Compile React + TypeScript with Vite
# ==============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies with package caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

# Inject API base URL at build time (Vite bakes env vars into the bundle)
ARG VITE_API_BASE_URL=https://testarea.ddns.net
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Build production bundle
RUN npm run build

# ==============================================================================
# Production Stage: Serve static build via Nginx with API reverse proxy
# ==============================================================================
FROM nginx:alpine

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
