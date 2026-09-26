# Felo v2 runtime: Node 20 + the exact libraries v2 was running with on
# 2026-09-24 (copied out of the running container). The app code itself is
# not in the image; it is mounted read-only from /root/felo-codex-preview/app.
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json ./
COPY node_modules ./node_modules
WORKDIR /repair
CMD ["node", "/repair/preview.js"]
