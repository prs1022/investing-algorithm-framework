#!/bin/bash
# 停止实盘交易机器人

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/trading_bot.pid"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠️  没有找到运行中的机器人${NC}"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  机器人进程不存在 (PID: $PID)${NC}"
    rm "$PID_FILE"
    exit 1
fi

echo -e "${YELLOW}🛑 正在停止机器人 (PID: $PID)...${NC}"

# 发送 SIGTERM 信号（优雅退出）
kill "$PID"

# 等待最多 10 秒
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 机器人已停止${NC}"
        rm "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# 如果还没停止，强制终止
echo -e "${RED}⚠️  机器人未响应，强制终止...${NC}"
kill -9 "$PID"
sleep 1

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 机器人已强制停止${NC}"
    rm "$PID_FILE"
else
    echo -e "${RED}❌ 无法停止机器人${NC}"
    exit 1
fi
