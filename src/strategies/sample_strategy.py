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
        # 未来实现: 策略初始化
        pass
    
    def next(self):
        """每个数据点调用一次，实现交易逻辑"""
        # 未来实现: 交易逻辑
        pass
