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
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    # 根据命令行参数修改配置
    if args.data_generator:
        config['data_generator']['type'] = args.data_generator
        print(f"使用命令行指定的数据生成器: {args.data_generator}")
        
    if args.strategy:
        config['strategies']['type'] = args.strategy
        print(f"使用命令行指定的策略: {args.strategy}")
    
    if args.mode == 'backtest':
        # 生成模拟数据并运行回测
        from run_backtest import run_backtest
        run_backtest(config)
    else:
        # 运行策略参数优化
        from run_optimization import run_optimization
        strategy_type = config['strategies']['type']
        run_optimization(config, strategy_type)

if __name__ == '__main__':
    main()
