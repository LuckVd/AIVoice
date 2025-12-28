#!/bin/bash

# AI Voice TTS - Development Startup Script

# 设置环境变量
export PYTHONPATH=/opt/projects/AIVoice/backend:$PYTHONPATH
export DATABASE_URL=postgresql://tts_user:tts_password@localhost:15432/tts_db
export REDIS_URL=redis://localhost:16379/0
export STORAGE_PATH=/opt/projects/AIVoice/storage

echo "🚀 Starting AI Voice TTS Services..."

# 停止已存在的进程
echo "🛑 Stopping existing processes..."
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "celery.*app.core.celery_app" 2>/dev/null
sleep 2

# 启动Backend
echo "📡 Starting Backend (FastAPI)..."
cd /opt/projects/AIVoice/backend
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/aivoice_backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
sleep 3

# 启动Celery Worker
echo "⚙️ Starting Celery Worker..."
nohup celery -A app.core.celery_app worker --loglevel=info > /tmp/aivoice_celery.log 2>&1 &
CELERY_PID=$!
echo "   Celery PID: $CELERY_PID"
sleep 2

# 检查服务状态
echo ""
echo "✅ Services Status:"
echo "===================="

# 检查Backend
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✓ Backend: Running (http://localhost:8000)"
else
    echo "✗ Backend: Failed to start"
    echo "   Check logs: tail -f /tmp/aivoice_backend.log"
fi

# 检查Celery
if ps -p $CELERY_PID > /dev/null; then
    echo "✓ Celery Worker: Running (PID: $CELERY_PID)"
else
    echo "✗ Celery Worker: Failed to start"
    echo "   Check logs: tail -f /tmp/aivoice_celery.log"
fi

echo ""
echo "📝 Logs:"
echo "  Backend: tail -f /tmp/aivoice_backend.log"
echo "  Celery: tail -f /tmp/aivoice_celery.log"
echo ""
echo "🌐 Frontend URL: http://localhost:8000/app"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "💡 To stop services: pkill -f 'uvicorn app.main:app' && pkill -f 'celery.*app.core.celery_app'"
echo ""
