# 🚀 实盘交易指南

## 📋 回测 vs 实盘交易对比

| 特性 | 回测 | 实盘交易 |
|------|------|----------|
| 命令 | `app.run_backtest()` | `app.run()` |
| 数据 | 历史数据 | 实时数据 |
| 交易 | 模拟 | 真实 |
| 风险 | 无 | 有真实资金风险 |
| 运行方式 | 一次性完成 | 持续运行 |

## 🔧 配置步骤

### 1. 获取 Gate.io API 密钥

1. 登录 [Gate.io](https://www.gate.io/)
2. 进入 **账户设置 → API 管理**
3. 创建新的 API 密钥
4. **重要**：设置 IP 白名单，限制交易权限

### 2. 配置 .env 文件

在项目根目录创建或编辑 `.env` 文件：

```bash
# Gate.io API 配置
GATEIO_API_KEY=your_api_key_here
GATEIO_SECRET_KEY=your_secret_key_here

# 可选：其他交易所
# BINANCE_API_KEY=...
# BINANCE_SECRET_KEY=...
```

### 3. 运行实盘交易

```bash
# 先确保回测结果满意
python examples/simple_trading_bot_example.py

# 然后运行实盘交易
python examples/gateio_live_trading_bot.py
```

## ⚠️ 重要安全提示

### 🛡️ 风险管理

1. **从小资金开始**：建议先用 $100-500 测试
2. **设置止损**：考虑添加最大亏损限制
3. **监控运行**：定期检查机器人状态
4. **备份数据**：保存交易记录和日志

### 🔒 API 安全

1. **限制权限**：只开启必要的交易权限
2. **IP 白名单**：限制 API 只能从特定 IP 访问
3. **定期更换**：定期更新 API 密钥
4. **不要分享**：永远不要分享你的 API 密钥

### 📊 监控建议

1. **日志记录**：查看 `logs/` 目录的日志文件
2. **交易通知**：考虑添加邮件/Telegram 通知
3. **性能追踪**：定期检查盈亏情况
4. **异常处理**：设置网络断线、API 错误的处理机制

## 🔄 回测到实盘的转换

### 回测代码（测试用）

```python
# simple_trading_bot_example.py
backtest = app.run_backtest(
    backtest_date_range=backtest_range,
    initial_amount=1000,
    risk_free_rate=0.03
)
```

### 实盘代码（真实交易）

```python
# gateio_live_trading_bot.py
app.add_market(
    market="gateio",
    trading_symbol="USDT",
    initial_balance=1000
)

app.run()  # 持续运行，实时交易
```

## 📈 策略优化建议

在实盘前，建议：

1. **多时间段回测**：测试不同市场环境
2. **参数优化**：调整 RSI 阈值、EMA 周期等
3. **风险控制**：添加止损、止盈逻辑
4. **资金管理**：合理分配仓位大小

## 🐛 常见问题

### Q: 如何停止实盘交易？
A: 按 `Ctrl+C` 停止程序。已开仓的交易不会自动平仓。

### Q: 机器人会24小时运行吗？
A: 是的，`app.run()` 会持续运行，按设定的时间间隔检查信号。

### Q: 如何查看当前持仓？
A: 查看日志文件或登录 Gate.io 网页查看。

### Q: 网络断线怎么办？
A: 框架会自动重试，但建议使用稳定的服务器运行。

### Q: 可以同时运行多个策略吗？
A: 可以，使用 `app.add_strategy()` 添加多个策略。

## 📚 进阶功能

### 添加通知

```python
# 在策略中添加
import requests

def send_telegram_notification(message):
    # 发送 Telegram 通知
    pass

# 在买入/卖出时调用
if buy_signal:
    send_telegram_notification(f"买入 {symbol}")
```

### 添加止损

```python
position_sizes = [
    PositionSize(
        symbol="BTC",
        percentage_of_portfolio=20.0,
        stop_loss_percentage=5.0,  # 5% 止损
        take_profit_percentage=10.0  # 10% 止盈
    )
]
```

### 使用数据库

```python
# 框架会自动使用 SQLite 存储交易数据
# 数据库文件：resources/app.db
```

## 🎯 下一步

1. ✅ 完成回测，确保策略盈利
2. ✅ 配置 API 密钥
3. ✅ 小资金测试实盘
4. ✅ 监控并优化策略
5. ✅ 逐步增加资金

---

**免责声明**：加密货币交易有风险，可能导致资金损失。本指南仅供教育目的，不构成投资建议。请自行承担交易风险。
