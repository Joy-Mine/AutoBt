import backtrader as bt
import numpy as np
from typing import Dict, Any

class MeanReversionStrategy(bt.Strategy):
    """
    均值回归策略
    
    该策略基于价格偏离均值的程度来交易，当价格显著高于均值时卖出，
    当价格显著低于均值时买入，适合在震荡市场中使用。
    """
    
    params = (
        ('lookback', 20),        # 均值计算的回看周期
        ('entry_std', 2.0),      # 入场标准差倍数
        ('exit_std', 0.5),       # 出场标准差倍数
        ('order_percentage', 0.95), # 下单资金比例
        ('stop_loss', 0.05),     # 止损比例
    )
    
    def log(self, txt, dt=None):
        """记录日志"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
        
    def __init__(self):
        """初始化策略"""
        # 计算移动平均线和标准差
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.lookback
        )
        
        # 使用自定义指标计算标准差
        self.data_close = self.datas[0].close
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        
        # 跟踪当前持仓状态
        self.in_position = False
        
        # 计算布林带
        self.bbands = bt.indicators.BollingerBands(
            self.datas[0].close, period=self.params.lookback
        )
        
        # 价格与均值的偏离度
        # 布林带的标准差是top和mid之间的差除以2
        std_dev = (self.bbands.lines.top - self.bbands.lines.mid) / 2.0
        self.deviation = (self.datas[0].close - self.sma) / std_dev

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
                self.in_position = True
            else:  # 卖出
                self.log(f'卖出执行, 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 手续费: {order.executed.comm:.2f}')
                self.in_position = False

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

        # 计算当前价格与均值的偏离度
        current_deviation = self.deviation[0]
        
        # 如果没有持仓
        if not self.position:
            # 当价格显著低于均值时买入（负偏离度大于入场阈值）
            if current_deviation < -self.params.entry_std:
                size = int(self.broker.get_cash() / self.datas[0].close[0] * self.params.order_percentage)
                if size > 0:
                    self.log(f'买入信号 (偏离度: {current_deviation:.2f}), 价格: {self.datas[0].close[0]:.2f}')
                    self.order = self.buy(size=size)
                    self.buy_price = self.datas[0].close[0]
        else:
            # 计算当前亏损比例
            current_price = self.datas[0].close[0]
            if self.buy_price is None:  # 安全检查
                self.buy_price = self.position.price
            
            loss_pct = (self.buy_price - current_price) / self.buy_price
            
            # 当价格回归到均值附近或超过均值时卖出
            if current_deviation > self.params.exit_std:
                self.log(f'卖出信号 (偏离度: {current_deviation:.2f}), 价格: {current_price:.2f}')
                self.order = self.sell(size=self.position.size)
            # 止损
            elif loss_pct >= self.params.stop_loss:
                self.log(f'止损, 价格: {current_price:.2f}, 止损比例: {loss_pct:.2%}')
                self.order = self.sell(size=self.position.size) 