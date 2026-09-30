FROM oven/bun:1 AS build
WORKDIR /web
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/. .
RUN bun run build

FROM nginx:alpine
COPY --from=build /web/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
