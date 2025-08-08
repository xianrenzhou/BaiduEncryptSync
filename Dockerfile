FROM python:3.10-slim

WORKDIR /app

# 安装基本依赖
RUN apt-get update && apt-get install -y \
    inotify-tools \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置挂载点用于持久化配置和映射本地文件
VOLUME ["/app/config", "/data"]

# 设置默认环境变量
ENV WATCH_DIR=/data \
    REMOTE_DIR=/apps/autoSync \
    ENCRYPT=false \
    PASSWORD=123456 \
    RECURSIVE=true \
    MIN_SIZE=0 \
    COOLDOWN=2 \
    UPLOAD_EXISTING=false \
    WORKERS=3 \
    EXCLUDE_DIRS="" \
    AUTH_CODE=""

# 入口脚本
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
