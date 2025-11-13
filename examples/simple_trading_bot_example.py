from typing import Dict, Any
from datetime import datetime, timezone

import pandas as pd
from pyindicators import ema, rsi, crossover, crossunder

from investing_algorithm_framework import (
    TradingStrategy,
    DataSource,
    TimeUnit,
    DataType,
    PositionSize,
    create_app,
    RESOURCE_DIRECTORY,
    BacktestDateRange,
    BacktestReport,
)


class RSIEMACrossoverStrategy(TradingStrategy):
    time_unit = TimeUnit.HOUR
    interval = 2
    symbols = ["LTC", "ETH"]
    position_sizes = [
        PositionSize(symbol="LTC", percentage_of_portfolio=20.0),
        PositionSize(symbol="ETH", percentage_of_portfolio=20.0),
    ]

    def __init__(
        self,
        time_unit: TimeUnit,
        interval: int,
        market: str,
        rsi_time_frame: str,
        rsi_period: int,
        rsi_overbought_threshold,
        rsi_oversold_threshold,
        ema_time_frame,
        ema_short_period,
        ema_long_period,
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
                    window_size=800,
                    data_provider_identifier="ccxt",
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
                    window_size=800,
                    data_provider_identifier="ccxt",
                )
            )

        super().__init__(
            data_sources=data_sources, time_unit=time_unit, interval=interval
        )

        self.buy_signal_dates = {}
        self.sell_signal_dates = {}

        for symbol in self.symbols:
            self.buy_signal_dates[symbol] = []
            self.sell_signal_dates[symbol] = []

    def _prepare_indicators(self, rsi_data, ema_data):
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
        # Detect crossover (short EMA crosses above long EMA)
        ema_data = crossover(
            ema_data,
            first_column=self.ema_short_result_column,
            second_column=self.ema_long_result_column,
            result_column=self.ema_crossover_result_column,
        )
        # Detect crossunder (short EMA crosses below long EMA)
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

    def generate_buy_signals(self, data: Dict[str, Any]) -> Dict[str, pd.Series]:
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

            print(f"\n[{symbol}] Buy signals: {buy_signals.sum()} / {len(buy_signals)}")

        return signals

    def generate_sell_signals(self, data: Dict[str, Any]) -> Dict[str, pd.Series]:
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

            print(f"[{symbol}] Sell signals: {sell_signal.sum()} / {len(sell_signal)}")

        return signals


if __name__ == "__main__":
    app = create_app()
    app.add_strategy(
        RSIEMACrossoverStrategy(
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
    )

    backtest_range = BacktestDateRange(
        start_date=datetime(2025, 6, 1, tzinfo=timezone.utc),
        end_date=datetime(2025, 11, 1, tzinfo=timezone.utc),
    )

    backtest = app.run_backtest(
        backtest_date_range=backtest_range, initial_amount=1000, risk_free_rate=0.03
    )

    # Print results
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)

    metrics = backtest.get_backtest_metrics(backtest_range)

    print(f"\n📊 Performance:")
    print(
        f"   Total Return: {getattr(metrics, 'total_growth_percentage', 0) * 100:.2f}%"
    )
    print(f"   Profit/Loss: ${getattr(metrics, 'total_net_gain', 0):.2f}")
    print(f"   Sharpe Ratio: {getattr(metrics, 'sharpe_ratio', 0):.4f}")
    print(f"   Win Rate: {getattr(metrics, 'win_rate', 0) * 100:.2f}%")

    print(f"\n🔄 Trades: {getattr(metrics, 'number_of_trades', 0)} total")
    print(f"   Closed: {getattr(metrics, 'number_of_trades_closed', 0)}")
    print(f"   Open: {getattr(metrics, 'number_of_trades_open', 0)}")

    # Show detailed trade info
    summary_dict = backtest.to_dict()
    if summary_dict.get("trades"):
        print(f"\n💼 Trade Details:")
        for i, trade in enumerate(summary_dict["trades"], 1):
            print(f"\n  Trade #{i}:")
            print(f"    Symbol: {trade['target_symbol']}")
            print(f"    Status: {trade['status']}")
            print(f"    Amount: {trade['amount']:.8f}")
            print(f"    Cost: ${trade['cost']:.2f}")
            print(f"    Open Price: ${trade['open_price']:.2f}")
            print(f"    Last Price: ${trade['last_reported_price']:.2f}")
            print(f"    Opened: {trade['opened_at']}")
            if trade["closed_at"]:
                print(f"    Closed: {trade['closed_at']}")
            print(f"    Net Gain: ${trade['net_gain']:.2f}")

    print("=" * 80)
