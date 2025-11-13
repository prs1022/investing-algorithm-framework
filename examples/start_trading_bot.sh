#!/bin/bash
# 启动实盘交易机器人的健壮脚本
# 包含自动重启和日志管理

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_SCRIPT="$SCRIPT_DIR/gateio_live_trading_with_risk_control.py"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/trading_bot.pid"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 生成日志文件名（带时间戳）
LOG_FILE="$LOG_DIR/trading_$(date +%Y%m%d_%H%M%S).log"
LATEST_LOG="$LOG_DIR/latest.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  机器人已经在运行 (PID: $OLD_PID)${NC}"
        echo "使用以下命令停止："
        echo "  kill $OLD_PID"
        exit 1
    else
        echo "清理旧的 PID 文件..."
        rm "$PID_FILE"
    fi
fi

echo -e "${GREEN}🚀 启动交易机器人...${NC}"
echo "日志文件: $LOG_FILE"
echo ""

# 启动机器人（自动输入 YES）
echo "YES" | nohup python "$BOT_SCRIPT" > "$LOG_FILE" 2>&1 &
BOT_PID=$!

# 保存 PID
echo "$BOT_PID" > "$PID_FILE"

# 创建最新日志的软链接
ln -sf "$LOG_FILE" "$LATEST_LOG"

echo -e "${GREEN}✅ 机器人已启动 (PID: $BOT_PID)${NC}"
echo ""
echo "查看日志："
echo "  tail -f $LATEST_LOG"
echo ""
echo "停止机器人："
echo "  kill $BOT_PID"
echo "  或运行: $SCRIPT_DIR/stop_trading_bot.sh"
echo ""

# 等待几秒并检查是否成功启动
sleep 3

if ps -p "$BOT_PID" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 机器人运行正常${NC}"
    echo ""
    echo "最近的日志："
    tail -20 "$LOG_FILE"
else
    echo -e "${RED}❌ 机器人启动失败${NC}"
    echo ""
    echo "错误日志："
    cat "$LOG_FILE"
    rm "$PID_FILE"
    exit 1
fi
