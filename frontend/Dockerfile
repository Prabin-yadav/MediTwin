# ============================================================
# Stage 1 — Build React application
# ============================================================
FROM node:22-bookworm-slim AS build

WORKDIR /app

# Frontend build-time configuration
ARG VITE_GOOGLE_CLIENT_ID=""
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

COPY package*.json ./

RUN if [ -f package-lock.json ]; then \
        npm ci; \
    else \
        npm install; \
    fi

COPY . .

RUN npm run build


# ============================================================
# Stage 2 — Serve production build with Nginx
# ============================================================
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]