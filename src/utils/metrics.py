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
    if returns.empty or len(returns) < 2:
        return 0.0
    
    # 处理NaN值
    returns = returns.fillna(0)
    
    excess_returns = returns - (risk_free_rate / periods_per_year)
    
    # 计算标准差前先检查
    std = excess_returns.std()
    if std == 0:
        return 0.0  # 如果波动率为0，夏普比率也为0
        
    sharpe_ratio = excess_returns.mean() / std
    return sharpe_ratio * np.sqrt(periods_per_year) # Annualize

def calculate_max_drawdown(portfolio_values: pd.Series) -> float:
    """
    计算最大回撤
    
    参数:
        portfolio_values: 投资组合价值序列 (pandas Series)
        
    返回:
        最大回撤 (百分比, e.g., 0.1 for 10% drawdown)
    """
    if portfolio_values.empty or len(portfolio_values) < 2:
        return 0.0
    
    # 处理NaN值
    portfolio_values = portfolio_values.ffill().bfill()
    
    # 计算最大回撤
    cumulative_max = portfolio_values.cummax()
    drawdowns = (portfolio_values - cumulative_max) / cumulative_max
    max_drawdown = drawdowns.min()
    
    # 检查是否是有效值
    if pd.isna(max_drawdown):
        return 0.0
        
    return abs(max_drawdown)

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
    
    # 处理NaN值
    portfolio_values = portfolio_values.ffill().bfill()
    
    start_value = portfolio_values.iloc[0]
    end_value = portfolio_values.iloc[-1]
    
    # 计算投资时间长度（以年为单位）
    time_diff = (portfolio_values.index[-1] - portfolio_values.index[0]).total_seconds()
    years = time_diff / (365.25 * 24 * 60 * 60)  # 转换为年
    
    # 安全检查
    if start_value <= 0 or years <= 0:
        return 0.0
    
    # 计算CAGR
    cagr = (end_value / start_value) ** (1 / years) - 1
    
    # 检查是否是有效值
    if pd.isna(cagr) or np.isinf(cagr):
        return 0.0
        
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
    
    # 处理NaN值
    portfolio_values = portfolio_values.ffill().bfill()
    
    # 计算收益率
    returns = portfolio_values.pct_change().fillna(0)
    
    # 计算总收益率
    total_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1
    
    # 计算年化波动率
    volatility = returns.std() * np.sqrt(periods_per_year)
    if pd.isna(volatility) or np.isinf(volatility):
        volatility = 0.0
    
    # 计算各项指标
    cagr = calculate_cagr(portfolio_values, periods_per_year)
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate, periods_per_year)
    max_dd = calculate_max_drawdown(portfolio_values)
    
    # 计算索提诺比率（只考虑下行风险）
    downside_returns = returns[returns < 0]
    if not downside_returns.empty and downside_returns.std() > 0:
        sortino_ratio = (returns.mean() - (risk_free_rate / periods_per_year)) / downside_returns.std()
        sortino_ratio = sortino_ratio * np.sqrt(periods_per_year)  # 年化
        
        # 检查有效性
        if pd.isna(sortino_ratio) or np.isinf(sortino_ratio):
            sortino_ratio = 0.0
    else:
        sortino_ratio = 0.0 if returns.mean() <= 0 else 100.0  # 如果平均收益为正但无下行风险
    
    metrics = {
        'cagr': cagr,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'sortino_ratio': sortino_ratio,
        'total_return': total_return,
        'volatility': volatility
    }
    return metrics
