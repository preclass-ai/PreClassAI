# Build from the repository root (pnpm workspace): docker build -f apps/web/Dockerfile -t preclass-web .
FROM node:22-alpine AS build
WORKDIR /repo
RUN corepack enable && corepack prepare pnpm@10 --activate
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/
COPY packages/api-client/package.json packages/api-client/
RUN pnpm install --frozen-lockfile
COPY packages/api-client packages/api-client
COPY apps/web apps/web
ENV NEXT_TELEMETRY_DISABLED=1
# next.config requires a public API_ORIGIN for production builds; here Caddy routes /v1 so the rewrite is unused.
ENV API_ORIGIN=https://api.example.com
RUN pnpm --filter @preclass/web build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup -S app && adduser -S app -G app
COPY --from=build --chown=app:app /repo/apps/web/.next/standalone ./
COPY --from=build --chown=app:app /repo/apps/web/.next/static ./apps/web/.next/static
USER app
EXPOSE 3000
# /v1/* never reaches this container in staging/prod: Caddy routes it to the API first.
CMD ["node", "apps/web/server.js"]
