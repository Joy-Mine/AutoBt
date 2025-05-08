import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import random

from .base import BaseDataGenerator

class StressTestGenerator(BaseDataGenerator):
    """
    压力测试数据生成器
    
    该生成器可以模拟各种市场极端情况，如市场崩盘、暴涨、高波动期等，
    用于测试策略在极端市场环境下的表现。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化压力测试数据生成器
        
        参数:
            config: 配置字典，包含压力测试相关参数
        """
        super().__init__(config)
        # 从配置中获取stress_test参数
        stress_config = config.get('stress_test', {})
        
        # 极端事件类型
        self.event_type = stress_config.get('event_type', 'random')  # 'crash', 'rally', 'volatility', 'random'
        
        # 极端事件参数
        self.crash_intensity = stress_config.get('crash_intensity', 0.3)  # 崩盘强度（跌幅）
        self.crash_duration = stress_config.get('crash_duration', 20)     # 崩盘持续时间（天）
        self.crash_recovery = stress_config.get('crash_recovery', 60)     # 崩盘恢复时间（天）
        
        self.rally_intensity = stress_config.get('rally_intensity', 0.3)  # 暴涨强度（涨幅）
        self.rally_duration = stress_config.get('rally_duration', 20)     # 暴涨持续时间（天）
        self.rally_correction = stress_config.get('rally_correction', 30) # 暴涨后修正时间（天）
        
        self.vol_multiplier = stress_config.get('vol_multiplier', 3.0)    # 高波动期波动率倍数
        self.vol_duration = stress_config.get('vol_duration', 40)         # 高波动期持续时间（天）
        
        # 基础市场参数
        self.mu = stress_config.get('mu', 0.0001)  # 基础漂移率
        self.sigma = stress_config.get('sigma', 0.01)  # 基础波动率
        
    def _generate_crash(self, start_price: float) -> Tuple[List[float], List[float], List[float], List[float]]:
        """生成市场崩盘数据"""
        # 分三个阶段：正常期、崩盘期、恢复期
        normal_days = self.length - self.crash_duration - self.crash_recovery
        
        # 确保至少有一些正常日
        if normal_days < 10:
            normal_days = self.length // 3
            self.crash_duration = self.length // 3
            self.crash_recovery = self.length - normal_days - self.crash_duration
        
        # 第一阶段：正常市场
        prices_normal = [start_price]
        for _ in range(1, normal_days):
            drift = self.mu
            shock = self.sigma * np.random.normal()
            price = prices_normal[-1] * np.exp(drift + shock)
            prices_normal.append(price)
        
        # 第二阶段：市场崩盘
        crash_start_price = prices_normal[-1]
        crash_end_price = crash_start_price * (1 - self.crash_intensity)
        
        # 使用对数线性插值生成崩盘期价格
        prices_crash = []
        for i in range(self.crash_duration):
            # 非线性崩盘路径，前期缓慢，后期加速
            progress = (i / self.crash_duration) ** 2
            log_price = np.log(crash_start_price) * (1 - progress) + np.log(crash_end_price) * progress
            # 添加一些随机波动
            log_price += self.sigma * 1.5 * np.random.normal()  # 崩盘期波动加大
            prices_crash.append(np.exp(log_price))
        
        # 第三阶段：市场恢复
        recovery_start_price = prices_crash[-1]
        recovery_target = crash_start_price * 0.9  # 恢复到崩盘前的90%
        
        # 使用对数线性插值生成恢复期价格
        prices_recovery = []
        for i in range(self.crash_recovery):
            # 非线性恢复路径，前期快速，后期放缓
            progress = np.sqrt(i / self.crash_recovery)
            log_price = np.log(recovery_start_price) * (1 - progress) + np.log(recovery_target) * progress
            # 添加一些随机波动
            log_price += self.sigma * 1.2 * np.random.normal()  # 恢复期波动略大
            prices_recovery.append(np.exp(log_price))
        
        # 合并所有阶段的价格
        prices = prices_normal + prices_crash + prices_recovery
        
        # 生成开盘价、最高价、最低价
        opens, highs, lows = self._generate_ohlc(prices)
        
        return prices, opens, highs, lows
    
    def _generate_rally(self, start_price: float) -> Tuple[List[float], List[float], List[float], List[float]]:
        """生成市场暴涨数据"""
        # 分三个阶段：正常期、暴涨期、修正期
        normal_days = self.length - self.rally_duration - self.rally_correction
        
        # 确保至少有一些正常日
        if normal_days < 10:
            normal_days = self.length // 3
            self.rally_duration = self.length // 3
            self.rally_correction = self.length - normal_days - self.rally_duration
        
        # 第一阶段：正常市场
        prices_normal = [start_price]
        for _ in range(1, normal_days):
            drift = self.mu
            shock = self.sigma * np.random.normal()
            price = prices_normal[-1] * np.exp(drift + shock)
            prices_normal.append(price)
        
        # 第二阶段：市场暴涨
        rally_start_price = prices_normal[-1]
        rally_end_price = rally_start_price * (1 + self.rally_intensity)
        
        # 使用对数线性插值生成暴涨期价格
        prices_rally = []
        for i in range(self.rally_duration):
            # 非线性暴涨路径，前期缓慢，后期加速
            progress = (i / self.rally_duration) ** 1.5
            log_price = np.log(rally_start_price) * (1 - progress) + np.log(rally_end_price) * progress
            # 添加一些随机波动
            log_price += self.sigma * 1.5 * np.random.normal()  # 暴涨期波动加大
            prices_rally.append(np.exp(log_price))
        
        # 第三阶段：市场修正
        correction_start_price = prices_rally[-1]
        correction_target = correction_start_price * 0.85  # 修正到高点的85%
        
        # 使用对数线性插值生成修正期价格
        prices_correction = []
        for i in range(self.rally_correction):
            # 非线性修正路径
            progress = (i / self.rally_correction) ** 0.8
            log_price = np.log(correction_start_price) * (1 - progress) + np.log(correction_target) * progress
            # 添加一些随机波动
            log_price += self.sigma * 1.2 * np.random.normal()  # 修正期波动略大
            prices_correction.append(np.exp(log_price))
        
        # 合并所有阶段的价格
        prices = prices_normal + prices_rally + prices_correction
        
        # 生成开盘价、最高价、最低价
        opens, highs, lows = self._generate_ohlc(prices)
        
        return prices, opens, highs, lows
    
    def _generate_high_volatility(self, start_price: float) -> Tuple[List[float], List[float], List[float], List[float]]:
        """生成高波动性数据"""
        # 分三个阶段：正常期、高波动期、恢复正常期
        normal_days_before = (self.length - self.vol_duration) // 2
        normal_days_after = self.length - normal_days_before - self.vol_duration
        
        # 第一阶段：正常市场
        prices_normal_before = [start_price]
        for _ in range(1, normal_days_before):
            drift = self.mu
            shock = self.sigma * np.random.normal()
            price = prices_normal_before[-1] * np.exp(drift + shock)
            prices_normal_before.append(price)
        
        # 第二阶段：高波动期
        vol_start_price = prices_normal_before[-1]
        prices_vol = [vol_start_price]
        for _ in range(1, self.vol_duration):
            drift = self.mu
            # 使用更高的波动率
            shock = self.sigma * self.vol_multiplier * np.random.normal()
            price = prices_vol[-1] * np.exp(drift + shock)
            prices_vol.append(price)
        
        # 第三阶段：恢复正常
        normal_after_start_price = prices_vol[-1]
        prices_normal_after = [normal_after_start_price]
        for _ in range(1, normal_days_after):
            drift = self.mu
            shock = self.sigma * np.random.normal()
            price = prices_normal_after[-1] * np.exp(drift + shock)
            prices_normal_after.append(price)
        
        # 合并所有阶段的价格
        prices = prices_normal_before + prices_vol + prices_normal_after
        
        # 生成开盘价、最高价、最低价
        opens, highs, lows = self._generate_ohlc(prices)
        
        return prices, opens, highs, lows
    
    def _generate_ohlc(self, prices: List[float]) -> Tuple[List[float], List[float], List[float]]:
        """从收盘价生成开盘价、最高价、最低价"""
        opens = []
        highs = []
        lows = []
        
        # 第一天的开盘价等于收盘价
        opens.append(prices[0])
        
        # 为后续日期生成开盘价
        for i in range(1, len(prices)):
            # 开盘价基于前一天收盘价有小幅波动
            gap_factor = self.sigma / 2
            opens.append(prices[i-1] * (1 + np.random.uniform(-gap_factor, gap_factor)))
        
        # 生成最高价和最低价
        for i in range(len(prices)):
            # 计算当天价格变动范围
            price_range = abs(opens[i] - prices[i])
            daily_volatility = max(price_range, prices[i] * self.sigma)
            
            # 最高价和最低价
            if prices[i] >= opens[i]:  # 上涨日
                high = prices[i] + np.random.uniform(0, daily_volatility)
                low = opens[i] - np.random.uniform(0, daily_volatility / 2)
            else:  # 下跌日
                high = opens[i] + np.random.uniform(0, daily_volatility / 2)
                low = prices[i] - np.random.uniform(0, daily_volatility)
            
            # 确保最低价大于0且关系正确
            low = max(low, 0.01)
            high = max(high, opens[i], prices[i])
            low = min(low, opens[i], prices[i])
            
            highs.append(high)
            lows.append(low)
            
        return opens, highs, lows
        
    def generate(self, base_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        生成压力测试数据
        
        参数:
            base_data: 可选的基础数据，可以用于设定初始价格
            
        返回:
            pandas DataFrame，包含OHLCV数据
        """
        # 设置起始价格
        start_price = 100.0
        if base_data is not None and not base_data.empty:
            start_price = base_data['close'].iloc[-1]
        
        # 根据事件类型生成价格序列
        if self.event_type == 'crash':
            prices, opens, highs, lows = self._generate_crash(start_price)
        elif self.event_type == 'rally':
            prices, opens, highs, lows = self._generate_rally(start_price)
        elif self.event_type == 'volatility':
            prices, opens, highs, lows = self._generate_high_volatility(start_price)
        else:  # random
            # 随机选择一种极端事件
            event = random.choice(['crash', 'rally', 'volatility'])
            if event == 'crash':
                prices, opens, highs, lows = self._generate_crash(start_price)
            elif event == 'rally':
                prices, opens, highs, lows = self._generate_rally(start_price)
            else:
                prices, opens, highs, lows = self._generate_high_volatility(start_price)
        
        # 创建日期索引
        freq = self.config.get('frequency', 'D')
        if freq == 'D':
            freq_str = 'B'  # 使用工作日
        elif freq == 'H':
            freq_str = 'H'
        elif freq == 'M':
            freq_str = 'T'  # 分钟用T表示
        else:
            freq_str = 'B'

        # 设置起始日期
        if base_data is not None and not base_data.empty and isinstance(base_data.index, pd.DatetimeIndex):
            start_date = base_data.index[-1] + timedelta(days=1)
        else:
            start_date = datetime(2020, 1, 1)  # 默认起始日期
        
        # 使用pandas的date_range生成日期序列
        dates = pd.date_range(start=start_date, periods=len(prices), freq=freq_str)
        
        # 创建DataFrame
        df = pd.DataFrame(index=dates)
        df['open'] = opens
        df['high'] = highs
        df['low'] = lows
        df['close'] = prices
        
        # 生成成交量 - 在极端事件中，成交量通常与价格波动正相关
        base_volume = np.random.lognormal(mean=8, sigma=1, size=len(prices))
        
        # 添加自相关性
        volume = np.zeros(len(prices))
        volume[0] = base_volume[0]
        for i in range(1, len(prices)):
            # 新成交量有60%来自前一天的成交量
            volume[i] = 0.6 * volume[i-1] + 0.4 * base_volume[i]
        
        # 价格变动大的日子，成交量往往更大
        price_changes = np.zeros(len(prices))
        price_changes[1:] = np.abs(np.diff(prices) / prices[:-1])
        
        # 在极端事件中，成交量与价格变动的关系更强
        volume_factor = 1 + 10 * price_changes  # 放大价格变动对成交量的影响
        
        df['volume'] = (volume * volume_factor).astype(int)
        df.index.name = 'datetime'
        
        return df 