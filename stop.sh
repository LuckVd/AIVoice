#!/bin/bash

echo "🛑 Stopping AI Voice TTS Services..."

# 停止Backend
pkill -f "uvicorn app.main:app" && echo "✓ Backend stopped" || echo "✗ Backend not running"

# 停止Celery Worker
pkill -f "celery.*app.core.celery_app" && echo "✓ Celery Worker stopped" || echo "✗ Celery Worker not running"

echo ""
echo "✅ All services stopped"
