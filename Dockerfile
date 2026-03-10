FROM oven/bun:1.1-alpine AS base
WORKDIR /app

FROM base AS deps
COPY package.json bun.lockb* ./
RUN bun install --frozen-lockfile || bun install

FROM base AS runner
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN mkdir -p /app/data

ENV NODE_ENV=production
ENV PORT=3000
ENV DB_PATH=/app/data/arigato.db

EXPOSE 3000
CMD ["bun", "run", "src/index.ts"]
