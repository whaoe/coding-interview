# 阶段 1：构建 React 前端静态产物
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install --registry=https://registry.npmmirror.com
COPY frontend/ ./
RUN npm run build

# 阶段 2：构建 Python FastAPI 生产环境镜像（Linux 部署）
FROM python:3.11-slim
WORKDIR /app

# 复制后端依赖并安装
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r backend/requirements.txt

# 复制后端源码与前端构建产物
COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
