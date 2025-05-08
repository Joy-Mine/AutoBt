import pandas as pd
import numpy as np
from typing import Dict, Any, List

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    """
    计算夏普比率
    
    参数:
        returns: 收益率序列 (pandas Series)
        risk_free_rate: 年化无风险利率
        periods_per_year: 每年的周期数 (例如，日收益率为252，月收益率为12)
        
    返回:
        年化夏普比率
    """
    if returns.empty or returns.std() == 0:
        return 0.0
    excess_returns = returns - (risk_free_rate / periods_per_year)
    sharpe_ratio = excess_returns.mean() / excess_returns.std()
    return sharpe_ratio * np.sqrt(periods_per_year) # Annualize

def calculate_max_drawdown(portfolio_values: pd.Series) -> float:
    """
    计算最大回撤
    
    参数:
        portfolio_values: 投资组合价值序列 (pandas Series)
        
    返回:
        最大回撤 (百分比, e.g., 0.1 for 10% drawdown)
    """
    if portfolio_values.empty:
        return 0.0
    # Calculate the cumulative maximum
    cumulative_max = portfolio_values.cummax()
    # Calculate the drawdown
    drawdown = (portfolio_values - cumulative_max) / cumulative_max
    # Get the maximum drawdown
    max_drawdown = drawdown.min() # This will be negative or zero
    return abs(max_drawdown) if not pd.isna(max_drawdown) else 0.0

def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252, target_return: float = 0.0) -> float:
    """
    计算索提诺比率
    
    参数:
        returns: 收益率序列 (pandas Series)
        risk_free_rate: 年化无风险利率
        periods_per_year: 每年的周期数
        target_return: 目标收益率 (年化, 用于计算下行偏差)
        
    返回:
        年化索提诺比率
    """
    if returns.empty:
        return 0.0
    
    # Calculate excess returns over the target return
    excess_returns = returns - (target_return / periods_per_year)
    # Calculate downside deviation
    downside_returns = excess_returns[excess_returns < 0]
    if downside_returns.empty or downside_returns.std() == 0:
        return np.inf if excess_returns.mean() > 0 else 0.0 # Avoid division by zero; if mean is positive, it's infinitely good by this measure
        
    downside_deviation = downside_returns.std()
    
    # Calculate Sortino Ratio
    sortino_ratio = (returns.mean() - (risk_free_rate / periods_per_year)) / downside_deviation
    return sortino_ratio * np.sqrt(periods_per_year) # Annualize

def calculate_cagr(portfolio_values: pd.Series, periods_per_year: int = 252) -> float:
    """
    计算复合年增长率 (CAGR)

    参数:
        portfolio_values: 投资组合价值序列 (pandas Series)
        periods_per_year: 每年的周期数

    返回:
        CAGR (e.g., 0.1 for 10% CAGR)
    """
    if portfolio_values.empty or len(portfolio_values) < 2:
        return 0.0
    start_value = portfolio_values.iloc[0]
    end_value = portfolio_values.iloc[-1]
    num_years = len(portfolio_values) / periods_per_year
    if start_value == 0 or num_years == 0: # Avoid division by zero or power of zero
        return 0.0
    cagr = (end_value / start_value) ** (1 / num_years) - 1
    return cagr

def calculate_metrics(portfolio_values: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> Dict[str, float]:
    """
    计算一系列性能指标
    
    参数:
        portfolio_values: 投资组合价值序列 (pandas Series)
        risk_free_rate: 年化无风险利率
        periods_per_year: 每年的周期数
        
    返回:
        包含各种性能指标的字典
    """
    if portfolio_values.empty or len(portfolio_values) < 2:
        return {
            'cagr': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'sortino_ratio': 0.0,
            'total_return': 0.0,
            'volatility': 0.0
        }

    returns = portfolio_values.pct_change().dropna()
    total_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1
    
    metrics = {
        'cagr': calculate_cagr(portfolio_values, periods_per_year),
        'sharpe_ratio': calculate_sharpe_ratio(returns, risk_free_rate, periods_per_year),
        'max_drawdown': calculate_max_drawdown(portfolio_values),
        'sortino_ratio': calculate_sortino_ratio(returns, risk_free_rate, periods_per_year),
        'total_return': total_return,
        'volatility': returns.std() * np.sqrt(periods_per_year) # Annualized volatility
    }
    return metrics
