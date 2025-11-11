"""
Gate.io 实盘交易机器人
使用 RSI + EMA 交叉策略进行实时交易

⚠️ 警告：这是真实交易！会使用真实资金！
在运行前请确保：
1. 已在 .env 文件中配置 Gate.io API 密钥
2. 理解策略逻辑和风险
3. 从小资金开始测试
"""

from dotenv import load_dotenv
from typing import Dict, Any
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
    Context
)

# 配置日志
logging.config.dictConfig(DEFAULT_LOGGING_CONFIG)

# 加载环境变量（API 密钥）
load_dotenv()


class RSIEMACrossoverLiveStrategy(TradingStrategy):
    """
    RSI + EMA 交叉策略（实盘版本）
    
    买入条件：RSI < 35 且 短期EMA上穿长期EMA
    卖出条件：RSI >= 65 且 短期EMA下穿长期EMA
    """
    
    time_unit = TimeUnit.HOUR
    interval = 2  # 每2小时运行一次
    symbols = ["BTC", "ETH"]
    
    position_sizes = [
        PositionSize(symbol="BTC", percentage_of_portfolio=20.0),
        PositionSize(symbol="ETH", percentage_of_portfolio=20.0)
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
        ema_cross_lookback_window: int = 10
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
        
        # 配置数据源
        data_sources = []
        for symbol in self.symbols:
            full_symbol = f"{symbol}/USDT"
            data_sources.append(
                DataSource(
                    identifier=f"{symbol}_rsi_data",
                    data_type=DataType.OHLCV,
                    time_frame=self.rsi_time_frame,
                    market=market,
                    symbol=full_symbol,
                    pandas=True,
                    window_size=200  # 实盘只需要较少的历史数据
                )
            )
            data_sources.append(
                DataSource(
                    identifier=f"{symbol}_ema_data",
                    data_type=DataType.OHLCV,
                    time_frame=self.ema_time_frame,
                    market=market,
                    symbol=full_symbol,
                    pandas=True,
                    window_size=200
                )
            )

        super().__init__(
            data_sources=data_sources, 
            time_unit=time_unit, 
            interval=interval
        )

    def _prepare_indicators(self, rsi_data, ema_data):
        """计算技术指标"""
        ema_data = ema(
            ema_data,
            period=self.ema_short_period,
            source_column="Close",
            result_column=self.ema_short_result_column
        )
        ema_data = ema(
            ema_data,
            period=self.ema_long_period,
            source_column="Close",
            result_column=self.ema_long_result_column
        )
        ema_data = crossover(
            ema_data,
            first_column=self.ema_short_result_column,
            second_column=self.ema_long_result_column,
            result_column=self.ema_crossover_result_column
        )
        ema_data = crossunder(
            ema_data,
            first_column=self.ema_short_result_column,
            second_column=self.ema_long_result_column,
            result_column=self.ema_crossunder_result_column
        )
        rsi_data = rsi(
            rsi_data,
            period=self.rsi_period,
            source_column="Close",
            result_column=self.rsi_result_column
        )
        return ema_data, rsi_data

    def generate_buy_signals(self, data: Dict[str, Any]) -> Dict[str, pd.Series]:
        """生成买入信号"""
        signals = {}

        for symbol in self.symbols:
            ema_data_identifier = f"{symbol}_ema_data"
            rsi_data_identifier = f"{symbol}_rsi_data"
            ema_data, rsi_data = self._prepare_indicators(
                data[ema_data_identifier].copy(),
                data[rsi_data_identifier].copy()
            )

            ema_crossover_lookback = ema_data[
                self.ema_crossover_result_column
            ].rolling(window=self.ema_cross_lookback_window).max().astype(bool)

            rsi_oversold = rsi_data[self.rsi_result_column] < self.rsi_oversold_threshold

            buy_signal = rsi_oversold & ema_crossover_lookback
            buy_signals = buy_signal.fillna(False).astype(bool)
            signals[symbol] = buy_signals
            
            # 实盘日志
            if buy_signals.iloc[-1]:  # 如果最新数据点有买入信号
                logging.info(f"🟢 BUY SIGNAL for {symbol}! RSI: {rsi_data[self.rsi_result_column].iloc[-1]:.2f}")

        return signals

    def generate_sell_signals(self, data: Dict[str, Any]) -> Dict[str, pd.Series]:
        """生成卖出信号"""
        signals = {}
        
        for symbol in self.symbols:
            ema_data_identifier = f"{symbol}_ema_data"
            rsi_data_identifier = f"{symbol}_rsi_data"
            ema_data, rsi_data = self._prepare_indicators(
                data[ema_data_identifier].copy(),
                data[rsi_data_identifier].copy()
            )

            ema_crossunder_lookback = ema_data[
                self.ema_crossunder_result_column
            ].rolling(window=self.ema_cross_lookback_window).max().astype(bool)

            rsi_overbought = rsi_data[self.rsi_result_column] >= self.rsi_overbought_threshold

            sell_signal = rsi_overbought & ema_crossunder_lookback
            sell_signal = sell_signal.fillna(False).astype(bool)
            signals[symbol] = sell_signal
            
            # 实盘日志
            if sell_signal.iloc[-1]:  # 如果最新数据点有卖出信号
                logging.info(f"🔴 SELL SIGNAL for {symbol}! RSI: {rsi_data[self.rsi_result_column].iloc[-1]:.2f}")

        return signals


if __name__ == "__main__":
    print("="*80)
    print("⚠️  Gate.io 实盘交易机器人")
    print("="*80)
    print("\n请确认以下事项：")
    print("1. ✅ 已在 .env 文件中配置 GATEIO_API_KEY 和 GATEIO_SECRET_KEY")
    print("2. ✅ 理解策略逻辑和交易风险")
    print("3. ✅ 账户中有足够的 USDT 余额")
    print("4. ✅ 从小资金开始测试")
    print("\n" + "="*80)
    
    # 等待用户确认
    response = input("\n是否继续运行实盘交易？(输入 'YES' 继续): ")
    
    if response != "YES":
        print("❌ 已取消运行")
        exit()
    
    print("\n🚀 启动实盘交易机器人...\n")
    
    # 创建应用
    app = create_app()
    
    # 添加策略
    app.add_strategy(
        RSIEMACrossoverLiveStrategy(
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
            ema_cross_lookback_window=10
        )
    )

    # 配置 Gate.io 市场
    # API 密钥会从 .env 文件自动读取
    app.add_market(
        market="gateio",
        trading_symbol="USDT",
        initial_balance=1000  # 初始资金（仅用于记录）
    )

    # 🚀 启动实盘交易！
    # 这会持续运行，每2小时检查一次信号并执行交易
    app.run()
