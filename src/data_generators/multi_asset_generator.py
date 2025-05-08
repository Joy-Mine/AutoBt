import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .base import BaseDataGenerator

class MultiAssetGenerator(BaseDataGenerator):
    """
    多资产相关性数据生成器
    
    该生成器可以创建多个具有特定相关性结构的资产价格序列，
    适合测试资产配置和多资产交易策略。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化多资产相关性数据生成器
        
        参数:
            config: 配置字典，包含多资产相关性模拟的相关参数
        """
        super().__init__(config)
        # 从配置中获取multi_asset参数
        multi_asset_config = config.get('multi_asset', {})
        self.num_assets = multi_asset_config.get('num_assets', 3)  # 资产数量
        self.asset_names = multi_asset_config.get('asset_names', [f'Asset_{i+1}' for i in range(self.num_assets)])
        
        # 确保资产名称数量与资产数量一致
        if len(self.asset_names) != self.num_assets:
            self.asset_names = [f'Asset_{i+1}' for i in range(self.num_assets)]
        
        # 相关性矩阵，默认为单位矩阵（资产间无相关性）
        self.correlation_matrix = multi_asset_config.get('correlation_matrix', np.eye(self.num_assets))
        
        # 检查相关性矩阵尺寸
        if np.array(self.correlation_matrix).shape != (self.num_assets, self.num_assets):
            print(f"相关性矩阵尺寸不匹配，使用默认单位矩阵")
            self.correlation_matrix = np.eye(self.num_assets)
        
        # 各资产的波动率和漂移率
        self.sigmas = multi_asset_config.get('sigmas', [0.01] * self.num_assets)  # 波动率
        self.mus = multi_asset_config.get('mus', [0.0001] * self.num_assets)      # 漂移率
        
        # 确保波动率和漂移率数组长度正确
        if len(self.sigmas) != self.num_assets:
            self.sigmas = [0.01] * self.num_assets
        if len(self.mus) != self.num_assets:
            self.mus = [0.0001] * self.num_assets
        
    def generate(self, base_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        生成多个相关资产的价格序列
        
        参数:
            base_data: 可选的基础数据，可以用于设定初始价格和学习参数
            
        返回:
            pandas DataFrame，包含多个资产的OHLCV数据
        """
        dt = 1  # 时间步长
        
        # 设置起始价格
        start_prices = [100.0] * self.num_assets
        if base_data is not None and not base_data.empty:
            # 如果有基础数据，尝试提取各资产的最后价格
            for i, name in enumerate(self.asset_names):
                if f'{name}_close' in base_data.columns:
                    start_prices[i] = base_data[f'{name}_close'].iloc[-1]
        
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
        
        # 创建包含所有资产数据的DataFrame
        df = pd.DataFrame(index=dates)
        
        # 生成相关的随机数
        # 使用Cholesky分解生成相关的正态随机数
        L = np.linalg.cholesky(self.correlation_matrix)
        uncorrelated_random = np.random.normal(0, 1, size=(self.length, self.num_assets))
        correlated_random = uncorrelated_random @ L.T
        
        # 为每个资产生成价格序列
        for i in range(self.num_assets):
            asset_name = self.asset_names[i]
            mu = self.mus[i]
            sigma = self.sigmas[i]
            
            # 生成收盘价序列
            prices = [start_prices[i]]
            for j in range(1, self.length):
                drift = mu * dt
                shock = sigma * np.sqrt(dt) * correlated_random[j, i]
                price = prices[-1] * np.exp(drift + shock)
                prices.append(price)
            
            # 生成开盘价、最高价、最低价
            opens = []
            highs = []
            lows = []
            
            # 第一天的开盘价等于起始价格
            opens.append(prices[0])
            
            # 为后续日期生成开盘价
            for j in range(1, len(prices)):
                # 开盘价基于前一天收盘价有小幅波动
                gap_factor = sigma / 2
                opens.append(prices[j-1] * (1 + np.random.uniform(-gap_factor, gap_factor)))
            
            # 生成最高价和最低价
            for j in range(len(prices)):
                # 计算当天价格变动范围
                price_range = abs(opens[j] - prices[j])
                daily_volatility = max(price_range, prices[j] * sigma)
                
                # 最高价和最低价
                if prices[j] >= opens[j]:  # 上涨日
                    high = prices[j] + np.random.uniform(0, daily_volatility)
                    low = opens[j] - np.random.uniform(0, daily_volatility / 2)
                else:  # 下跌日
                    high = opens[j] + np.random.uniform(0, daily_volatility / 2)
                    low = prices[j] - np.random.uniform(0, daily_volatility)
                
                # 确保最低价大于0且关系正确
                low = max(low, 0.01)
                high = max(high, opens[j], prices[j])
                low = min(low, opens[j], prices[j])
                
                highs.append(high)
                lows.append(low)
            
            # 生成成交量
            base_volume = np.random.lognormal(mean=8, sigma=1, size=self.length)
            
            # 添加自相关性
            volume = np.zeros(self.length)
            volume[0] = base_volume[0]
            for j in range(1, self.length):
                volume[j] = 0.6 * volume[j-1] + 0.4 * base_volume[j]
            
            # 价格变动大的日子，成交量往往更大
            price_changes = np.zeros(self.length)
            price_changes[1:] = np.abs(np.diff(prices) / prices[:-1])
            volume_factor = 1 + 5 * price_changes**0.5
            
            # 添加到DataFrame
            df[f'{asset_name}_open'] = opens
            df[f'{asset_name}_high'] = highs
            df[f'{asset_name}_low'] = lows
            df[f'{asset_name}_close'] = prices
            df[f'{asset_name}_volume'] = (volume * volume_factor).astype(int)
        
        df.index.name = 'datetime'
        return df
        
    def to_bt_feed(self, data: pd.DataFrame) -> List:
        """
        将生成的多资产数据转换为backtrader可用的数据源列表
        
        参数:
            data: 生成的模拟数据, 包含多个资产的OHLCV数据
            
        返回:
            backtrader的PandasData对象列表
        """
        from backtrader.feeds import PandasData
        
        data_feeds = []
        
        for asset_name in self.asset_names:
            # 为每个资产创建一个子DataFrame
            asset_data = pd.DataFrame({
                'open': data[f'{asset_name}_open'],
                'high': data[f'{asset_name}_high'],
                'low': data[f'{asset_name}_low'],
                'close': data[f'{asset_name}_close'],
                'volume': data[f'{asset_name}_volume'],
                'openinterest': 0  # backtrader需要这个字段
            }, index=data.index)
            
            # 创建PandasData对象
            data_feed = PandasData(dataname=asset_data, name=asset_name)
            data_feeds.append(data_feed)
            
        return data_feeds 