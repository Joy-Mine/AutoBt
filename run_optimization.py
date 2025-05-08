import backtrader as bt
import pandas as pd
import yaml
import os
import json
from typing import Dict, Any, Type, Tuple, Optional, List
from src.optimizers import OptunaOptimizer
from src.utils.visualizer import plot_optimization_results

def run_optimization(config: Dict[str, Any], strategy_name: str, force_optimize: bool = False, apply_best: bool = False) -> Dict[str, Any]:
    """
    执行参数优化
    
    参数:
        config: 配置字典
        strategy_name: 要优化的策略名称
        force_optimize: 是否强制重新优化，忽略已保存的结果
        apply_best: 是否将最优参数应用到配置文件
        
    返回:
        优化结果
    """
    print(f"\n{'='*60}")
    print(f"开始优化策略: {strategy_name}")
    print(f"{'='*60}")
    
    # 创建优化器实例
    optimizer = OptunaOptimizer(config)
    
    # 如果强制优化，则传递特殊存储URL确保创建新的优化
    storage_url = "sqlite:///:memory:" if force_optimize else None
    
    # 开始优化
    study = optimizer.optimize(strategy_name, storage_url=storage_url)
    
    # 获取优化结果
    results_path = os.path.join('results', f"{strategy_name}_optimization_results.json")
    
    if os.path.exists(results_path):
        # 读取保存的结果
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        best_params = results.get('best_params', {})
        best_value = results.get('best_value', 'N/A')
        
        # 打印优化结果摘要
        print(f"\n优化结果摘要:")
        print(f"策略: {strategy_name}")
        print(f"优化指标: {results.get('metric', 'sharpe_ratio')}")
        print(f"最佳值: {best_value}")
        print(f"最佳参数:")
        for param, value in best_params.items():
            print(f"  {param}: {value}")
        
        # 可视化优化结果
        param_space = config.get('optimization', {}).get('param_space', {}).get(strategy_name, {})
        param_names = list(param_space.keys()) if param_space else []
        metric_name = config.get('optimization', {}).get('metric', 'sharpe_ratio')
        
        print(f"\n正在生成优化结果图表...")
        try:
            plot_optimization_results(study, param_names, metric_name=metric_name, 
                                    save_path=f'results/{strategy_name}_optimization.png')
        except Exception as e:
            print(f"生成图表时出错: {e}")
        
        # 如果需要应用最佳参数到配置
        if apply_best and best_params:
            apply_best_params(config, strategy_name, best_params)
        
        return {
            'best_value': best_value,
            'best_params': best_params,
            'trials': results.get('trials', 0)
        }
    else:
        print(f"警告: 未找到保存的优化结果文件: {results_path}")
        if hasattr(study, 'best_trial') and study.best_trial:
            return {
                'best_value': study.best_value,
                'best_params': study.best_trial.params,
                'trials': len(study.trials)
            }
        else:
            return {
                'best_value': None,
                'best_params': {},
                'trials': 0
            }

def apply_best_params(config: Dict[str, Any], strategy_name: str, best_params: Dict[str, Any]) -> None:
    """
    将最优参数应用到配置文件
    
    参数:
        config: 配置字典
        strategy_name: 策略名称
        best_params: 最优参数字典
    """
    print(f"\n正在将最优参数应用到配置文件...")
    
    # 更新内存中的配置
    if 'strategies' in config and strategy_name in config['strategies']:
        for param, value in best_params.items():
            config['strategies'][strategy_name][param] = value
        
        # 保存到配置文件
        config_path = 'config/config_optimized.yaml'
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        print(f"已将最优参数写入配置文件: {config_path}")
    else:
        print(f"警告: 配置文件中不存在策略 {strategy_name} 的配置部分")

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
                    space[name] = {'type': 'float', 'low': max(0.001, default / 2), 'high': default * 2}
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
    elif strategy_type == 'MeanReversionStrategy':
        from src.strategies.mean_reversion_strategy import MeanReversionStrategy
        return MeanReversionStrategy
    elif strategy_type == 'MomentumStrategy':
        from src.strategies.momentum_strategy import MomentumStrategy
        return MomentumStrategy
    else:
        raise ValueError(f"未知的策略类型: {strategy_type}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='AutoBt 策略参数优化')
    parser.add_argument('--config', type=str, default='config/config.yaml', help='配置文件路径')
    parser.add_argument('--strategy', type=str, help='要优化的策略名称')
    parser.add_argument('--force', action='store_true', help='强制重新优化，忽略已保存的结果')
    parser.add_argument('--apply', action='store_true', help='将最优参数应用到配置文件')
    args = parser.parse_args()
    
    with open(args.config, 'r') as file:
        config = yaml.safe_load(file)
    
    strategy_name = args.strategy or config.get('strategies', {}).get('type', 'SampleStrategy')
    results = run_optimization(config, strategy_name, force_optimize=args.force, apply_best=args.apply)
    print(f"\n优化完成! 最佳{config.get('optimization', {}).get('metric', 'sharpe_ratio')}: {results['best_value']}")
