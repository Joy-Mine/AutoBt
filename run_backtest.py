import backtrader as bt
import pandas as pd
import importlib
import os
from typing import Dict, Any, Type, List

from src.data_generators.base import BaseDataGenerator
from src.utils.metrics import calculate_metrics
from src.utils.visualizer import plot_equity_curve, plot_drawdown


def get_data_generator(config: Dict[str, Any]) -> BaseDataGenerator:
    """根据配置获取数据生成器实例"""
    generator_type = config.get('data_generator', {}).get('type', 'monte_carlo') # Default to monte_carlo
    data_config = config.get('data_generator', {})

    if generator_type == 'monte_carlo':
        from src.data_generators.monte_carlo import MonteCarloGenerator
        return MonteCarloGenerator(data_config)
    elif generator_type == 'garch':
        from src.data_generators.garch import GARCHGenerator
        return GARCHGenerator(data_config)
    elif generator_type == 'extreme':
        from src.data_generators.extreme import ExtremeEventGenerator
        return ExtremeEventGenerator(data_config)
    elif generator_type == 'regime':
        from src.data_generators.regime import RegimeSwitchingGenerator
        return RegimeSwitchingGenerator(data_config)
    else:
        raise ValueError(f"未知的模拟数据生成器类型: {generator_type}")

def get_strategy_class(strategy_name: str) -> Type[bt.Strategy]:
    """
    根据名称获取策略类
    
    参数:
        strategy_name: 策略名称 (e.g., 'SampleStrategy')
        
    返回:
        策略类
    """
    try:
        module = importlib.import_module(f"src.strategies.{strategy_name.lower()}_strategy")
        strategy_class = getattr(module, strategy_name)
        return strategy_class
    except ImportError as e:
        raise ImportError(f"无法导入策略模块: src.strategies.{strategy_name.lower()}_strategy. Error: {e}")
    except AttributeError:
        raise AttributeError(f"在模块中未找到策略类: {strategy_name}")

def run_backtest(config: Dict[str, Any], strategy_name: str, plot: bool = True, results_dir: str = 'results') -> Dict[str, Any]:
    """
    执行回测
    
    参数:
        config: 配置字典
        strategy_name: 要使用的策略名称
        plot: 是否绘制结果图表
        results_dir: 保存结果图表的目录
        
    返回:
        回测结果字典
    """
    data_generator = get_data_generator(config)
    simulated_data_df = data_generator.generate()
    bt_data_feed = data_generator.to_bt_feed(simulated_data_df)

    cerebro = bt.Cerebro()
    cerebro.adddata(bt_data_feed)
    
    StrategyClass = get_strategy_class(strategy_name)
    strategy_params = config.get('strategies', {}).get(strategy_name, {}).get('params', {})
    cerebro.addstrategy(StrategyClass, **strategy_params)
    
    backtest_config = config.get('backtest', {})
    cerebro.broker.setcash(backtest_config.get('cash', 100000.0))
    cerebro.broker.setcommission(commission=backtest_config.get('commission', 0.001))

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')

    print(f"开始回测策略: {strategy_name}...")
    results = cerebro.run()
    strat = results[0]
    print(f"回测完成. 最终组合价值: {cerebro.broker.getvalue():.2f}")

    portfolio_values = pd.Series([v[0] for v in strat.analyzers.pyfolio.get_analysis()['portfolio_value'].values()])
    portfolio_values.index = pd.to_datetime([k for k in strat.analyzers.pyfolio.get_analysis()['portfolio_value'].keys()])
    
    os.makedirs(results_dir, exist_ok=True)
    
    freq = config.get('data_generator', {}).get('frequency', 'D')
    periods_map = {'D': 252, 'H': 252*24, 'M': 252*24*60}
    periods_per_year = periods_map.get(freq, 252)

    calculated_metrics = calculate_metrics(portfolio_values, periods_per_year=periods_per_year)
    
    analysis_results = {
        'initial_cash': backtest_config.get('cash', 100000.0),
        'final_value': cerebro.broker.getvalue(),
        'total_return_abs': cerebro.broker.getvalue() - backtest_config.get('cash', 100000.0),
        'total_return_pct': (cerebro.broker.getvalue() / backtest_config.get('cash', 100000.0) - 1) * 100,
        'sharpe_ratio': strat.analyzers.sharpe.get_analysis().get('sharperatio', 0),
        'max_drawdown': strat.analyzers.drawdown.get_analysis().max.drawdown,
        'num_trades': strat.analyzers.tradeanalyzer.get_analysis().total.total,
        'winning_trades': strat.analyzers.tradeanalyzer.get_analysis().won.total,
        'losing_trades': strat.analyzers.tradeanalyzer.get_analysis().lost.total,
    }
    analysis_results.update(calculated_metrics)

    print("--- 回测结果 ---")
    for key, value in analysis_results.items():
        print(f"{key}: {value}")
    print("-----------------")

    if plot:
        plot_equity_curve(portfolio_values, title=f"Equity Curve - {strategy_name}", save_path=os.path.join(results_dir, f"{strategy_name}_equity_curve.png"))
        plot_drawdown(portfolio_values, title=f"Drawdown - {strategy_name}", save_path=os.path.join(results_dir, f"{strategy_name}_drawdown.png"))

    return analysis_results




if __name__ == '__main__':
    import yaml
    config_path = 'config/config.yaml'
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {os.path.abspath(config_path)}")
        if os.path.exists(os.path.join(os.path.dirname(__file__), config_path)):
            config_path = os.path.join(os.path.dirname(__file__), config_path)
        else:
            potential_path = os.path.join(os.path.dirname(__file__), '..', config_path)
            if os.path.exists(potential_path):
                config_path = potential_path
            else:
                exit(1)

    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    if 'strategies' not in config:
        config['strategies'] = {}
    if 'SampleStrategy' not in config['strategies']:
        config['strategies']['SampleStrategy'] = {
            'params': {'fast_period': 10, 'slow_period': 30}
        }
    if 'data_generator' not in config:
        config['data_generator'] = {}
    config['data_generator']['type'] = 'monte_carlo'

    results = run_backtest(config, 'SampleStrategy', plot=True)
    print("\nDetailed Results Dictionary:")
    print(results)
