"""
Gate.io 实盘交易机器人 - 带风险控制版本
使用 RSI + EMA 交叉策略 + 高级风险管理

风险控制特性：
1. 每次开仓不超过总资金的 10%
2. 总亏损达到 30% 时全部平仓止损
3. 斐波那契止盈：3%, 5%, 8%, 13%, 21%, 34%... 每次止盈一半仓位

⚠️ 警告：这是真实交易！会使用真实资金！
"""

from dotenv import load_dotenv
from typing import Dict, Any, List
import logging.config

import pandas as pd
from pyindicators import ema, rsi, crossover, crossunder

from investing_algorithm_framework import (
    TradingStrategy,
    DataSource,
    TimeUnit,
    DataType,
    PositionSize,
    create_app,
    DEFAULT_LOGGING_CONFIG,
    Context,
)

# 配置日志
logging.config.dictConfig(DEFAULT_LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


def generate_fibonacci_levels(max_level: int = 10) -> List[float]:
    """
    生成斐波那契数列作为止盈百分比
    返回: [3, 5, 8, 13, 21, 34, 55, 89, ...]
    """
    fib = [3, 5]  # 起始值
    for i in range(2, max_level):
        fib.append(fib[i - 1] + fib[i - 2])
    return [f / 100.0 for f in fib]  # 转换为小数


class RiskControlledStrategy(TradingStrategy):
    """
    带风险控制的 RSI + EMA 交叉策略
    """

    time_unit = TimeUnit.HOUR
    interval = 2
    symbols = ["LTC", "SOL"]

    # 风险控制参数
    INITIAL_CAPITAL = 20.0  # 初始资金 20 USDT
    MAX_POSITION_SIZE_PCT = 10.0  # 每次开仓最多 10%
    MAX_LOSS_PCT = 30.0  # 最大亏损 30%
    FIBONACCI_LEVELS = generate_fibonacci_levels(10)  # 斐波那契止盈点

    position_sizes = [
        PositionSize(
            symbol="LTC",
            percentage_of_portfolio=MAX_POSITION_SIZE_PCT,  # 10%
        ),
        PositionSize(
            symbol="SOL",
            percentage_of_portfolio=MAX_POSITION_SIZE_PCT,  # 10%
        ),
    ]

    def __init__(
        self,
        time_unit: TimeUnit,
        interval: int,
        market: str,
        rsi_time_frame: str,
        rsi_period: int,
        rsi_overbought_threshold: int,
        rsi_oversold_threshold: int,
        ema_time_frame: str,
        ema_short_period: int,
        ema_long_period: int,
        ema_cross_lookback_window: int = 10,
    ):
        self.rsi_time_frame = rsi_time_frame
        self.rsi_period = rsi_period
        self.rsi_result_column = f"rsi_{self.rsi_period}"
        self.rsi_overbought_threshold = rsi_overbought_threshold
        self.rsi_oversold_threshold = rsi_oversold_threshold
        self.ema_time_frame = ema_time_frame
        self.ema_short_result_column = f"ema_{ema_short_period}"
        self.ema_long_result_column = f"ema_{ema_long_period}"
        self.ema_crossunder_result_column = "ema_crossunder"
        self.ema_crossover_result_column = "ema_crossover"
        self.ema_short_period = ema_short_period
        self.ema_long_period = ema_long_period
        self.ema_cross_lookback_window = ema_cross_lookback_window

        # 风险控制状态
        self.initial_capital = self.INITIAL_CAPITAL
        self.stop_loss_triggered = False
        self.profit_taking_history = {}  # 记录每个交易的止盈历史

        # 配置数据源
        data_sources = []
        for symbol in self.symbols:
            full_symbol = f"{symbol}/USDT"
            # RSI 数据源
            data_sources.append(
                DataSource(
                    identifier=f"{symbol}_rsi_data",
                    data_type=DataType.OHLCV,
                    time_frame=self.rsi_time_frame,
                    market=market,
                    symbol=full_symbol,
                    pandas=True,
                    window_size=200,
                )
            )
            # EMA 数据源
            data_sources.append(
                DataSource(
                    identifier=f"{symbol}_ema_data",
                    data_type=DataType.OHLCV,
                    time_frame=self.ema_time_frame,
                    market=market,
                    symbol=full_symbol,
                    pandas=True,
                    window_size=200,
                )
            )

        super().__init__(
            data_sources=data_sources, time_unit=time_unit, interval=interval
        )

    def _check_stop_loss(self, context: Context) -> bool:
        """
        检查是否触发止损

        止损条件：所有持仓的净浮动亏损 >= 当前总资产的 30%

        例如：
        - 当前总资产：15 USDT
        - 仓位 A：-10 USDT（浮亏）
        - 仓位 B：+2 USDT（浮盈）
        - 净浮动亏损：-8 USDT
        - 亏损比例：|-8| / 15 = 53.3% >= 30% ✅ 触发止损
        """
        portfolio = context.get_portfolio()
        current_value = portfolio.get_net_size()  # 当前总资产

        # 获取所有未平仓交易,net_size（当前净资产）和 initial_balance + realized（初始资金 + 已平仓收益），差值即为未平仓收益（若框架的 net_size 计算逻辑包含未平仓浮盈）
        open_trades = current_value - (
            portfolio.get_initial_balance() + portfolio.get_realized()
        )

        if not open_trades:
            return False  # 没有持仓，无需止损

        # 计算所有持仓的净浮动盈亏
        total_floating_pnl = 0.0
        trade_details = []

        for trade in open_trades:
            # 使用 net_gain_absolute 获取浮动盈亏
            floating_pnl = trade.net_gain_absolute
            total_floating_pnl += floating_pnl
            trade_details.append(f"{trade.target_symbol}: ${floating_pnl:+.2f}")

        # 计算浮动亏损占当前总资产的比例
        if current_value > 0:
            floating_loss_pct = (
                (abs(total_floating_pnl) / current_value) * 100
                if total_floating_pnl < 0
                else 0
            )
        else:
            floating_loss_pct = 0

        # 记录当前状态
        logger.info(
            f"💼 Positions PnL: ${total_floating_pnl:+.2f} "
            f"({floating_loss_pct:.2f}% of ${current_value:.2f}) | "
            f"{', '.join(trade_details)}"
        )

        # 检查是否触发止损（仅当有亏损时）
        if total_floating_pnl < 0 and floating_loss_pct >= self.MAX_LOSS_PCT:
            logger.critical(
                f"🛑 STOP LOSS TRIGGERED! "
                f"Floating loss: ${total_floating_pnl:.2f} ({floating_loss_pct:.2f}%) "
                f"Threshold: {self.MAX_LOSS_PCT}% of current assets "
                f"Current assets: ${current_value:.2f}"
            )
            return True

        # 警告：接近止损线
        if total_floating_pnl < 0 and floating_loss_pct >= self.MAX_LOSS_PCT * 0.8:
            logger.warning(
                f"⚠️  WARNING: Approaching stop-loss! "
                f"Floating loss: {floating_loss_pct:.2f}% "
                f"(Threshold: {self.MAX_LOSS_PCT}%)"
            )

        return False

    def _check_fibonacci_profit_taking(self, context: Context, symbol: str):
        """
        检查斐波那契止盈点
        按照 3%, 5%, 8%, 13%, 21%... 逐步止盈一半仓位
        """
        # 获取该币种的持仓（使用 context 而不是 portfolio）
        try:
            position = context.get_position(symbol)
            if not position or position.amount <= 0:
                return

            # 获取该币种的交易
            portfolio = context.get_portfolio()
            trades = [
                t for t in portfolio.get_open_trades() if t.target_symbol == symbol
            ]

            if not trades:
                return

            for trade in trades:
                trade_id = trade.id

                # 初始化该交易的止盈历史
                if trade_id not in self.profit_taking_history:
                    self.profit_taking_history[trade_id] = {
                        "levels_taken": [],
                        "original_amount": trade.amount,
                    }

                # 计算当前盈利百分比
                # 从持仓获取最新价格
                current_price = trade.last_reported_price
                profit_pct = (current_price - trade.open_price) / trade.open_price

                # 检查每个斐波那契止盈点
                for i, fib_level in enumerate(self.FIBONACCI_LEVELS):
                    if (
                        profit_pct >= fib_level
                        and i
                        not in self.profit_taking_history[trade_id]["levels_taken"]
                    ):
                        # 触发止盈
                        remaining_amount = trade.available_amount
                        sell_amount = remaining_amount * 0.5  # 卖出一半

                        if sell_amount > 0:
                            logger.info(
                                f"💰 FIBONACCI PROFIT TAKING! "
                                f"{symbol} at {fib_level * 100:.0f}% profit "
                                f"(Level {i + 1}). Selling 50% ({sell_amount:.8f})"
                            )

                            # 执行部分平仓
                            context.create_limit_sell_order(
                                target_symbol=symbol,
                                amount=sell_amount,
                                price=current_price,
                            )

                            # 记录已触发的止盈点
                            self.profit_taking_history[trade_id]["levels_taken"].append(
                                i
                            )

                        break  # 每次只处理一个止盈点

        except Exception as e:
            logger.error(f"Error in profit taking for {symbol}: {e}")

    def _emergency_close_all_positions(self, context: Context):
        """
        紧急平仓所有持仓
        """
        portfolio = context.get_portfolio()
        open_trades = portfolio.get_open_trades()

        logger.critical(
            f"🚨 EMERGENCY CLOSE ALL POSITIONS! Closing {len(open_trades)} trades"
        )

        for trade in open_trades:
            try:
                symbol = trade.target_symbol
                current_price = trade.last_reported_price

                context.create_limit_sell_order(
                    target_symbol=symbol,
                    amount=trade.available_amount,
                    price=current_price,
                )

                logger.info(
                    f"✅ Closed position: {symbol} - {trade.available_amount:.8f} @ ${current_price:.2f}"
                )

            except Exception as e:
                logger.error(f"❌ Failed to close {trade.target_symbol}: {e}")

    def _prepare_indicators(self, rsi_data, ema_data):
        """计算技术指标"""
        ema_data = ema(
            ema_data,
            period=self.ema_short_period,
            source_column="Close",
            result_column=self.ema_short_result_column,
        )
        ema_data = ema(
            ema_data,
            period=self.ema_long_period,
            source_column="Close",
            result_column=self.ema_long_result_column,
        )
        ema_data = crossover(
            ema_data,
            first_column=self.ema_short_result_column,
            second_column=self.ema_long_result_column,
            result_column=self.ema_crossover_result_column,
        )
        ema_data = crossunder(
            ema_data,
            first_column=self.ema_short_result_column,
            second_column=self.ema_long_result_column,
            result_column=self.ema_crossunder_result_column,
        )
        rsi_data = rsi(
            rsi_data,
            period=self.rsi_period,
            source_column="Close",
            result_column=self.rsi_result_column,
        )
        return ema_data, rsi_data

    def _save_ohlcv_data(self, data: Dict[str, Any]):
        """
        保存 OHLCV 数据到文件
        每次策略运行时保存实时数据
        """
        import os
        from datetime import datetime

        # 创建数据目录
        data_dir = "examples/live_trading_data"
        os.makedirs(data_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for symbol in self.symbols:
            # 保存 RSI 和 EMA 数据（都是 OHLCV）
            for data_type in ["rsi_data", "ema_data"]:
                identifier = f"{symbol}_{data_type}"

                if identifier in data:
                    df = data[identifier]

                    if df is not None and not df.empty:
                        # 文件名格式：BTC_rsi_data_20251111_153000.csv
                        filename = f"{data_dir}/{symbol}_{data_type}_{timestamp}.csv"

                        # 保存到 CSV
                        df.to_csv(filename, index=True)
                        logger.info(f"💾 Saved {len(df)} rows to {filename}")

    def run_strategy(self, context: Context, data: Dict[str, Any]):
        """
        策略主逻辑 - 在每次运行时执行
        data 包含实时的 OHLCV 数据
        """
        # 0. 保存实时数据到文件
        try:
            self._save_ohlcv_data(data)
        except Exception as e:
            logger.error(f"Failed to save OHLCV data: {e}")

        # 1. 检查止损
        if self._check_stop_loss(context):
            if not self.stop_loss_triggered:
                self.stop_loss_triggered = True
                self._emergency_close_all_positions(context)
            return  # 止损后不再交易

        # 2. 检查斐波那契止盈
        for symbol in self.symbols:
            self._check_fibonacci_profit_taking(context, symbol)

        # 3. 打印当前状态
        portfolio = context.get_portfolio()
        current_value = portfolio.get_net_size()
        pnl_pct = ((current_value - self.initial_capital) / self.initial_capital) * 100

        logger.info(
            f"📊 Portfolio Status: ${current_value:.2f} "
            f"(PnL: {pnl_pct:+.2f}%) | "
            f"Unallocated: ${portfolio.get_unallocated():.2f}"
        )

        # 4. 执行正常的买卖信号逻辑
        super().run_strategy(context, data)

    def generate_buy_signals(self, data: Dict[str, Any]) -> Dict[str, pd.Series]:
        """生成买入信号"""
        signals = {}

        for symbol in self.symbols:
            ema_data_identifier = f"{symbol}_ema_data"
            rsi_data_identifier = f"{symbol}_rsi_data"
            ema_data, rsi_data = self._prepare_indicators(
                data[ema_data_identifier].copy(), data[rsi_data_identifier].copy()
            )

            ema_crossover_lookback = (
                ema_data[self.ema_crossover_result_column]
                .rolling(window=self.ema_cross_lookback_window)
                .max()
                .astype(bool)
            )

            rsi_oversold = (
                rsi_data[self.rsi_result_column] < self.rsi_oversold_threshold
            )

            buy_signal = rsi_oversold & ema_crossover_lookback
            buy_signals = buy_signal.fillna(False).astype(bool)
            signals[symbol] = buy_signals

            if buy_signals.iloc[-1]:
                logger.info(
                    f"🟢 BUY SIGNAL: {symbol} | "
                    f"RSI: {rsi_data[self.rsi_result_column].iloc[-1]:.2f} | "
                    f"Position size: {self.MAX_POSITION_SIZE_PCT}%"
                )

        return signals

    def generate_sell_signals(self, data: Dict[str, Any]) -> Dict[str, pd.Series]:
        """生成卖出信号"""
        signals = {}

        for symbol in self.symbols:
            ema_data_identifier = f"{symbol}_ema_data"
            rsi_data_identifier = f"{symbol}_rsi_data"
            ema_data, rsi_data = self._prepare_indicators(
                data[ema_data_identifier].copy(), data[rsi_data_identifier].copy()
            )

            ema_crossunder_lookback = (
                ema_data[self.ema_crossunder_result_column]
                .rolling(window=self.ema_cross_lookback_window)
                .max()
                .astype(bool)
            )

            rsi_overbought = (
                rsi_data[self.rsi_result_column] >= self.rsi_overbought_threshold
            )

            sell_signal = rsi_overbought & ema_crossunder_lookback
            sell_signal = sell_signal.fillna(False).astype(bool)
            signals[symbol] = sell_signal

            if sell_signal.iloc[-1]:
                logger.info(
                    f"🔴 SELL SIGNAL: {symbol} | "
                    f"RSI: {rsi_data[self.rsi_result_column].iloc[-1]:.2f}"
                )

        return signals


if __name__ == "__main__":
    import os

    # 设置独立的数据库，避免与回测冲突
    os.environ["DATABASE_NAME"] = "live-trading-database.sqlite3"

    print("=" * 80)
    print("⚠️  Gate.io 实盘交易机器人 - 风险控制版")
    print("=" * 80)
    print("\n💰 资金配置:")
    print(f"   初始资金: ${RiskControlledStrategy.INITIAL_CAPITAL} USDT")
    print(
        f"   每次开仓: {RiskControlledStrategy.MAX_POSITION_SIZE_PCT}% (最多 ${RiskControlledStrategy.INITIAL_CAPITAL * RiskControlledStrategy.MAX_POSITION_SIZE_PCT / 100:.2f})"
    )

    print("\n🛡️ 风险控制:")
    print(
        f"   止损线: -{RiskControlledStrategy.MAX_LOSS_PCT}% (${RiskControlledStrategy.INITIAL_CAPITAL * (1 - RiskControlledStrategy.MAX_LOSS_PCT / 100):.2f})"
    )
    print(f"   止盈策略: 斐波那契分批止盈")

    fib_levels = RiskControlledStrategy.FIBONACCI_LEVELS[:6]
    print(
        f"   止盈点: {', '.join([f'{l * 100:.0f}%' for l in fib_levels])}... (每次止盈50%)"
    )

    print("\n" + "=" * 80)
    print("\n请确认:")
    print("1. ✅ 已配置 Gate.io API 密钥")
    print("2. ✅ 账户有至少 $20 USDT")
    print("3. ✅ 理解风险控制机制")
    print("4. ✅ 准备好监控交易")

    # response = input("\n是否继续？(输入 'YES' 继续): ")

    # if response != "YES":
        # print("❌ 已取消")
        # exit()

    print("\n🚀 启动交易机器人...\n")

    app = create_app()

    app.add_strategy(
        RiskControlledStrategy(
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

    app.add_market(
        market="gateio",
        trading_symbol="USDT",
        initial_balance=20,  # 20 USDT
    )

    # 启动实盘交易
    # 注意：由于框架 bug，需要指定一个很大的迭代次数
    # 每次迭代间隔 1 秒，所以 86400 次 = 24 小时
    # 设置为 999999 次，约等于持续运行 11.5 天
    print("\n⏰ 机器人将持续运行...")
    print("   按 Ctrl+C 可以随时停止\n")

    try:
        app.run(number_of_iterations=999999)
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断，正在安全退出...")
        print("✅ 机器人已停止")
