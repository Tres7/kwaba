# Debian 13 (trixie), like the server image
FROM node:24-trixie-slim AS base
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

FROM base AS deps
COPY package*.json ./
RUN npm ci --no-audit --no-fund

# Development (compose.yaml, target: dev): code mounted as a volume, hot reload
FROM deps AS dev
COPY . .
USER node
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM deps AS build
COPY . .
# Public values baked into the browser code at build time (one image per environment)
ARG NEXT_PUBLIC_API_URL=http://localhost/api
ARG NEXT_PUBLIC_SITE_URL=http://localhost
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID=""
ARG NEXT_PUBLIC_CONTACT_EMAIL=""
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL \
    NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID \
    NEXT_PUBLIC_CONTACT_EMAIL=$NEXT_PUBLIC_CONTACT_EMAIL
# Lint and types are checked by the CI before the image is built
RUN npx next build --no-lint

# Production: standalone Next.js server, without the full node_modules nor the source code
FROM base AS production
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0
# npm and corepack are only needed for the build: removed to reduce the attack surface (and their CVEs) at runtime
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack \
    /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack
COPY --from=build --chown=1000:1000 /app/.next/standalone ./
COPY --from=build --chown=1000:1000 /app/.next/static ./.next/static
COPY --from=build --chown=1000:1000 /app/public ./public
# The image's node user (uid 1000), never root
USER 1000:1000
EXPOSE 3000
CMD ["node", "server.js"]
