# !/usr/bin/env python
# coding: utf-8
import logging
import time
from decimal import Decimal as D, ROUND_UP, getcontext
from gate_api import (
    ApiClient,
    Configuration,
    FuturesApi,
    FuturesOrder,
    Transfer,
    WalletApi,
)
from gate_api.exceptions import GateApiException

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 直接填写你的API密钥（建议测试时使用测试网）
API_KEY = "3e8d2d1664611f23d7cd46d30b20043c"
API_SECRET = "a633008d65e6b77c095af45b0f82ff047ce5c2d02826f28d294b832f1335fd6f"
# 主网地址："https://api.gateio.ws/api/v4"
# 测试网地址："https://fx-api-testnet.gateio.ws/api/v4"
API_HOST = "https://api.gateio.ws/api/v4"


class SolPerpStrategy:
    def __init__(self, api_key, api_secret, host):
        """初始化策略，直接传入key和secret"""
        self.settle = "usdt"  # 结算货币
        self.contract = "SOL_USDT"  # SOL永续合约代码
        self.leverage = "100"  # 杠杆倍数

        # 直接配置API客户端
        self.config = Configuration(key=api_key, secret=api_secret, host=host)
        self.api_client = ApiClient(self.config)
        self.futures_api = FuturesApi(self.api_client)
        self.wallet_api = WalletApi(self.api_client)
        self.use_test = (
            host == "https://fx-api-testnet.gateio.ws/api/v4"
        )  # 判断是否为测试网
        self.init_strategy()

    def init_strategy(self):
        """初始化策略参数"""
        # 设置杠杆
        self.futures_api.update_position_leverage(
            self.settle, self.contract, self.leverage
        )
        logger.info(f"已设置{self.contract}杠杆为{self.leverage}x")

        # 确保账户有足够保证金
        self.ensure_margin()

    def get_last_price(self):
        """获取最新价格"""
        tickers = self.futures_api.list_futures_tickers(
            self.settle, contract=self.contract
        )
        return D(tickers[0].last)

    def calculate_order_size(self):
        """计算下单数量（不小于最小下单量）"""
        contract_info = self.futures_api.get_futures_contract(
            self.settle, self.contract
        )
        min_size = D(contract_info.order_size_min)
        # 实际策略可根据资金量调整，这里简化为最小下单量的2倍
        return max(min_size, min_size * D("2"))

    def ensure_margin(self):
        """确保保证金充足，测试网不自动转账"""
        last_price = self.get_last_price()
        contract_info = self.futures_api.get_futures_contract(
            self.settle, self.contract
        )
        order_size = self.calculate_order_size()

        # 计算所需保证金（加10%缓冲）
        getcontext().prec = 8
        getcontext().rounding = ROUND_UP
        margin = (
            order_size
            * last_price
            * D(contract_info.quanto_multiplier)
            / D(self.leverage)
            * D("1.1")
        )

        # 检查当前可用保证金
        try:
            account = self.futures_api.list_futures_accounts(self.settle)
            available = D(account.available)
            logger.info(f"当前可用保证金: {available} USDT, 所需保证金: {margin} USDT")

            # 主网环境下保证金不足时自动从现货账户转入
            if available < margin and not self.use_test:
                transfer = Transfer(
                    amount=str(margin - available),
                    currency=self.settle.upper(),
                    _from="spot",
                    to="futures",
                )
                self.wallet_api.transfer(transfer)
                logger.info(f"已转入{margin - available} USDT至合约账户")
            elif available < margin and self.use_test:
                logger.warning("测试网保证金不足，请手动在网页端转入")
        except GateApiException as e:
            logger.error(f"获取账户信息失败: {e.label} - {e.message}")

    def place_order(self, side):
        """下单 (side: 'long' 做多, 'short' 做空)"""
        # 先取消所有未成交订单
        self.futures_api.cancel_futures_orders(self.settle, self.contract)

        order_size = self.calculate_order_size()
        # 做空时数量为负数
        if side == "short":
            order_size = -order_size

        # 市价单 (IOC: 无法立即成交的部分取消)
        order = FuturesOrder(
            contract=self.contract,
            size=str(order_size),
            price="0",  # 0表示市价单
            tif="ioc",
        )

        try:
            response = self.futures_api.create_futures_order(self.settle, order)
            logger.info(f"下单成功: 订单ID {response.id}, 状态 {response.status}")

            # 检查成交情况
            if response.status == "filled":
                logger.info(f"完全成交: {order_size} 合约单位")
            elif response.status == "open":
                # 部分成交则取消剩余
                self.futures_api.cancel_futures_order(self.settle, str(response.id))
                logger.info("部分成交，已取消剩余订单")
            return response
        except GateApiException as e:
            logger.error(f"下单失败: {e.label} - {e.message}")
            return None

    def get_position(self):
        """获取当前仓位，处理size为None的情况"""
        try:
            position = self.futures_api.get_position(self.settle, self.contract)
            # 处理size为None的情况（无持仓时可能返回None）
            position_size = D(position.size) if position.size is not None else D(0)
            entry_price = (
                D(position.entry_price) if position.entry_price is not None else D(0)
            )
            pnl = self.get_unrealised_pnl()
            return {"size": position_size, "entry_price": entry_price, "pnl": pnl}
        except GateApiException as e:
            if e.label == "POSITION_NOT_FOUND":
                return {"size": D(0), "entry_price": D(0), "pnl": D(0)}
            else:
                logger.error(f"获取仓位失败: {e}")
                return None

    def get_unrealised_pnl(self):
        """从账户信息中获取未实现盈亏"""
        try:
            account = self.futures_api.list_futures_accounts(self.settle)
            return (
                D(account.unrealised_pnl)
                if hasattr(account, "unrealised_pnl") and account.unrealised_pnl
                else D(0)
            )
        except GateApiException as e:
            logger.error(f"获取账户盈亏失败: {e}")
            return D(0)


if __name__ == "__main__":
    # 初始化策略（直接传入key和secret）
    strategy = SolPerpStrategy(API_KEY, API_SECRET, API_HOST)

    # 先平掉现有仓位
    current_pos = strategy.get_position()
    if current_pos["size"] > 0:
        logger.info(f"平掉多单: {current_pos['size']}")
        strategy.place_order("short")
    elif current_pos["size"] < 0:
        logger.info(f"平掉空单: {current_pos['size']}")
        strategy.place_order("long")

    # 等待操作完成
    time.sleep(2)

    # 执行策略：这里示例做多，实际可根据指标判断
    logger.info("执行做多策略")
    strategy.place_order("long")

    # 打印当前仓位
    final_pos = strategy.get_position()
    logger.info(f"最终仓位: {final_pos['size']}, 持仓盈亏: {final_pos['pnl']} USDT")
