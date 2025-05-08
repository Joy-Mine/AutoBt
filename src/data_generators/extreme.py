import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .base import BaseDataGenerator

class ExtremeEventGenerator(BaseDataGenerator):
    """
    极端情况模拟数据生成器，可以模拟市场崩盘、急剧上涨等极端情况
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化极端情况模拟数据生成器
        
        参数:
            config: 配置字典，包含极端情况模拟的相关参数
        """
        super().__init__(config)
        extreme_config = config.get('extreme', {})
        self.crash_probability = extreme_config.get('crash_probability', 0.01)
        self.crash_intensity = extreme_config.get('crash_intensity', 0.1)
        
    def generate(self, base_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        生成包含极端事件的价格序列
        
        参数:
            base_data: 可选的基础数据，在此基础上添加极端事件。如果提供，将使用其最后的价格作为起点。
                     如果未提供，将从一个默认价格开始（例如100）。
            
        返回:
            pandas DataFrame，包含OHLCV数据
        """
        # Start with a simple random walk for base prices if no base_data
        if base_data is None or base_data.empty:
            prices = [100.0] # Default starting price
            for _ in range(1, self.length):
                # Small random daily changes
                change = np.random.normal(0, 0.01) # mu=0, sigma=0.01
                prices.append(prices[-1] * (1 + change))
        else:
            # Use the provided base_data as a starting point
            # For simplicity, we'll just use the close prices and append to them
            # A more sophisticated approach might involve learning parameters from base_data
            # or overlaying extreme events onto a copy of base_data.
            # Here, we'll generate new data of `self.length` starting from base_data's end.
            prices = [base_data['close'].iloc[-1]]
            for _ in range(1, self.length):
                change = np.random.normal(0, 0.01)
                prices.append(prices[-1] * (1 + change))

        # Introduce extreme events
        for i in range(self.length):
            if np.random.rand() < self.crash_probability:
                # Simulate a crash (sudden drop)
                prices[i] *= (1 - self.crash_intensity * np.random.rand()) # Intensity varies a bit
            elif np.random.rand() < self.config.get('extreme', {}).get('surge_probability', 0.01): # Example for surge
                # Simulate a surge (sudden jump)
                surge_intensity = self.config.get('extreme', {}).get('surge_intensity', 0.1)
                prices[i] *= (1 + surge_intensity * np.random.rand())
        
        # Ensure prices are positive
        prices = [max(0.01, p) for p in prices] 

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

        if base_data is not None and not base_data.empty and isinstance(base_data.index, pd.DatetimeIndex):
            start_date = base_data.index[-1] + time_delta
        else:
            start_date = datetime(2020, 1, 1) # Default start date
            
        dates = pd.to_datetime([start_date + i * time_delta for i in range(self.length)])
        
        df = pd.DataFrame(index=dates)
        df['open'] = prices
        df['high'] = [p * (1 + np.random.uniform(0, 0.02)) for p in prices] # Add some noise for H/L
        df['low'] = [p * (1 - np.random.uniform(0, 0.02)) for p in prices]
        df['close'] = prices
        # Ensure low <= open/close <= high
        df['high'] = df[['high', 'open', 'close']].max(axis=1)
        df['low'] = df[['low', 'open', 'close']].min(axis=1)

        df['volume'] = np.random.randint(100, 10000, size=self.length)
        df.index.name = 'datetime'
        
        return df
