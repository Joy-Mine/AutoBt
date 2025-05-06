import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .base import BaseDataGenerator

class RegimeSwitchingGenerator(BaseDataGenerator):
    """
    市场状态转换模型，使用马尔科夫链模拟不同市场状态下的价格行为
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化市场状态转换模型数据生成器
        
        参数:
            config: 配置字典，包含市场状态转换模型的相关参数
        """
        super().__init__(config)
        regime_config = config.get('regime', {})
        self.states = regime_config.get('states', 2)
        # Ensure transition_matrix is a numpy array
        self.transition_matrix = np.array(regime_config.get('transition_matrix', 
                                                 [[0.95, 0.05], [0.05, 0.95]]))
        # Define parameters for each regime (e.g., mu and sigma)
        # These can be loaded from config or set as defaults
        self.regime_params = regime_config.get('regime_params', [
            {'mu': 0.0001, 'sigma': 0.01}, # Regime 0: Low volatility
            {'mu': 0.0002, 'sigma': 0.03}  # Regime 1: High volatility
        ])
        if len(self.regime_params) != self.states:
            raise ValueError("Length of regime_params must match the number of states.")
        self.initial_price = config.get('initial_price', 100.0)

    def _get_next_state(self, current_state: int) -> int:
        """Determine the next state based on the transition matrix."""
        return np.random.choice(self.states, p=self.transition_matrix[current_state])
        
    def generate(self, base_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        使用马尔科夫链模拟不同市场状态下的价格行为
        
        参数:
            base_data: 可选的基础数据，可以用于学习转移概率矩阵或设定初始价格。
            
        返回:
            pandas DataFrame，包含OHLCV数据
        """
        prices = np.zeros(self.length)
        regimes = np.zeros(self.length, dtype=int)

        # Set initial price and state
        if base_data is not None and not base_data.empty:
            prices[0] = base_data['close'].iloc[-1]
            # Optionally, infer initial state from base_data characteristics
            # For simplicity, start with state 0
            current_state = 0 
        else:
            prices[0] = self.initial_price
            current_state = 0 # Start in the first regime by default
        
        regimes[0] = current_state

        for t in range(1, self.length):
            # Get parameters for the current state
            params = self.regime_params[current_state]
            mu = params['mu']
            sigma = params['sigma']
            
            # Generate return based on current regime's parameters
            dt = 1 # Time step
            drift = mu * dt
            shock = sigma * np.sqrt(dt) * np.random.normal()
            prices[t] = prices[t-1] * np.exp(drift + shock)
            
            # Determine next state
            current_state = self._get_next_state(current_state)
            regimes[t] = current_state

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
        df['high'] = [p * (1 + np.random.uniform(0, self.regime_params[reg]['sigma']/2)) for p, reg in zip(prices, regimes)]
        df['low'] = [p * (1 - np.random.uniform(0, self.regime_params[reg]['sigma']/2)) for p, reg in zip(prices, regimes)]
        df['close'] = prices
        # Ensure low <= open/close <= high
        df['high'] = df[['high', 'open', 'close']].max(axis=1)
        df['low'] = df[['low', 'open', 'close']].min(axis=1)

        df['volume'] = np.random.randint(100, 1000, size=self.length)
        df['regime'] = regimes # Optionally include regime information
        df.index.name = 'datetime'
        
        return df
