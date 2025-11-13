#!/bin/bash
# 检查交易机器人状态

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/trading_bot.pid"
LATEST_LOG="$SCRIPT_DIR/logs/latest.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}📊 交易机器人状态检查${NC}"
echo "================================"

# 检查进程
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 状态: 运行中${NC}"
        echo "   PID: $PID"
        
        # 显示运行时间
        START_TIME=$(ps -p "$PID" -o lstart=)
        echo "   启动时间: $START_TIME"
        
        # 显示内存使用
        MEM=$(ps -p "$PID" -o rss= | awk '{print $1/1024 " MB"}')
        echo "   内存使用: $MEM"
        
        # 显示 CPU 使用
        CPU=$(ps -p "$PID" -o %cpu=)
        echo "   CPU 使用: $CPU%"
    else
        echo -e "${RED}❌ 状态: 已停止${NC}"
        echo "   (PID 文件存在但进程不存在)"
    fi
else
    echo -e "${YELLOW}⚠️  状态: 未运行${NC}"
fi

echo ""
echo "================================"

# 检查最新日志
if [ -f "$LATEST_LOG" ]; then
    echo -e "${BLUE}📝 最近的日志 (最后 20 行):${NC}"
    echo "--------------------------------"
    tail -20 "$LATEST_LOG"
    echo "--------------------------------"
    echo ""
    echo "完整日志: $LATEST_LOG"
else
    echo -e "${YELLOW}⚠️  没有找到日志文件${NC}"
fi

echo ""
echo "================================"

# 检查数据文件
DATA_DIR="$SCRIPT_DIR/live_trading_data"
if [ -d "$DATA_DIR" ]; then
    FILE_COUNT=$(ls -1 "$DATA_DIR"/*.csv 2>/dev/null | wc -l)
    if [ "$FILE_COUNT" -gt 0 ]; then
        echo -e "${GREEN}📁 数据文件: $FILE_COUNT 个${NC}"
        echo "   最新文件:"
        ls -lt "$DATA_DIR"/*.csv 2>/dev/null | head -3 | awk '{print "   " $9 " (" $6 " " $7 " " $8 ")"}'
    else
        echo -e "${YELLOW}⚠️  没有数据文件${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  数据目录不存在${NC}"
fi

echo ""
echo "================================"
echo "命令:"
echo "  启动: $SCRIPT_DIR/start_trading_bot.sh"
echo "  停止: $SCRIPT_DIR/stop_trading_bot.sh"
echo "  日志: tail -f $LATEST_LOG"
