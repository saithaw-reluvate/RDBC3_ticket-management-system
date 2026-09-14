# Build context is frontend/ (docker-compose.prod.yml). Multi-stage so the
# runtime image carries only the standalone server output, not the full
# node_modules tree or build toolchain.

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# next.config.mjs's rewrites() destination is resolved once at `next build`
# time and baked into the standalone output's routes manifest — it is NOT
# re-read from process.env at container start. Server Components that read
# process.env.BACKEND_ORIGIN directly (lib/api.ts) still pick up the runtime
# value set in docker-compose.prod.yml; only the rewrite needs this build ARG.
ARG BACKEND_ORIGIN=http://backend:8000
ENV BACKEND_ORIGIN=$BACKEND_ORIGIN
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# No public/ directory exists in this project — nothing to copy for it.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
