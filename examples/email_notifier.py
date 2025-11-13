"""
邮件通知模块
用于发送交易通知邮件
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import ssl
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self, sender_email: str, auth_code: str, receiver_email: str):
        """
        初始化邮件通知器
        
        Args:
            sender_email: 发件人邮箱（QQ邮箱）
            auth_code: QQ邮箱授权码
            receiver_email: 收件人邮箱
        """
        self.sender_email = sender_email
        self.auth_code = auth_code
        self.receiver_email = receiver_email
        self.smtp_server = "smtp.qq.com"
        self.smtp_port = 465
    
    def send_email(self, subject: str, content: str, html: bool = False) -> bool:
        """
        发送邮件
        
        Args:
            subject: 邮件主题
            content: 邮件内容
            html: 是否为 HTML 格式
            
        Returns:
            bool: 是否发送成功
        """
        try:
            context = ssl.create_default_context()
            
            if html:
                message = MIMEMultipart('alternative')
                text_part = MIMEText(content, 'plain', 'utf-8')
                html_part = MIMEText(content, 'html', 'utf-8')
                message.attach(text_part)
                message.attach(html_part)
            else:
                message = MIMEText(content, 'plain', 'utf-8')
            
            message['From'] = self.sender_email
            message['To'] = self.receiver_email
            message['Subject'] = Header(subject, 'utf-8')
            
            with smtplib.SMTP_SSL(
                self.smtp_server, 
                self.smtp_port, 
                context=context
            ) as server:
                server.login(self.sender_email, self.auth_code)
                server.sendmail(
                    self.sender_email, 
                    self.receiver_email, 
                    message.as_string()
                )
            
            logger.info(f"📧 邮件发送成功: {subject}")
            return True
            
        except Exception as e:
            # QQ邮箱有时会返回 -1 错误但实际发送成功
            if '-1' in str(e):
                logger.info(f"📧 邮件发送成功: {subject}")
                return True
            
            logger.error(f"📧 邮件发送失败: {e}")
            return False
    
    def send_buy_notification(
        self, 
        symbol: str, 
        amount: float, 
        price: float, 
        cost: float,
        portfolio_value: float,
        reason: str = ""
    ) -> bool:
        """
        发送买入通知
        
        Args:
            symbol: 币种符号
            amount: 买入数量
            price: 买入价格
            cost: 买入成本
            portfolio_value: 当前总资产
            reason: 买入原因
        """
        subject = f"🟢 买入通知 - {symbol}"
        
        content = f"""
交易机器人买入通知
{'='*50}

📊 交易信息:
  币种: {symbol}
  数量: {amount:.8f}
  价格: ${price:,.2f}
  成本: ${cost:.2f}

💰 账户信息:
  当前总资产: ${portfolio_value:,.2f}

📝 买入原因:
  {reason if reason else '策略信号触发'}

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*50}
此邮件由交易机器人自动发送
"""
        
        return self.send_email(subject, content)
    
    def send_sell_notification(
        self, 
        symbol: str, 
        amount: float, 
        price: float, 
        revenue: float,
        profit: float,
        profit_pct: float,
        portfolio_value: float,
        reason: str = ""
    ) -> bool:
        """
        发送卖出通知
        
        Args:
            symbol: 币种符号
            amount: 卖出数量
            price: 卖出价格
            revenue: 卖出收入
            profit: 盈亏金额
            profit_pct: 盈亏百分比
            portfolio_value: 当前总资产
            reason: 卖出原因
        """
        profit_emoji = "📈" if profit >= 0 else "📉"
        subject = f"🔴 卖出通知 - {symbol} ({profit_emoji} {profit_pct:+.2f}%)"
        
        content = f"""
交易机器人卖出通知
{'='*50}

📊 交易信息:
  币种: {symbol}
  数量: {amount:.8f}
  价格: ${price:,.2f}
  收入: ${revenue:.2f}

💵 盈亏情况:
  盈亏金额: ${profit:+,.2f}
  盈亏比例: {profit_pct:+.2f}%
  {profit_emoji} {'盈利' if profit >= 0 else '亏损'}

💰 账户信息:
  当前总资产: ${portfolio_value:,.2f}

📝 卖出原因:
  {reason if reason else '策略信号触发'}

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*50}
此邮件由交易机器人自动发送
"""
        
        return self.send_email(subject, content)
    
    def send_stop_loss_notification(
        self,
        total_loss: float,
        loss_pct: float,
        portfolio_value: float,
        positions: list
    ) -> bool:
        """
        发送止损通知
        
        Args:
            total_loss: 总亏损金额
            loss_pct: 亏损百分比
            portfolio_value: 当前总资产
            positions: 持仓列表
        """
        subject = f"🛑 止损警告 - 亏损 {loss_pct:.2f}%"
        
        positions_text = "\n".join([
            f"  {pos['symbol']}: ${pos['pnl']:+.2f}" 
            for pos in positions
        ])
        
        content = f"""
⚠️ 交易机器人止损通知 ⚠️
{'='*50}

🛑 止损触发:
  总亏损: ${total_loss:,.2f}
  亏损比例: {loss_pct:.2f}%
  
💰 当前资产:
  总资产: ${portfolio_value:,.2f}

📊 持仓情况:
{positions_text}

⚡ 已执行操作:
  ✅ 已平掉所有持仓
  ✅ 已停止新的交易

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*50}
请及时检查账户状态！
此邮件由交易机器人自动发送
"""
        
        return self.send_email(subject, content)
    
    def send_profit_taking_notification(
        self,
        symbol: str,
        level: int,
        profit_pct: float,
        amount_sold: float,
        price: float,
        portfolio_value: float
    ) -> bool:
        """
        发送止盈通知
        
        Args:
            symbol: 币种符号
            level: 止盈级别
            profit_pct: 盈利百分比
            amount_sold: 卖出数量
            price: 卖出价格
            portfolio_value: 当前总资产
        """
        subject = f"💰 止盈通知 - {symbol} (Level {level})"
        
        content = f"""
交易机器人止盈通知
{'='*50}

💰 止盈信息:
  币种: {symbol}
  级别: Level {level}
  盈利: {profit_pct:.2f}%

📊 交易详情:
  卖出数量: {amount_sold:.8f}
  卖出价格: ${price:,.2f}
  卖出比例: 50% (剩余 50%)

💵 账户信息:
  当前总资产: ${portfolio_value:,.2f}

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*50}
此邮件由交易机器人自动发送
"""
        
        return self.send_email(subject, content)
    
    def send_daily_summary(
        self,
        portfolio_value: float,
        initial_value: float,
        total_pnl: float,
        total_pnl_pct: float,
        open_positions: list,
        trades_today: int
    ) -> bool:
        """
        发送每日总结
        
        Args:
            portfolio_value: 当前总资产
            initial_value: 初始资产
            total_pnl: 总盈亏
            total_pnl_pct: 总盈亏百分比
            open_positions: 持仓列表
            trades_today: 今日交易次数
        """
        subject = f"📊 每日总结 - {datetime.now().strftime('%Y-%m-%d')}"
        
        positions_text = "\n".join([
            f"  {pos['symbol']}: {pos['amount']:.8f} (${pos['value']:.2f}, PnL: ${pos['pnl']:+.2f})"
            for pos in open_positions
        ]) if open_positions else "  无持仓"
        
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        
        content = f"""
交易机器人每日总结
{'='*50}

💰 资产概况:
  当前总资产: ${portfolio_value:,.2f}
  初始资产: ${initial_value:,.2f}
  总盈亏: ${total_pnl:+,.2f}
  盈亏比例: {total_pnl_pct:+.2f}% {pnl_emoji}

📊 持仓情况:
{positions_text}

📈 交易统计:
  今日交易: {trades_today} 笔

⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*50}
此邮件由交易机器人自动发送
"""
        
        return self.send_email(subject, content)
