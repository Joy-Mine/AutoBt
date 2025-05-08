import argparse
import yaml
from typing import Dict, Any

def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def main():
    parser = argparse.ArgumentParser(description='AutoBt - 自动化回测系统')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                        help='配置文件路径')
    parser.add_argument('--mode', type=str, choices=['backtest', 'optimize'], default='backtest',
                        help='运行模式: backtest或optimize')
    parser.add_argument('--data-generator', type=str, 
                        choices=['monte_carlo', 'garch', 'regime', 'extreme', 'multi_asset', 'stress_test'],
                        help='数据生成器类型，覆盖配置文件中的设置')
    parser.add_argument('--strategy', type=str, 
                        choices=['SampleStrategy', 'DualMovingAverageStrategy', 'MeanReversionStrategy', 'MomentumStrategy'],
                        help='策略类型，覆盖配置文件中的设置')
    parser.add_argument('--force-optimize', action='store_true',
                        help='强制重新优化，忽略已保存的优化结果')
    parser.add_argument('--apply-best', action='store_true',
                        help='将最优参数应用到配置文件')
    parser.add_argument('--metric', type=str, 
                        choices=['sharpe_ratio', 'sortino_ratio', 'max_drawdown', 'total_return', 'cagr'],
                        help='优化使用的性能指标')
    parser.add_argument('--trials', type=int,
                        help='优化试验次数')
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    # 根据命令行参数修改配置
    if args.data_generator:
        config['data_generator']['type'] = args.data_generator
        print(f"使用命令行指定的数据生成器: {args.data_generator}")
        
    if args.strategy:
        config['strategies']['type'] = args.strategy
        print(f"使用命令行指定的策略: {args.strategy}")
    
    # 设置优化参数
    if args.metric and 'optimization' in config:
        config['optimization']['metric'] = args.metric
        print(f"使用命令行指定的优化指标: {args.metric}")
    
    if args.trials and 'optimization' in config:
        config['optimization']['trials'] = args.trials
        print(f"使用命令行指定的优化试验次数: {args.trials}")
    
    if args.mode == 'backtest':
        # 生成模拟数据并运行回测
        from run_backtest import run_backtest
        run_backtest(config)
    else:
        # 运行策略参数优化
        from run_optimization import run_optimization
        strategy_type = config['strategies']['type']
        run_optimization(config, strategy_type, 
                         force_optimize=args.force_optimize, 
                         apply_best=args.apply_best)

if __name__ == '__main__':
    main()
