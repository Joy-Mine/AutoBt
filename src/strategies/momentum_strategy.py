import backtrader as bt
import numpy as np
from typing import Dict, Any

class MomentumStrategy(bt.Strategy):
    """
    动量策略
    
    该策略基于价格的动量指标进行交易，当动量指标上穿0线时买入，
    当动量指标下穿0线时卖出，适合在趋势明显的市场中使用。
    """
    
    params = (
        ('momentum_period', 30),   # 动量计算周期
        ('signal_period', 9),      # 信号平滑周期
        ('order_percentage', 0.95), # 下单资金比例
        ('stop_loss', 0.05),       # 止损比例
        ('trailing_stop', 0.02),   # 跟踪止损比例
    )
    
    def log(self, txt, dt=None):
        """记录日志"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
        
    def __init__(self):
        """初始化策略"""
        # 计算动量指标 (ROC - Rate of Change)
        self.roc = bt.indicators.ROC(self.datas[0], period=self.params.momentum_period)
        
        # 平滑动量指标
        self.signal = bt.indicators.EMA(self.roc, period=self.params.signal_period)
        
        # 动量指标的交叉信号
        self.crossover = bt.indicators.CrossOver(self.roc, 0)
        
        # 交易相关变量
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        
        # 跟踪止损价格
        self.trailing_stop_price = 0
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/已接受 - 无需操作
            return

        # 检查订单是否已完成
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'买入执行, 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}'
                )
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
                # 设置初始跟踪止损价格
                self.trailing_stop_price = order.executed.price * (1 - self.params.stop_loss)
            else:  # 卖出
                self.log(f'卖出执行, 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                self.trailing_stop_price = 0  # 重置跟踪止损价格

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'交易利润, 毛利: {trade.pnl:.2f}, 净利: {trade.pnlcomm:.2f}')

    def next(self):
        """每个数据点调用一次，实现交易逻辑"""
        # 如果有未完成的订单，不进行新的操作
        if self.order:
            return

        # 当前价格
        current_price = self.datas[0].close[0]
        
        # 如果没有持仓
        if not self.position:
            # 当动量指标上穿0线时买入
            if self.crossover > 0 and self.signal > 0:
                size = int(self.broker.get_cash() / current_price * self.params.order_percentage)
                if size > 0:
                    self.log(f'买入信号 (动量: {self.roc[0]:.4f}), 价格: {current_price:.2f}')
                    self.order = self.buy(size=size)
                    self.buy_price = current_price
        else:
            # 更新跟踪止损价格
            if current_price > self.buy_price:
                new_stop = current_price * (1 - self.params.trailing_stop)
                if new_stop > self.trailing_stop_price:
                    self.trailing_stop_price = new_stop
                    self.log(f'更新跟踪止损价格: {self.trailing_stop_price:.2f}')
            
            # 计算当前亏损比例
            if self.buy_price is None:  # 安全检查
                self.buy_price = self.position.price
            
            # 卖出条件
            # 1. 动量指标下穿0线
            if self.crossover < 0 and self.signal < 0:
                self.log(f'卖出信号 (动量: {self.roc[0]:.4f}), 价格: {current_price:.2f}')
                self.order = self.sell(size=self.position.size)
            # 2. 价格触及跟踪止损
            elif current_price <= self.trailing_stop_price:
                self.log(f'跟踪止损, 价格: {current_price:.2f}, 止损价格: {self.trailing_stop_price:.2f}')
                self.order = self.sell(size=self.position.size)
            # 3. 固定止损
            elif current_price < self.buy_price * (1 - self.params.stop_loss):
                self.log(f'固定止损, 价格: {current_price:.2f}, 止损比例: {self.params.stop_loss:.2%}')
                self.order = self.sell(size=self.position.size) 