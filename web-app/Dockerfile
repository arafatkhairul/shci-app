# ===== Stage 1: Build Stage =====
FROM node:20-alpine AS builder

# Working directory set kora
WORKDIR /app

# Package file gulo copy kora
COPY package*.json ./

# Dependency gulo install kora
RUN npm install

# Shompurno project code copy kora
COPY . .

# Production build toiri kora
RUN npm run build

# ===== Stage 2: Production Stage =====
FROM node:20-alpine

# Working directory set kora
WORKDIR /app

# Build stage theke shudhu matro proyojoniyo file gulo copy kora
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Port expose kora
EXPOSE 3000

# Production server chalate command deya
CMD ["npm", "start"]
