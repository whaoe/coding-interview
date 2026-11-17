#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "===================================================="
echo " AI问数 - 企业级销售经管数据管理平台 一键启动脚本"
echo "===================================================="

# 1. 选择 Python 解释器（优先使用项目 .venv 或本地 conda pytorch 环境）
if [ -x "$ROOT_DIR/backend/.venv/bin/python" ]; then
  PY_BIN="$ROOT_DIR/backend/.venv/bin/python"
elif [ -x "/opt/anaconda3/envs/pytorch/bin/python" ]; then
  PY_BIN="/opt/anaconda3/envs/pytorch/bin/python"
else
  PY_BIN="python3"
fi
echo "[1/3] 使用 Python 环境: $PY_BIN"

# 2. 启动后端 FastAPI 服务 (端口 8000)
cd "$ROOT_DIR/backend"
"$PY_BIN" -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "[2/3] FastAPI 后端已启动 (PID: $BACKEND_PID) -> http://127.0.0.1:8000"

# 3. 启动前端 Vite React 服务 (端口 5173)
cd "$ROOT_DIR/frontend"
if [ ! -d "node_modules" ]; then
  echo "正在安装前端依赖..."
  npm install --registry=https://registry.npmmirror.com
fi
echo "[3/3] 正在启动 React 前端服务 -> http://127.0.0.1:5173"
trap "kill $BACKEND_PID 2>/dev/null || true" EXIT
npm run dev
