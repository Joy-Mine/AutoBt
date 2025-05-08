import backtrader as bt
import pandas as pd
from typing import Dict, Any, Type, Tuple
from src.optimizers import OptunaOptimizer
from src.utils.visualizer import plot_optimization_results

def run_optimization(config: Dict[str, Any], strategy_name: str) -> Dict[str, Any]:
    """
    执行参数优化
    
    参数:
        config: 配置字典
        strategy_name: 要优化的策略名称
        
    返回:
        优化结果
    """
    optimizer = OptunaOptimizer(config)
    study = optimizer.optimize(strategy_name)
    # 可视化优化结果
    param_space = config.get('optimization', {}).get('param_space', {}).get(strategy_name, {})
    param_names = list(param_space.keys()) if param_space else []
    plot_optimization_results(study, param_names, metric_name=config.get('optimization', {}).get('metric', 'sharpe_ratio'), save_path=f'results/{strategy_name}_optimization.png')
    # 返回最优结果
    return {
        'best_value': study.best_value,
        'best_params': study.best_params,
        'trials': len(study.trials)
    }

def get_param_space(strategy_class: Type[bt.Strategy]) -> Dict[str, Tuple]:
    """
    为给定策略构建参数空间
    
    参数:
        strategy_class: 策略类
        
    返回:
        参数空间字典
    """
    # 直接从params属性推断
    space = {}
    if hasattr(strategy_class, 'params') and isinstance(strategy_class.params, tuple):
        for p_tuple in strategy_class.params:
            if isinstance(p_tuple, tuple) and len(p_tuple) >= 2:
                name = p_tuple[0]
                default = p_tuple[1]
                if isinstance(default, int):
                    space[name] = {'type': 'int', 'low': max(1, default // 2), 'high': default * 2}
                elif isinstance(default, float):
                    space[name] = {'type': 'float', 'low': default / 2, 'high': default * 2}
    return space

def get_strategy_class(config: Dict[str, Any]) -> Type[bt.Strategy]:
    """
    根据配置获取策略类
    
    参数:
        config: 配置字典
        
    返回:
        策略类
    """
    strategy_type = config.get('strategies', {}).get('type', 'SampleStrategy')
    
    if strategy_type == 'SampleStrategy':
        from src.strategies.sample_strategy import SampleStrategy
        return SampleStrategy
    elif strategy_type == 'DualMovingAverageStrategy':
        from src.strategies.dual_moving_average_strategy import DualMovingAverageStrategy
        return DualMovingAverageStrategy
    else:
        raise ValueError(f"未知的策略类型: {strategy_type}")

if __name__ == '__main__':
    import yaml
    with open('config/config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    
    results = run_optimization(config, 'SampleStrategy')
    print(results)
