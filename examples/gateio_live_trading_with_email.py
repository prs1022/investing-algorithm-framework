"""
Gate.io 实盘交易机器人 - 带邮件通知版本

在 gateio_live_trading_with_risk_control.py 的基础上添加邮件通知功能
"""

# 首先导入原始策略
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from gateio_live_trading_with_risk_control import *
from email_notifier import EmailNotifier

# 重写策略类，添加邮件通知
class RiskControlledStrategyWithEmail(RiskControlledStrategy):
    """带邮件通知的风险控制策略"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 初始化邮件通知器
        self.email_notifier = EMAIL_NOTIFIER
        self.last_portfolio_value = self.INITIAL_CAPITAL
        
        # 记录上次的持仓状态（用于检测变化）
        self.last_positions = {}  # {symbol: amount}
        self.last_trades_count = 0
    
    def _send_trade_email(self, context: Context, trade_type: str, symbol: str, amount: float, price: float):
        """发送交易邮件通知"""
        if not self.email_notifier:
            return
        
        try:
            portfolio = context.get_portfolio()
            portfolio_value = portfolio.get_net_size()
            
            if trade_type == "BUY":
                cost = amount * price
                self.email_notifier.send_buy_notification(
                    symbol=symbol,
                    amount=amount,
                    price=price,
                    cost=cost,
                    portfolio_value=portfolio_value,
                    reason="RSI 超卖 + EMA 交叉向上"
                )
            elif trade_type == "SELL":
                revenue = amount * price
                # 尝试计算盈亏
                profit = 0
                profit_pct = 0
                
                try:
                    # 获取该币种的交易历史来计算盈亏
                    trades = [t for t in portfolio.get_open_trades() if t.target_symbol == symbol]
                    if trades:
                        trade = trades[0]
                        profit = (price - trade.open_price) * amount
                        profit_pct = (profit / (trade.open_price * amount)) * 100
                except:
                    pass
                
                self.email_notifier.send_sell_notification(
                    symbol=symbol,
                    amount=amount,
                    price=price,
                    revenue=revenue,
                    profit=profit,
                    profit_pct=profit_pct,
                    portfolio_value=portfolio_value,
                    reason="RSI 超买 + EMA 交叉向下"
                )
        except Exception as e:
            logger.error(f"发送交易邮件失败: {e}")
    
    def _check_position_changes(self, context: Context):
        """
        检查持仓变化并发送邮件通知
        这是检测交易执行的关键方法
        """
        if not self.email_notifier:
            return
        
        try:
            portfolio = context.get_portfolio()
            current_positions = {}
            
            # 获取当前所有持仓
            for symbol in self.symbols:
                try:
                    position = context.get_position(symbol)
                    if position and position.amount > 0:
                        current_positions[symbol] = position.amount
                except:
                    current_positions[symbol] = 0
            
            # 检查每个币种的持仓变化
            for symbol in self.symbols:
                last_amount = self.last_positions.get(symbol, 0)
                current_amount = current_positions.get(symbol, 0)
                
                # 持仓增加 = 买入
                if current_amount > last_amount:
                    amount_change = current_amount - last_amount
                    
                    # 获取最新价格
                    try:
                        trades = [t for t in portfolio.get_open_trades() 
                                 if t.target_symbol == symbol]
                        if trades:
                            price = trades[-1].open_price
                            cost = amount_change * price
                            
                            self.email_notifier.send_buy_notification(
                                symbol=symbol,
                                amount=amount_change,
                                price=price,
                                cost=cost,
                                portfolio_value=portfolio.get_net_size(),
                                reason="RSI 超卖 + EMA 交叉向上"
                            )
                            logger.info(f"📧 已发送买入通知邮件: {symbol}")
                    except Exception as e:
                        logger.error(f"发送买入邮件失败: {e}")
                
                # 持仓减少 = 卖出
                elif current_amount < last_amount:
                    amount_change = last_amount - current_amount
                    
                    # 尝试获取卖出信息
                    try:
                        # 从已平仓的交易中获取信息
                        closed_trades = [t for t in portfolio.get_closed_trades() 
                                        if t.target_symbol == symbol]
                        
                        if closed_trades:
                            last_trade = closed_trades[-1]
                            price = last_trade.last_reported_price
                            revenue = amount_change * price
                            profit = last_trade.net_gain
                            profit_pct = last_trade.net_gain_percentage
                            
                            self.email_notifier.send_sell_notification(
                                symbol=symbol,
                                amount=amount_change,
                                price=price,
                                revenue=revenue,
                                profit=profit,
                                profit_pct=profit_pct,
                                portfolio_value=portfolio.get_net_size(),
                                reason="RSI 超买 + EMA 交叉向下"
                            )
                            logger.info(f"📧 已发送卖出通知邮件: {symbol}")
                    except Exception as e:
                        logger.error(f"发送卖出邮件失败: {e}")
            
            # 更新记录的持仓
            self.last_positions = current_positions
            
        except Exception as e:
            logger.error(f"检查持仓变化失败: {e}")
    
    def run_strategy(self, context: Context, data: Dict[str, Any]):
        """
        重写 run_strategy 以在策略执行前后检查持仓变化
        """
        # 1. 保存数据
        try:
            self._save_ohlcv_data(data)
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
        
        # 2. 执行原始策略（包括止损、止盈、信号生成等）
        super().run_strategy(context, data)
        
        # 3. 检查持仓变化并发送邮件
        self._check_position_changes(context)
    
    def _emergency_close_all_positions(self, context: Context):
        """紧急平仓所有持仓（重写以添加邮件通知）"""
        portfolio = context.get_portfolio()
        open_trades = portfolio.get_open_trades()
        
        # 发送止损邮件
        if self.email_notifier and open_trades:
            try:
                total_loss = 0
                positions = []
                
                for trade in open_trades:
                    pnl = trade.net_gain_absolute
                    total_loss += pnl
                    positions.append({
                        'symbol': trade.target_symbol,
                        'pnl': pnl
                    })
                
                portfolio_value = portfolio.get_net_size()
                loss_pct = (abs(total_loss) / portfolio_value) * 100
                
                self.email_notifier.send_stop_loss_notification(
                    total_loss=total_loss,
                    loss_pct=loss_pct,
                    portfolio_value=portfolio_value,
                    positions=positions
                )
            except Exception as e:
                logger.error(f"发送止损邮件失败: {e}")
        
        # 执行原始的平仓逻辑
        super()._emergency_close_all_positions(context)


if __name__ == "__main__":
    import os
    
    # 设置独立的数据库，避免与回测冲突
    os.environ["DATABASE_NAME"] = "live-trading-database.sqlite3"
    
    print("=" * 80)
    print("⚠️  Gate.io 实盘交易机器人 - 风险控制 + 邮件通知版")
    print("=" * 80)
    print("\n💰 资金配置:")
    print(f"   初始资金: ${RiskControlledStrategy.INITIAL_CAPITAL} USDT")
    print(
        f"   每次开仓: {RiskControlledStrategy.MAX_POSITION_SIZE_PCT}% "
        f"(最多 ${RiskControlledStrategy.INITIAL_CAPITAL * RiskControlledStrategy.MAX_POSITION_SIZE_PCT / 100:.2f})"
    )
    
    print("\n🛡️ 风险控制:")
    print(
        f"   止损线: -{RiskControlledStrategy.MAX_LOSS_PCT}% "
        f"(${RiskControlledStrategy.INITIAL_CAPITAL * (1 - RiskControlledStrategy.MAX_LOSS_PCT/100):.2f})"
    )
    print(f"   止盈策略: 斐波那契分批止盈")
    
    fib_levels = RiskControlledStrategy.FIBONACCI_LEVELS[:6]
    print(
        f"   止盈点: {', '.join([f'{l*100:.0f}%' for l in fib_levels])}... "
        f"(每次止盈50%)"
    )
    
    print("\n📧 邮件通知:")
    if EMAIL_NOTIFIER:
        print(f"   ✅ 已启用")
        print(f"   发件人: {os.getenv('EMAIL_SENDER')}")
        print(f"   收件人: {os.getenv('EMAIL_RECEIVER')}")
    else:
        print(f"   ⚠️  未配置")
        print(f"   提示: 在 .env 文件中配置 EMAIL_SENDER 和 EMAIL_AUTH_CODE")
    
    print("\n" + "=" * 80)
    print("\n请确认:")
    print("1. ✅ 已配置 Gate.io API 密钥")
    print("2. ✅ 账户有至少 $20 USDT")
    print("3. ✅ 理解风险控制机制")
    print("4. ✅ 准备好监控交易")
    
    response = input("\n是否继续？(输入 'YES' 继续): ")
    
    if response != "YES":
        print("❌ 已取消")
        exit()
    
    print("\n🚀 启动交易机器人...\n")
    
    app = create_app()
    
    app.add_strategy(
        RiskControlledStrategyWithEmail(
            time_unit=TimeUnit.HOUR,
            interval=2,
            market="gateio",
            rsi_time_frame="2h",
            rsi_period=14,
            rsi_overbought_threshold=65,
            rsi_oversold_threshold=35,
            ema_time_frame="2h",
            ema_short_period=12,
            ema_long_period=26,
            ema_cross_lookback_window=10,
        )
    )

    app.add_market(market="gateio", trading_symbol="USDT", initial_balance=20)

    print("\n⏰ 机器人将持续运行...")
    print("   按 Ctrl+C 可以随时停止\n")

    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        try:
            app.run(number_of_iterations=999999)
            break

        except KeyboardInterrupt:
            print("\n\n🛑 用户中断，正在安全退出...")
            print("✅ 机器人已停止")
            break

        except Exception as e:
            retry_count += 1
            error_type = type(e).__name__

            # 网络相关错误，自动重试
            if any(
                err in str(e)
                for err in ["timeout", "Timeout", "Connection", "Network"]
            ):
                logger.error(f"⚠️  网络错误 ({error_type}): {str(e)[:100]}")

                if retry_count < max_retries:
                    wait_time = min(60 * retry_count, 300)
                    logger.warning(
                        f"🔄 将在 {wait_time} 秒后重试 (第 {retry_count}/{max_retries} 次)"
                    )
                    import time

                    time.sleep(wait_time)
                    logger.info("🚀 重新启动机器人...")
                else:
                    logger.critical(f"❌ 达到最大重试次数 ({max_retries})，程序退出")
                    break
            else:
                # 其他错误，记录并退出
                logger.critical(f"❌ 严重错误 ({error_type}): {e}")
                import traceback

                logger.error(traceback.format_exc())
                break
