# ─────────────────────────────────────────────────────────────────────────────
# PaperLens Frontend — Multi-stage Docker build
#
# Stage 1 (builder): installs ALL deps (including devDeps), runs next build
# Stage 2 (runner):  copies only the standalone output — lean production image
#
# Requires: package-lock.json (committed to repo)
# Uses:     npm ci  — fast, reproducible, exact-version install from lockfile
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Build ───────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependency manifests first (cached layer unless deps change)
COPY package.json package-lock.json ./

# npm ci: reads the lockfile exactly — no version drift, no network guessing.
# This is why package-lock.json must be committed to the repository.
RUN npm ci

# Copy source code
COPY . .

# Build-time environment (public vars only — never put secrets here)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Produce the standalone Next.js output
RUN npm run build

# ── Stage 2: Production image ─────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
# Disable Next.js telemetry in Docker
ENV NEXT_TELEMETRY_DISABLED=1

# Unprivileged user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy only the standalone server and static assets from the builder stage.
# Note: the `public/` directory may be empty for this project (no static assets
# yet), but the COPY is kept so future files (favicon, robots.txt, etc.) are
# included automatically without changing the Dockerfile.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

# The standalone build generates server.js at the root of the output directory
CMD ["node", "server.js"]
