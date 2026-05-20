#!/bin/bash
set -e

KEYS_DIR="/app/keys"
SOCKET_PATH="/tmp/ceph-ssh-agent.sock"

echo "[SSH Agent] Starting..."

# 创建密钥目录
mkdir -p $KEYS_DIR

# 启动 SSH Agent
echo "[SSH Agent] Initializing SSH agent..."
eval $(ssh-agent -s)
echo "[SSH Agent] Agent PID: $SSH_AGENT_PID"

# 将 Agent PID 写入文件供监控使用
echo $SSH_AGENT_PID > /tmp/ssh-agent.pid

# 从持久化目录加载已有密钥
echo "[SSH Agent] Loading keys from $KEYS_DIR..."
for keyfile in $KEYS_DIR/*/id_rsa; do
    if [ -f "$keyfile" ]; then
        zone=$(dirname "$keyfile" | xargs basename)
        echo "[SSH Agent] Adding key for zone: $zone"
        ssh-add "$keyfile" 2>/dev/null || echo "[SSH Agent] Warning: Failed to add $keyfile"
    fi
done

# 列出已加载的密钥
echo "[SSH Agent] Currently loaded keys:"
ssh-add -l || echo "[SSH Agent] No keys loaded"

echo "[SSH Agent] SSH Agent ready on socket: $SOCKET_PATH"

# 保持容器运行
echo "[SSH Agent] Holding container open..."
tail -f /dev/null
