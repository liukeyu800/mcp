# Linux 系统后端部署指南

## 环境要求

- **Python 版本**: >=3.8 (推荐使用 Python 3.9 或 3.10)
- **操作系统**: Linux (Ubuntu 20.04+, CentOS 7+, 或其他主流发行版)
- **Conda**: 已安装 Miniconda 或 Anaconda

## 创建 Conda 环境

### 1. 创建新的 conda 环境

```bash
# 使用 Python 3.10 (推荐)
conda create -n db-agent python=3.10 -y

# 或者使用 Python 3.9
conda create -n db-agent python=3.9 -y
```

### 2. 激活环境

```bash
conda activate db-agent
```

### 3. 安装系统依赖 (Ubuntu/Debian)

```bash
# 安装 MySQL 客户端库 (用于 pymysql)
sudo apt-get update
sudo apt-get install -y default-libmysqlclient-dev build-essential

# 或者 CentOS/RHEL
sudo yum install -y mysql-devel gcc gcc-c++
```

### 4. 安装 Python 依赖

```bash
# 进入项目目录
cd /path/to/mcp

# 安装核心依赖
pip install -r requirements.txt
```

### 5. 配置环境变量

创建 `.env` 文件（如果不存在）：

```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_database_name

# LLM 配置 (使用 Ollama)
LLM_PROVIDER=ollama
OLLAMA_BASE=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2000
LLM_TIMEOUT=60

# 或者使用其他 LLM 服务
# LLM_PROVIDER=custom
# LLM_API_URL=http://your-llm-server:port/v1/chat/completions
# LLM_MODEL=your-model-name
```

### 6. 运行后端服务

```bash
# 激活环境
conda activate db-agent

# 运行 API 服务器 (默认模式)
python main.py

# 或者运行 MCP 服务器
python main.py mcp

# 或者同时运行两个服务器
python main.py both
```

API 服务器默认运行在 `http://0.0.0.0:8000`

## 验证安装

### 1. 检查 API 服务

```bash
# 访问健康检查端点
curl http://localhost:8000/health

# 访问 API 文档
# 浏览器打开: http://localhost:8000/docs
```

### 2. 测试工具列表

```bash
curl http://localhost:8000/api/tools
```

## 常见问题

### 问题 1: pymysql 安装失败

**解决方案**:
```bash
# 安装 MySQL 开发库
sudo apt-get install default-libmysqlclient-dev  # Ubuntu/Debian
sudo yum install mysql-devel  # CentOS/RHEL

# 然后重新安装
pip install pymysql --force-reinstall --no-cache-dir
```

### 问题 2: SQLAlchemy 版本兼容性问题

**解决方案**:
```bash
# 确保使用 SQLAlchemy 2.x
pip install 'sqlalchemy>=2.0.0'
```

### 问题 3: MCP 包安装失败

**解决方案**:
```bash
# 确保 pip 是最新版本
pip install --upgrade pip

# 然后安装 MCP
pip install mcp --no-cache-dir
```

### 问题 4: 端口已被占用

**解决方案**:
```bash
# 修改 main.py 中的端口号，或使用环境变量
export API_PORT=8001
```

## 生产环境部署

### 使用 systemd 服务 (推荐)

创建服务文件 `/etc/systemd/system/db-agent.service`:

```ini
[Unit]
Description=Database Agent API Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/mcp
Environment="PATH=/path/to/conda/envs/db-agent/bin"
ExecStart=/path/to/conda/envs/db-agent/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable db-agent
sudo systemctl start db-agent
sudo systemctl status db-agent
```

### 使用 Gunicorn (可选)

```bash
# 安装 Gunicorn
pip install gunicorn

# 运行
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:create_fastapi_app
```

## 可选功能安装

### OCR 功能

如果需要使用 OCR 服务 (`ocr_service.py`):

```bash
# 安装 PaddleOCR (需要先安装 PaddlePaddle)
pip install paddlepaddle
pip install paddleocr
```

### 语音识别功能

如果需要使用语音识别服务 (`speech_service.py`):

```bash
# 进入 FireRedASR 目录
cd FireRedASR

# 安装依赖
pip install -r requirements.txt

# 下载模型文件到 FireRedASR/pretrained_models/
```

## 依赖版本说明

所有依赖版本已在 `requirements.txt` 中指定，建议使用固定版本以确保一致性：

- **Python**: 3.8+ (推荐 3.9 或 3.10)
- **FastAPI**: >=0.104.0
- **SQLAlchemy**: >=2.0.0
- **Pydantic**: >=2.0.0

## 快速安装脚本

```bash
#!/bin/bash
# 快速安装脚本

# 创建 conda 环境
conda create -n db-agent python=3.10 -y
conda activate db-agent

# 安装系统依赖 (Ubuntu)
sudo apt-get update
sudo apt-get install -y default-libmysqlclient-dev build-essential

# 安装 Python 依赖
cd /path/to/mcp
pip install -r requirements.txt

# 创建 .env 文件 (需要手动配置)
cp .env.example .env  # 如果存在的话

echo "安装完成！请配置 .env 文件后运行: python main.py"
```

