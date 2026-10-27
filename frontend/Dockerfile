# ---------- Stage 1: build the Angular app ----------
FROM node:22-alpine AS build

WORKDIR /app

# Install dependencies first (cached as long as package*.json don't change)
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npx ng build --configuration production

# ---------- Stage 2: serve the built files with nginx ----------
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

EXPOSE 80
