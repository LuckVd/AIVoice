# 🎙️ AI Voice TTS - 智能语音合成系统

一个基于 FastAPI、Celery 和 Microsoft Edge TTS 的现代化智能语音合成系统，支持长文本自动分块、多语音模型、异步处理和美观的 Web 界面。

## ✨ 主要特性

### 🎵 语音合成功能
- **多语言支持**: 中文、英文、方言等多种语音模型
- **长文本处理**: 自动文本分块，支持超长文本转换
- **高质量音频**: 基于 Microsoft Edge TTS，音质清晰自然
- **参数自定义**: 语速、音调、语音模型灵活调节
- **异步处理**: 基于 Celery 的后台任务队列，支持高并发

### 🎨 现代化界面
- **侧边栏导航**: 左侧可折叠菜单，快速切换不同功能模块
- **任务列表视图**: 水平表格布局，清晰展示所有任务信息
- **批量操作**: 支持多选和批量删除任务
- **音频保存**: 将喜欢的音频保存到收藏夹，方便管理
- **响应式设计**: 完美适配桌面、平板、手机等设备
- **实时状态**: 任务状态实时更新，支持进度跟踪
- **音频预览**: 在线音频播放和下载功能
- **固定播放器**: 右下角浮动音频播放器，便捷播放
- **扁平化设计**: 现代扁平按钮风格，简洁美观
- **快速预设**: 6种预设配置（故事朗读、新闻播报、教学讲解等）
- **优雅通知**: 现代化的通知系统，无干扰式反馈

### 🏗️ 技术架构
- **后端**: FastAPI + SQLAlchemy + Alembic
- **任务队列**: Celery + Redis
- **数据库**: PostgreSQL (端口 15432)
- **缓存**: Redis (端口 16379)
- **前端**: 纯 HTML/CSS/JavaScript，Ant Design CSS框架
- **Web服务器**: Nginx
- **语音引擎**: Microsoft Edge TTS (edge-tts)
- **容器化**: Docker + Docker Compose

## 🚀 快速开始

### 环境要求
- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- Node.js 14+ (可选，用于前端开发)

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/LuckVd/AIVoice.git
cd AIVoice
```

2. **使用 Docker Compose（推荐）**
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

3. **手动安装**

```bash
# 安装后端依赖
cd backend
pip install -r requirements.txt

# 配置数据库
export DATABASE_URL="postgresql://tts_user:tts_password@localhost:15432/tts_db"
export REDIS_URL="redis://localhost:16379"

# 运行数据库迁移
export PYTHONPATH=/opt/projects/AIVoice/backend:* && alembic upgrade head

# 启动后端服务
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 启动 Celery Worker（新终端）
celery -A app.core.celery_app worker --loglevel=info
```

### 访问应用
- **Web 界面**: http://localhost:80
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 📖 使用指南

### Web 界面操作

1. **创建语音任务**
   - 点击左侧菜单"📝 创建任务"
   - 输入要转换的文本内容（支持长文本自动分块）
   - 选择语音模型（支持中文、英文、方言等）
   - 调节语速和音调参数
   - 可使用快速预设配置
   - 点击"🚀 开始语音合成"

2. **任务管理**
   - 点击左侧菜单"📋 任务列表"
   - 查看所有任务的列表
   - 实时更新任务状态（等待中、处理中、已完成、失败）
   - 使用复选框选择多个任务进行批量删除
   - 查看任务详细信息（点击📄按钮）
   - 在线播放生成的音频（点击▶️按钮）
   - 下载音频文件到本地（点击⬇️按钮）
   - 保存喜欢的音频（点击💾按钮）

3. **保存的音频**
   - 点击左侧菜单"💾 保存的音频"
   - 查看所有已保存的音频列表
   - 在线播放、下载或删除保存的音频

4. **侧边栏操作**
   - 点击顶部的◀按钮折叠/展开侧边栏
   - 折叠后只显示图标，节省空间

5. **快速预设**
   - 📙 **极轻柔睡前**: 甜美女声，极慢语速，适合助眠
   - 📰 **标准新闻**: 清晰女声，标准语速，适合新闻
   - 🎓 **教学讲解**: 磁性男声，平稳语速，适合教学
   - 🌙 **温柔睡前**: 甜美女声，缓慢语速，适合故事
   - ⚡ **活力宣传**: 活泼女声，明快语速，适合宣传
   - 🎨 **自定义**: 根据需要自行调整

### API 使用

```bash
# 创建 TTS 任务
curl -X POST "http://localhost:8000/api/tts/" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，欢迎使用 AI Voice TTS 系统！",
    "voice": "zh-CN-XiaoxiaoNeural",
    "rate": "-15%",
    "pitch": "-20Hz"
  }'

# 获取任务列表
curl "http://localhost:8000/api/tts/"

# 获取任务详情
curl "http://localhost:8000/api/tts/{task_id}"

# 保存音频
curl -X POST "http://localhost:8000/api/saved-audios" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_id_here",
    "name": "我的音频"
  }'

# 获取保存的音频列表
curl "http://localhost:8000/api/saved-audios"

# 删除保存的音频
curl -X DELETE "http://localhost:8000/api/saved-audios/{audio_id}"

# 健康检查
curl "http://localhost:8000/health"
```

## 🏛️ 项目结构

```
AIVoice/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── tts.py         # TTS API 接口
│   │   │   └── saved_audios.py # 保存音频 API 接口
│   │   ├── core/              # 核心模块
│   │   │   ├── config.py      # 配置文件
│   │   │   ├── database.py    # 数据库连接
│   │   │   └── celery_app.py  # Celery 配置
│   │   ├── models/            # 数据模型
│   │   │   ├── tts.py         # TTS 任务模型
│   │   │   └── saved_audio.py # 保存音频模型
│   │   ├── services/          # 业务逻辑
│   │   │   └── tts_service.py # TTS 服务
│   │   ├── schemas/           # Pydantic 模式
│   │   │   └── tts.py         # TTS 数据模式
│   │   └── tasks/             # Celery 任务
│   │       └── tts_tasks.py   # TTS 异步任务
│   └── alembic/               # 数据库迁移
│       └── versions/          # 迁移文件
│           └── 20241227_add_saved_audios_table.py
├── storage/                   # 存储目录
│   ├── audio/                 # 生成的音频文件
│   ├── saved/                # 保存的音频文件
│   ├── uploads/               # 上传文件
│   ├── temp/                  # 临时文件
│   └── index.html             # Web 界面
├── frontend/                  # 前端配置
│   └── nginx.conf            # Nginx 配置
├── docker-compose.yml         # Docker Compose 配置
├── requirements.txt           # Python 依赖
└── README.md                  # 项目文档
```

## 🔧 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL 数据库连接 | `postgresql://tts_user:tts_password@localhost:15432/tts_db` |
| `REDIS_URL` | Redis 连接地址 | `redis://localhost:16379` |
| `STORAGE_PATH` | 文件存储路径 | `/opt/projects/AIVoice/storage` |
| `MAX_FILE_SIZE` | 最大文件大小 | `10485760` (10MB) |
| `MAX_CHARS_PER_CHUNK` | 文本分块大小 | `500` |
| `DEFAULT_VOICE` | 默认语音模型 | `zh-CN-XiaoxiaoNeural` |
| `DEFAULT_RATE` | 默认语速 | `-15%` |
| `DEFAULT_PITCH` | 默认音调 | `-20Hz` |



## 🐳 Docker 部署

### 使用 Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
docker-compose logs -f celery

# 停止服务
docker-compose down

# 重新构建并启动
docker-compose up --build -d
```

### 单独部署

```bash
# 构建后端镜像
docker build -f docker/Dockerfile.backend -t aivoice-backend .

# 构建 Celery 镜像
docker build -f docker/Dockerfile.celery -t aivoice-celery .

# 运行容器
docker run -d --name aivoice-backend -p 8000:8000 aivoice-backend
docker run -d --name aivoice-celery aivoice-celery
```

## 🔍 监控和日志

### 健康检查
```bash
curl http://localhost:8000/health
```

### Celery 监控
```bash
# 查看 Celery 状态
celery -A app.core.celery_app inspect active

# 查看队列信息
celery -A app.core.celery_app inspect stats
```

### 日志查看
```bash
# 查看应用日志
tail -f logs/app.log

# 查看 Celery 日志
tail -f logs/celery.log

# Docker 环境
docker-compose logs -f backend
docker-compose logs -f celery
```

## 🛠️ 开发指南

### 本地开发环境设置

1. **安装依赖**
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio black flake8
```

2. **运行测试**
```bash
pytest tests/
```

3. **代码格式化**
```bash
black app/
flake8 app/
```

### 数据库迁移

```bash
# 创建迁移文件
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### API 开发

所有 API 端点都在 `app/api/` 目录下：

**TTS 任务相关：**
- `GET /api/tts/` - 获取任务列表
- `POST /api/tts/` - 创建新任务
- `GET /api/tts/{task_id}` - 获取任务详情
- `GET /api/tts/{task_id}/status` - 获取任务状态
- `DELETE /api/tts/{task_id}` - 删除任务
- `PATCH /api/tts/{task_id}/cancel` - 取消任务

**保存音频相关：**
- `GET /api/saved-audios` - 获取保存的音频列表
- `POST /api/saved-audios` - 保存音频
- `GET /api/saved-audios/{audio_id}` - 获取单个保存的音频
- `DELETE /api/saved-audios/{audio_id}` - 删除保存的音频
- `GET /api/saved-audios/{audio_id}/download` - 下载保存的音频

## 🔒 安全考虑

1. **文件上传安全**
   - 文件类型验证
   - 文件大小限制
   - 扫描恶意内容

2. **API 安全**
   - 请求频率限制
   - 输入参数验证
   - 错误信息脱敏

3. **数据保护**
   - 敏感信息加密存储
   - 定期清理临时文件
   - 访问日志记录

## 📈 性能优化

1. **异步处理**
   - 使用 Celery 处理耗时的 TTS 任务
   - 支持任务并发处理
   - 任务结果缓存

2. **数据库优化**
   - 合理的索引设计
   - 查询优化
   - 连接池管理

3. **文件管理**
   - 音频文件压缩
   - 静态文件 CDN
   - 定期清理过期文件

## 🐛 故障排除

### 常见问题

1. **TTS 任务失败**
   - 检查网络连接
   - 验证语音模型名称
   - 查看错误日志

2. **音频无法播放**
   - 检查文件路径
   - 验证音频格式
   - 确认文件权限

3. **界面显示异常**
   - 清除浏览器缓存
   - 检查控制台错误
   - 验证静态文件服务

### 日志分析

```bash
# 查看错误日志
grep "ERROR" logs/app.log

# 查看 TTS 相关日志
grep "TTS" logs/app.log

# 查看 Celery 任务日志
grep "task" logs/celery.log
```



## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 👥 作者

- **LuckVd** - 项目维护者

## 🙏 致谢
- [Edge TTS](https://github.com/rany2/edge-tts) - Microsoft Edge TTS Python 实现


## 📞 支持

如果您遇到任何问题或有任何建议，请：

1. 查看 [Issues](https://github.com/LuckVd/AIVoice/issues)
2. 创建新的 Issue

---

**🎙️ AI Voice TTS - 让文字拥有声音的力量！**