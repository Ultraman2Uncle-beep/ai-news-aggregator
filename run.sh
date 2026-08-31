#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "启动 AI 资讯聚合服务..."
echo "本机访问:     http://127.0.0.1:8000"
echo "局域网访问:   http://$(ipconfig getifaddr en0 2>/dev/null || echo 127.0.0.1):8000"
echo "手动触发更新: curl -X POST http://127.0.0.1:8000/update"
echo "按 Ctrl+C 停止"
echo ""

exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
