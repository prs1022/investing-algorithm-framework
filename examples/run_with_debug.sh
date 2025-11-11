#!/bin/bash
# 运行实盘交易并捕获所有输出

echo "Starting trading bot with full debug output..."
echo "YES" | python gateio_live_trading_with_risk_control.py 2>&1 | tee trading_bot.log

echo ""
echo "Log saved to trading_bot.log"
echo "Last 50 lines:"
tail -50 trading_bot.log
