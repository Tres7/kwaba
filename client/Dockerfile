FROM node:24-trixie-slim AS base
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

FROM base AS deps
COPY package*.json ./
RUN npm ci --no-audit --no-fund

FROM deps AS dev
COPY . .
USER node
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM deps AS build
COPY . .
# Nothing specific to an environment is baked in: the site address, the Google client and the contact address are read
# when the container starts (env/client.env), so the same image goes to the preprod then to the production
RUN npx next build --no-lint

FROM base AS production
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack \
    /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack
COPY --from=build --chown=1000:1000 /app/.next/standalone ./
COPY --from=build --chown=1000:1000 /app/.next/static ./.next/static
COPY --from=build --chown=1000:1000 /app/public ./public
USER 1000:1000
EXPOSE 3000
CMD ["node", "server.js"]
