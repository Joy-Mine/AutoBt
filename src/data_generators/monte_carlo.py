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
        self.mu = config.get('monte_carlo', {}).get('mu', 0.0001)
        self.sigma = config.get('monte_carlo', {}).get('sigma', 0.01)
        
    def generate(self, base_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        使用几何布朗运动生成价格序列
        
        参数:
            base_data: 可选的基础数据，可以用于设定初始价格和学习参数
            
        返回:
            pandas DataFrame，包含OHLCV数据
        """
        dt = 1  # Time step (e.g., 1 day)
        
        start_price = 100.0
        if base_data is not None and not base_data.empty:
            start_price = base_data['close'].iloc[-1]
        
        # Generate prices
        prices = [start_price]
        for _ in range(1, self.length):
            drift = self.mu * dt
            shock = self.sigma * np.sqrt(dt) * np.random.normal()
            price = prices[-1] * np.exp(drift + shock)
            prices.append(price)
            
        # Create datetime index
        freq = self.config.get('frequency', 'D')
        if freq == 'D':
            time_delta = timedelta(days=1)
        elif freq == 'H':
            time_delta = timedelta(hours=1)
        elif freq == 'M':
            time_delta = timedelta(minutes=1)
        else:
            time_delta = timedelta(days=1) # Default to daily

        # Try to get a start date from base_data or use a default
        if base_data is not None and not base_data.empty and isinstance(base_data.index, pd.DatetimeIndex):
            start_date = base_data.index[-1] + time_delta
        else:
            start_date = datetime(2020, 1, 1) # Default start date
            
        dates = pd.to_datetime([start_date + i * time_delta for i in range(self.length)])
        
        df = pd.DataFrame(index=dates)
        df['open'] = prices
        df['high'] = prices # Simplification: O=H=L=C
        df['low'] = prices
        df['close'] = prices
        # Generate some random volume
        df['volume'] = np.random.randint(100, 1000, size=self.length)
        df.index.name = 'datetime'
        
        return df
