import backtrader as bt

class DualMovingAverageStrategy(bt.Strategy):
    """
    双均线策略
    """
    params = (
        ('short_window', 20),
        ('long_window', 50),
        ('order_percentage', 0.9),
        ('stop_loss', 0.1),
    )

    def __init__(self):
        self.short_ma = bt.indicators.SimpleMovingAverage(self.datas[0], period=self.params.short_window)
        self.long_ma = bt.indicators.SimpleMovingAverage(self.datas[0], period=self.params.long_window)
        self.crossover = bt.indicators.CrossOver(self.short_ma, self.long_ma)
        self.order = None
        self.buy_price = None

    def next(self):
        if self.order:
            return

        if not self.position:
            if self.crossover > 0:  # 短期均线上穿长期均线
                size = int(self.broker.get_cash() / self.datas[0].close[0] * self.params.order_percentage)
                self.order = self.buy(size=size)
        else:
            if self.crossover < 0 or self.datas[0].close[0] < self.buy_price * (1 - self.params.stop_loss):
                self.order = self.sell(size=self.position.size)