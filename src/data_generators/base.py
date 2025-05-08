import pandas as pd
import numpy as np
import backtrader as bt
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseDataGenerator(ABC):
    """模拟数据生成器的基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据生成器
        
        参数:
            config: 配置字典，包含数据生成的相关参数
        """
        self.config = config
        self.length = config.get('length', 1000)
        self.seed = config.get('seed', 42)
        np.random.seed(self.seed)
        
    @abstractmethod
    def generate(self, base_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        生成模拟数据
        
        参数:
            base_data: 可选的基础数据，可以在此基础上生成模拟数据
            
        返回:
            pandas DataFrame，包含OHLCV数据
        """
        pass
    
    def to_bt_feed(self, data: pd.DataFrame) -> bt.feeds.PandasData:
        """
        将生成的数据转换为backtrader可用的数据源
        
        参数:
            data: 生成的模拟数据, 期望列名包含 'datetime', 'open', 'high', 'low', 'close', 'volume'
            
        返回:
            backtrader的PandasData对象
        """
        # 确保datetime列是索引且为datetime对象
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'datetime' in data.columns:
                data['datetime'] = pd.to_datetime(data['datetime'])
                data.set_index('datetime', inplace=True)
            else:
                raise ValueError("DataFrame必须包含'datetime'列或一个DatetimeIndex.")

        # 重命名字段以匹配backtrader的期望
        # backtrader 默认列名: datetime, open, high, low, close, volume, openinterest
        # 如果DataFrame的列名不同, 在这里进行映射
        # 例如: data.rename(columns={'Date': 'datetime', 'OpenPrice': 'open'}, inplace=True)
        
        # 确保必要的列存在
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in data.columns:
                # 如果缺少关键列，可以用一些默认值填充或抛出错误
                # 这里用close价格填充缺失的OHL，用0填充volume
                if col in ['open', 'high', 'low'] and 'close' in data.columns:
                    data[col] = data['close']
                elif col == 'volume':
                    data[col] = 0
                else:
                    raise ValueError(f"DataFrame缺少必需的列: {col}")
        
        # 添加 openinterest 列（如果不存在），backtrader 需要它
        if 'openinterest' not in data.columns:
            data['openinterest'] = 0.0

        return bt.feeds.PandasData(dataname=data)
    
    def save_to_csv(self, data: pd.DataFrame, filename: str) -> None:
        """
        将生成的数据保存为CSV文件
        
        参数:
            data: 生成的模拟数据
            filename: 保存的文件名
        """
        data.to_csv(filename)
