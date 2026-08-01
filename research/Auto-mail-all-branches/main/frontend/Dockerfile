# ── Stage 1: Build ───────────────────────────────────────────────────────────
# Uses Node to compile TypeScript + Vite → produces a static dist/ folder
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (cached layer — only re-runs if package.json changes)
COPY package*.json ./
RUN npm ci

# Copy all source code
COPY . .

# These build-time args bake the values INTO the JavaScript bundle at compile time.
# Vite replaces `import.meta.env.VITE_*` at build time — they are NOT secrets.
ARG VITE_API_BASE_URL=https://limitless-ai.in
ARG VITE_GOOGLE_CLIENT_ID

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

RUN npm run build

# ── Stage 2: Serve ───────────────────────────────────────────────────────────
# Nginx serves the compiled static files and proxies /api/* to the backend
FROM nginx:1.25-alpine

# Remove default nginx welcome page
RUN rm -rf /usr/share/nginx/html/*

# Copy the compiled React app from Stage 1
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy our custom nginx config (Now handled via docker-compose volume mount)

EXPOSE 80 443
