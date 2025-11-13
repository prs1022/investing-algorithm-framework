# 🌐 网络错误处理指南

## 常见网络错误

### 1. ReadTimeoutError
```
urllib3.exceptions.ReadTimeoutError: HTTPSConnectionPool(host='api.gateio.ws', port=443): Read timed out.
```

**原因**：
- 网络连接不稳定
- Gate.io API 响应慢
- 防火墙或代理问题
- 请求超时

**解决方案**：
- ✅ 已添加自动重试机制
- ✅ 程序会自动重启（最多 5 次）
- ✅ 每次重试间隔递增（60秒、120秒、180秒...）

### 2. ConnectionError
```
requests.exceptions.ConnectionError: Failed to establish a new connection
```

**原因**：
- 无网络连接
- DNS 解析失败
- Gate.io 服务不可用

**解决方案**：
- 检查网络连接
- 检查 DNS 设置
- 等待 Gate.io 服务恢复

### 3. SSLError
```
requests.exceptions.SSLError: SSL: CERTIFICATE_VERIFY_FAILED
```

**原因**：
- SSL 证书问题
- 系统时间不正确
- 中间人攻击（少见）

**解决方案**：
```bash
# 更新 CA 证书
pip install --upgrade certifi

# 检查系统时间
date
```

## 自动重试机制

### 工作原理

```python
max_retries = 5  # 最多重试 5 次
retry_count = 0

while retry_count < max_retries:
    try:
        app.run(number_of_iterations=999999)
        break  # 成功运行
    except NetworkError:
        retry_count += 1
        wait_time = min(60 * retry_count, 300)  # 最多等 5 分钟
        sleep(wait_time)
        # 重新启动
```

### 重试时间表

| 重试次数 | 等待时间 | 累计时间 |
|---------|---------|---------|
| 1 | 60 秒 | 1 分钟 |
| 2 | 120 秒 | 3 分钟 |
| 3 | 180 秒 | 6 分钟 |
| 4 | 240 秒 | 10 分钟 |
| 5 | 300 秒 | 15 分钟 |

### 日志示例

```
2025-11-11 16:00:00 - ERROR - ⚠️  网络错误 (ReadTimeoutError): Read timed out
2025-11-11 16:00:00 - WARNING - 🔄 将在 60 秒后重试 (第 1/5 次)
2025-11-11 16:01:00 - INFO - 🚀 重新启动机器人...
```

## 使用健壮的启动脚本

### 1. 启动机器人

```bash
# 给脚本添加执行权限
chmod +x examples/*.sh

# 启动
./examples/start_trading_bot.sh
```

**功能**：
- ✅ 检查是否已在运行
- ✅ 后台运行
- ✅ 自动创建日志
- ✅ 保存 PID 文件
- ✅ 启动验证

### 2. 停止机器人

```bash
./examples/stop_trading_bot.sh
```

**功能**：
- ✅ 优雅退出（SIGTERM）
- ✅ 等待 10 秒
- ✅ 强制终止（如果需要）
- ✅ 清理 PID 文件

### 3. 检查状态

```bash
./examples/check_trading_bot.sh
```

**显示**：
- 运行状态
- PID 和启动时间
- 内存和 CPU 使用
- 最近的日志
- 数据文件统计

## 手动运行（调试用）

### 前台运行（查看实时输出）

```bash
cd examples
python gateio_live_trading_with_risk_control.py
```

**优点**：
- 实时查看输出
- 容易调试
- Ctrl+C 立即停止

**缺点**：
- 终端关闭后停止
- 不适合长期运行

### 后台运行（推荐）

```bash
cd examples
nohup python gateio_live_trading_with_risk_control.py > output.log 2>&1 &

# 查看日志
tail -f output.log

# 查看 PID
ps aux | grep gateio_live_trading

# 停止
kill <PID>
```

## 网络优化建议

### 1. 使用稳定的网络

```bash
# 测试网络延迟
ping api.gateio.ws

# 测试 DNS 解析
nslookup api.gateio.ws

# 测试 HTTPS 连接
curl -I https://api.gateio.ws
```

### 2. 使用代理（如果需要）

```bash
# 设置代理
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"

# 运行机器人
python gateio_live_trading_with_risk_control.py
```

### 3. 增加超时时间

在代码中修改（如果框架支持）：

```python
# 在 .env 文件中添加
REQUEST_TIMEOUT=60  # 60 秒超时
```

### 4. 使用服务器运行

**推荐配置**：
- VPS 或云服务器
- 稳定的网络连接
- 低延迟到 Gate.io
- 24/7 运行

**推荐服务商**：
- AWS EC2
- Google Cloud
- DigitalOcean
- Vultr
- Linode

## 监控和告警

### 1. 日志监控

```bash
# 监控错误
tail -f logs/latest.log | grep -i error

# 监控网络错误
tail -f logs/latest.log | grep -i timeout

# 监控交易
tail -f logs/latest.log | grep -E "BUY|SELL"
```

### 2. 进程监控

```bash
# 每 5 分钟检查一次
*/5 * * * * /path/to/examples/check_trading_bot.sh > /dev/null 2>&1
```

### 3. 自动重启（使用 systemd）

创建 `/etc/systemd/system/trading-bot.service`：

```ini
[Unit]
Description=Gate.io Trading Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/investing-algorithm-framework/examples
ExecStart=/usr/bin/python3 gateio_live_trading_with_risk_control.py
Restart=always
RestartSec=60
StandardOutput=append:/path/to/logs/trading.log
StandardError=append:/path/to/logs/trading.log

[Install]
WantedBy=multi-user.target
```

启动：
```bash
sudo systemctl daemon-reload
sudo systemctl start trading-bot
sudo systemctl enable trading-bot
```

## 故障排查

### 问题：频繁超时

**检查**：
```bash
# 1. 网络延迟
ping -c 10 api.gateio.ws

# 2. 网络稳定性
mtr api.gateio.ws

# 3. DNS 问题
dig api.gateio.ws
```

**解决**：
- 更换网络
- 使用 VPN
- 更换 DNS（如 8.8.8.8）
- 联系 ISP

### 问题：重试后仍失败

**检查**：
```bash
# 查看完整错误日志
cat logs/latest.log | grep -A 10 "ERROR"

# 检查 Gate.io 状态
curl -I https://api.gateio.ws
```

**解决**：
- 检查 API 密钥
- 检查账户状态
- 等待 Gate.io 服务恢复
- 联系 Gate.io 支持

### 问题：程序崩溃

**检查**：
```bash
# 查看崩溃日志
tail -100 logs/latest.log

# 检查系统资源
free -h
df -h
```

**解决**：
- 增加内存
- 清理磁盘空间
- 检查代码错误
- 更新依赖

## 最佳实践

1. ✅ 使用启动脚本（`start_trading_bot.sh`）
2. ✅ 定期检查状态（`check_trading_bot.sh`）
3. ✅ 监控日志文件
4. ✅ 使用稳定的服务器
5. ✅ 设置告警通知
6. ✅ 定期备份数据
7. ✅ 测试网络连接
8. ✅ 保持依赖更新

---

**提示**: 网络错误是正常的，自动重试机制会处理大部分情况。如果频繁出现，考虑优化网络环境。
