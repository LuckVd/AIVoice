#!/bin/bash

# AI Voice TTS System 启动脚本

echo "🚀 启动 AI Voice TTS 系统..."

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

# 创建必要的目录
echo "📁 创建存储目录..."
mkdir -p storage/{audio,temp,uploads}

# 复制环境变量文件（如果不存在）
if [ ! -f backend/.env ]; then
    echo "📝 创建环境变量文件..."
    cp backend/.env.example backend/.env
    echo "⚠️  请编辑 backend/.env 文件配置您的环境变量"
fi

# 构建并启动服务
echo "🐳 构建并启动 Docker 容器..."
docker-compose up -d --build

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 初始化数据库
echo "🗄️  初始化数据库..."
docker-compose exec -T backend alembic upgrade head

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

echo ""
echo "✅ AI Voice TTS 系统启动成功！"
echo ""
echo "🌐 访问地址："
echo "   - 前端界面: http://localhost"
echo "   - API 文档: http://localhost/api/docs"
echo "   - 健康检查: http://localhost/api/health"
echo ""
echo "📊 查看日志："
echo "   docker-compose logs -f"
echo ""
echo "🛑 停止服务："
echo "   docker-compose down"
echo ""