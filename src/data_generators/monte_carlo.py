import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .base import BaseDataGenerator

class MonteCarloGenerator(BaseDataGenerator):
    """
    蒙特卡洛模拟数据生成器，使用几何布朗运动生成价格序列
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化蒙特卡洛模拟数据生成器
        
        参数:
            config: 配置字典，包含蒙特卡洛模拟的相关参数
        """
        super().__init__(config)
        # 从配置中获取monte_carlo参数
        monte_carlo_config = config.get('monte_carlo', {})
        self.mu = monte_carlo_config.get('mu', 0.0001)  # 漂移率
        self.sigma = monte_carlo_config.get('sigma', 0.01)  # 波动率
        
    def generate(self, base_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        使用几何布朗运动生成价格序列
        
        参数:
            base_data: 可选的基础数据，可以用于设定初始价格和学习参数
            
        返回:
            pandas DataFrame，包含OHLCV数据
        """
        dt = 1  # 时间步长
        
        # 设置起始价格
        start_price = 100.0
        if base_data is not None and not base_data.empty:
            start_price = base_data['close'].iloc[-1]
        
        # 生成收盘价序列
        prices = [start_price]
        for _ in range(1, self.length):
            drift = self.mu * dt
            shock = self.sigma * np.sqrt(dt) * np.random.normal()
            price = prices[-1] * np.exp(drift + shock)
            prices.append(price)
            
        # 创建日期索引
        freq = self.config.get('frequency', 'D')
        if freq == 'D':
            time_delta = timedelta(days=1)
            freq_str = 'B'  # 使用工作日
        elif freq == 'H':
            time_delta = timedelta(hours=1)
            freq_str = 'H'
        elif freq == 'M':
            time_delta = timedelta(minutes=1)
            freq_str = 'T'  # 分钟用T表示
        else:
            time_delta = timedelta(days=1)  # 默认为日线
            freq_str = 'B'

        # 设置起始日期
        if base_data is not None and not base_data.empty and isinstance(base_data.index, pd.DatetimeIndex):
            start_date = base_data.index[-1] + time_delta
        else:
            start_date = datetime(2020, 1, 1)  # 默认起始日期
        
        # 使用pandas的date_range生成更好的日期序列
        dates = pd.date_range(start=start_date, periods=self.length, freq=freq_str)
        
        # 创建包含OHLCV数据的DataFrame
        df = pd.DataFrame(index=dates)
        
        # 生成开盘价、最高价、最低价
        opens = []
        highs = []
        lows = []
        
        # 第一天的开盘价等于起始价格
        opens.append(prices[0])
        
        # 为后续日期生成开盘价（基于前一天的收盘价，加上合理的隔夜波动）
        for i in range(1, len(prices)):
            # 开盘价基于前一天收盘价有小幅波动，范围合理化
            gap_factor = self.sigma / 2  # 隔夜波动幅度取决于总体波动率
            opens.append(prices[i-1] * (1 + np.random.uniform(-gap_factor, gap_factor)))
        
        # 生成最高价和最低价
        for i in range(len(prices)):
            # 计算当天价格变动范围，基于总体波动率
            price_range = abs(opens[i] - prices[i])
            daily_volatility = max(price_range, prices[i] * self.sigma)
            
            # 最高价和最低价
            if prices[i] >= opens[i]:  # 上涨日
                high = prices[i] + np.random.uniform(0, daily_volatility)
                low = opens[i] - np.random.uniform(0, daily_volatility / 2)
            else:  # 下跌日
                high = opens[i] + np.random.uniform(0, daily_volatility / 2)
                low = prices[i] - np.random.uniform(0, daily_volatility)
            
            # 确保最低价大于0且关系正确: high > open,close > low
            low = max(low, 0.01)
            high = max(high, opens[i], prices[i])
            low = min(low, opens[i], prices[i])
            
            highs.append(high)
            lows.append(low)
        
        df['open'] = opens
        df['high'] = highs
        df['low'] = lows
        df['close'] = prices
        
        # 生成更真实的成交量，模拟真实的成交量特性（自相关性和与价格变动的关系）
        base_volume = np.random.lognormal(mean=8, sigma=1, size=self.length)  # 更真实的分布
        
        # 添加自相关性
        volume = np.zeros(self.length)
        volume[0] = base_volume[0]
        for i in range(1, self.length):
            # 新成交量有60%来自前一天的成交量
            volume[i] = 0.6 * volume[i-1] + 0.4 * base_volume[i]
        
        # 价格变动大的日子，成交量往往更大
        price_changes = np.zeros(self.length)
        price_changes[1:] = np.abs(np.diff(prices) / prices[:-1])
        
        # 更真实的成交量与价格关系 - 大涨大跌都有大成交量
        volume_factor = 1 + 5 * price_changes**0.5  # 价格变动越大，成交量越大，但非线性增长
        
        df['volume'] = (volume * volume_factor).astype(int)
        df.index.name = 'datetime'
        
        return df
