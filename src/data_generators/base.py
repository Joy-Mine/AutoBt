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
            data: 生成的模拟数据
            
        返回:
            backtrader的PandasData对象
        """
        pass
    
    def save_to_csv(self, data: pd.DataFrame, filename: str) -> None:
        """
        将生成的数据保存为CSV文件
        
        参数:
            data: 生成的模拟数据
            filename: 保存的文件名
        """
        pass
