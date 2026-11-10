FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（chromadb 等可能需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 初始化数据库
RUN python -c "from app.db.database import init_db; init_db()"

EXPOSE 8000 8501

# 默认启动后端 API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
