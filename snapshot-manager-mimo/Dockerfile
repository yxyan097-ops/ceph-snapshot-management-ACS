FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装依赖
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# 复制应用代码
COPY ceph_snapshot_manager/ ./ceph_snapshot_manager/
COPY templates/ ./templates/
COPY static/ ./static/
COPY app.py .

# 复制快照清理脚本
COPY scripts/snap-trim.sh /scripts/snap-trim.sh
RUN chmod +x /scripts/snap-trim.sh

EXPOSE 5000

CMD ["python", "app.py"]
