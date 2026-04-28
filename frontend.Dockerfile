FROM node:20-alpine AS deps

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

FROM node:20-alpine AS builder

WORKDIR /app/frontend

COPY --from=deps /app/frontend/node_modules ./node_modules
COPY frontend ./

ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app/frontend

ENV NODE_ENV=production \
    PORT=8080

COPY --from=builder /app/frontend ./

EXPOSE 8080

CMD ["sh", "-c", "npm run start -- -p ${PORT}"]
