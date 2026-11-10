# 构建阶段
FROM node:18-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 运行阶段：Nginx 服务静态资源并代理 API
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Nginx 配置：前端静态 + API 代理
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
