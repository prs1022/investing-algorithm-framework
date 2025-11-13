# 🪙 交易对配置指南

## 为什么会出现 "No data provider found" 错误？

### 常见原因

1. **交易对不存在**
   - Gate.io 不支持该交易对
   - 交易对已被停用
   - 拼写错误

2. **市场名称错误**
   - 使用了错误的市场名称
   - 大小写不匹配

3. **数据类型不支持**
   - 某些交易对不支持特定时间框架
   - OHLCV 数据不可用

## 推荐的交易对

### ✅ 主流币种（强烈推荐）

```python
symbols = ["BTC", "ETH"]
```

**优点**：
- 流动性最好
- 数据最完整
- 所有交易所都支持
- 价格稳定

### ⚠️ 其他币种（需要测试）

```python
# 需要先测试是否支持
symbols = ["SOL", "LTC", "BNB", "ADA"]
```

**注意**：
- 可能不被所有交易所支持
- 数据可能不完整
- 流动性可能较差

## 测试交易对支持

### 方法 1：使用测试脚本

```bash
python examples/test_gateio_symbols.py
```

**输出示例**：
```
✅ 支持 BTC/USDT       价格: $89,500.00
✅ 支持 ETH/USDT       价格: $3,200.00
❌ 不支持 SOL/USDT
```

### 方法 2：手动测试

```python
import ccxt

exchange = ccxt.gateio()
markets = exchange.load_markets()

# 检查交易对
if 'BTC/USDT' in markets:
    print("✅ BTC/USDT 支持")
else:
    print("❌ BTC/USDT 不支持")

# 测试获取数据
try:
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '2h', limit=5)
    print(f"✅ 获取到 {len(ohlcv)} 条数据")
except Exception as e:
    print(f"❌ 错误: {e}")
```

## 配置交易对

### 在策略中配置

```python
class RiskControlledStrategy(TradingStrategy):
    # ⚠️ 重要：只使用经过测试的交易对！
    symbols = ["BTC", "ETH"]  # ✅ 推荐
    # symbols = ["SOL", "LTC"]  # ❌ 可能不支持
    
    position_sizes = [
        PositionSize(
            symbol="BTC",
            percentage_of_portfolio=10.0
        ),
        PositionSize(
            symbol="ETH",
            percentage_of_portfolio=10.0
        ),
    ]
```

### 完整的交易对格式

在数据源中，交易对会自动转换：

```python
symbol = "BTC"  # 策略中使用
full_symbol = f"{symbol}/USDT"  # 实际 API 调用: "BTC/USDT"
```

## 不同交易所的差异

### Gate.io
```python
market = "gateio"
trading_symbol = "USDT"
symbols = ["BTC", "ETH"]  # ✅ 支持
```

### Binance
```python
market = "binance"
trading_symbol = "USDT"
symbols = ["BTC", "ETH", "BNB"]  # ✅ 支持
```

### Coinbase
```python
market = "coinbase"
trading_symbol = "USD"  # 注意：Coinbase 使用 USD
symbols = ["BTC", "ETH"]  # ✅ 支持
```

## 常见错误和解决方案

### 错误 1：No data provider found

```
ImproperlyConfigured: No data provider found for given parameters: 
{'symbol': 'SOL/USDT', 'market': 'GATEIO', ...}
```

**原因**：Gate.io 不支持 SOL/USDT

**解决**：
1. 运行 `python examples/test_gateio_symbols.py`
2. 查看支持的交易对列表
3. 修改 `symbols = ["BTC", "ETH"]`

### 错误 2：Market not found

```
Market 'SOL/USDT' not found
```

**原因**：交易对拼写错误或不存在

**解决**：
- 检查拼写：`SOL/USDT` vs `SOL/USD`
- 确认交易所支持
- 使用主流币种

### 错误 3：Symbol not active

```
Symbol 'XXX/USDT' is not active
```

**原因**：交易对已被停用

**解决**：
- 选择其他交易对
- 检查交易所公告
- 使用活跃的交易对

## 添加新的交易对

### 步骤 1：测试支持

```bash
python examples/test_gateio_symbols.py
```

### 步骤 2：修改配置

```python
# 在 gateio_live_trading_with_risk_control.py 中
symbols = ["BTC", "ETH", "NEW_SYMBOL"]  # 添加新币种

position_sizes = [
    PositionSize(symbol="BTC", percentage_of_portfolio=10.0),
    PositionSize(symbol="ETH", percentage_of_portfolio=10.0),
    PositionSize(symbol="NEW_SYMBOL", percentage_of_portfolio=10.0),
]
```

### 步骤 3：测试运行

```bash
# 先回测测试
python examples/simple_trading_bot_example.py

# 再实盘测试
python examples/gateio_live_trading_with_risk_control.py
```

## 最佳实践

### 1. 使用主流币种

```python
# ✅ 推荐
symbols = ["BTC", "ETH"]

# ⚠️ 谨慎使用
symbols = ["SHIB", "DOGE", "PEPE"]
```

### 2. 测试后再使用

```bash
# 1. 测试交易对
python examples/test_gateio_symbols.py

# 2. 回测验证
python examples/simple_trading_bot_example.py

# 3. 实盘运行
python examples/gateio_live_trading_with_risk_control.py
```

### 3. 保持配置一致

```python
# symbols 和 position_sizes 必须匹配
symbols = ["BTC", "ETH"]

position_sizes = [
    PositionSize(symbol="BTC", ...),  # ✅ 匹配
    PositionSize(symbol="ETH", ...),  # ✅ 匹配
    # ❌ 不要添加 symbols 中没有的币种
]
```

### 4. 监控数据质量

```python
# 检查数据是否完整
if len(ohlcv_data) < 100:
    logger.warning(f"数据不足: {len(ohlcv_data)} 条")
```

## 故障排查清单

- [ ] 运行 `test_gateio_symbols.py` 确认支持
- [ ] 检查 `symbols` 配置
- [ ] 检查 `position_sizes` 配置
- [ ] 确认 `market` 名称正确
- [ ] 确认 `trading_symbol` 正确（USDT/USD）
- [ ] 检查网络连接
- [ ] 查看完整错误日志

## 推荐配置

### 保守配置（最稳定）

```python
symbols = ["BTC", "ETH"]
market = "gateio"
trading_symbol = "USDT"
```

### 激进配置（需要测试）

```python
symbols = ["BTC", "ETH", "BNB", "SOL"]
market = "gateio"
trading_symbol = "USDT"
```

---

**重要提示**：
- 始终使用 BTC 和 ETH 作为主要交易对
- 添加新币种前必须测试
- 定期检查交易对是否仍然活跃
- 关注交易所公告
