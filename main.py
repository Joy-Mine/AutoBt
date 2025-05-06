import argparse
import yaml
import os
from typing import Dict, Any

def load_config(config_path: str) -> Dict[str, Any]:
    """
    加载配置文件
    
    参数:
        config_path: 配置文件路径
        
    返回:
        配置字典
    """
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='AutoBt - 自动化回测系统')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                        help='配置文件路径')
    parser.add_argument('--mode', type=str, choices=['backtest', 'optimize'],
                        default='backtest', help='运行模式: backtest或optimize')
    parser.add_argument('--strategy', type=str, default='SampleStrategy',
                        help='使用的策略名称')
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    if args.mode == 'backtest':
        # 运行回测
        from run_backtest import run_backtest
        run_backtest(config, args.strategy)
    else:
        # 运行优化
        from run_optimization import run_optimization
        run_optimization(config, args.strategy)

if __name__ == '__main__':
    main()
