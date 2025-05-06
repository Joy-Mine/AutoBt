import backtrader as bt
from typing import Dict, Any

class SampleStrategy(bt.Strategy):
    """
    样例交易策略，用于演示如何使用生成的数据进行回测
    """
    
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('order_percentage', 0.95),
        ('stop_loss', 0.05),
    )
    
    def log(self, txt, dt=None):
        """记录日志"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
        
    def __init__(self):
        """初始化策略"""
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.fast_period
        )
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.slow_period
        )
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        self.order = None
        self.buy_price = None
        self.buy_comm = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}'
                )
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            else:  # Sell
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}')

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')

    def next(self):
        """每个数据点调用一次，实现交易逻辑"""
        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            if self.crossover > 0:  # Fast SMA > Slow SMA, buy signal
                self.log(f'BUY CREATE, {self.datas[0].close[0]:.2f}')
                size = int(self.broker.get_cash() / self.datas[0].close[0] * self.params.order_percentage)
                self.order = self.buy(size=size)
        else:
            # Sell signal or stop loss
            if self.crossover < 0: # Fast SMA < Slow SMA, sell signal
                self.log(f'SELL CREATE, {self.datas[0].close[0]:.2f}')
                self.order = self.sell(size=self.position.size)
            elif self.datas[0].close[0] < (self.buy_price * (1 - self.params.stop_loss)):
                self.log(f'STOP LOSS, {self.datas[0].close[0]:.2f}')
                self.order = self.sell(size=self.position.size)
