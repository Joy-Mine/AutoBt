import backtrader as bt
import pandas as pd
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
        print(f"未知的模拟数据生成器类型: {generator_type}，使用默认的monte_carlo")
        from src.data_generators.monte_carlo import MonteCarloGenerator
        return MonteCarloGenerator(data_config)

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
        print(f"未知的策略类型: {strategy_type}，使用默认SampleStrategy")
        from src.strategies.sample_strategy import SampleStrategy
        return SampleStrategy

def run_backtest(config: Dict[str, Any], plot: bool = True, results_dir: str = 'results') -> Dict[str, Any]:
    """
    执行回测
    
    参数:
        config: 配置字典
        plot: 是否绘制结果图表
        results_dir: 保存结果图表的目录
        
    返回:
        回测结果字典
    """
    # 确保配置中存在必要的部分
    if 'strategies' not in config:
        config['strategies'] = {}
    if 'type' not in config['strategies']:
        config['strategies']['type'] = 'SampleStrategy'
    
    # 生成模拟数据
    data_generator = get_data_generator(config)
    simulated_data_df = data_generator.generate()
    bt_data_feed = data_generator.to_bt_feed(simulated_data_df)

    # 创建Cerebro引擎并添加数据
    cerebro = bt.Cerebro()
    cerebro.adddata(bt_data_feed)
    
    # 添加一个观察者来跟踪投资组合价值
    cerebro.addobserver(bt.observers.Value)
    cerebro.addobserver(bt.observers.DrawDown)

    # 添加策略
    StrategyClass = get_strategy_class(config)
    strategy_type = config['strategies']['type']
    strategy_params = config.get('strategies', {}).get(strategy_type, {})
    print(f"策略参数: {strategy_params}")
    cerebro.addstrategy(StrategyClass, **strategy_params)
    
    # 设置初始资金和手续费
    backtest_config = config.get('backtest', {})
    cerebro.broker.setcash(backtest_config.get('cash', 100000.0))
    cerebro.broker.setcommission(commission=backtest_config.get('commission', 0.001))

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')

    # 运行回测
    print(f"开始回测策略: {strategy_type}...")
    results = cerebro.run()
    print(f"回测完成. 最终组合价值: {cerebro.broker.getvalue():.2f}")

    # 创建结果目录
    os.makedirs(results_dir, exist_ok=True)
    
    # 获取回测结果
    strat = results[0]
    
    # 安全地获取分析结果
    def safe_get(analyzer, attr_path, default=0):
        try:
            result = analyzer.get_analysis()
            for attr in attr_path.split('.'):
                if hasattr(result, attr):
                    result = getattr(result, attr)
                elif isinstance(result, dict) and attr in result:
                    result = result[attr]
                else:
                    return default
            return result
        except Exception as e:
            print(f"获取分析结果时出错: {e}")
            return default
    
    # 获取投资组合价值
    try:
        # 创建直接的日线价值序列
        initial_cash = backtest_config.get('cash', 100000.0)
        final_value = cerebro.broker.getvalue()
        
        # 首先尝试从analyzers获取每日价值
        if hasattr(strat.analyzers, 'pyfolio'):
            pyfolio = strat.analyzers.getbyname('pyfolio')
            # 检查是否有portfolio_value
            pyfolio_analysis = pyfolio.get_analysis()
            if pyfolio_analysis and 'returns' in pyfolio_analysis and len(pyfolio_analysis['returns']) > 0:
                # 获取收益率，然后计算投资组合价值
                rets = pd.Series(pyfolio_analysis['returns'])
                # 从初始值开始累积
                portfolio_values = initial_cash * (1 + rets).cumprod()
                portfolio_values.index = pd.DatetimeIndex(pyfolio_analysis['returns'].keys())
            else:
                # 如果无法获取收益率，尝试获取交易日期和价值
                print("警告: 无法从pyfolio获取收益率，尝试构建简化的价值序列")
                # 获取交易日期
                trade_dates = []
                trade_values = []
                
                # 从交易分析器获取交易日期
                if hasattr(strat.analyzers, 'tradeanalyzer'):
                    analyzer = strat.analyzers.getbyname('tradeanalyzer')
                    analysis = analyzer.get_analysis()
                    
                    # 至少需要初始日期和最终日期
                    trade_dates = [simulated_data_df.index[0]]
                    trade_values = [initial_cash]
                    
                    # 添加每笔交易的日期和价值变化
                    if 'closed' in analysis and analysis['closed'] > 0:
                        for trade_num in range(analysis['closed']):
                            if f'trade{trade_num}' in analysis:
                                trade = analysis[f'trade{trade_num}']
                                if 'dtout' in trade:  # 平仓日期
                                    date = trade['dtout']
                                    if isinstance(date, str):
                                        date = pd.to_datetime(date)
                                    trade_dates.append(date)
                                    # 使用粗略的价值估计
                                    value = trade_values[-1] + trade.get('pnlcomm', 0)
                                    trade_values.append(value)
                
                # 添加最终日期和价值
                if trade_dates and trade_dates[-1] != simulated_data_df.index[-1]:
                    trade_dates.append(simulated_data_df.index[-1])
                    trade_values.append(final_value)
                
                # 创建投资组合价值序列
                if trade_dates:
                    portfolio_values = pd.Series(trade_values, index=trade_dates)
                    # 按日期排序
                    portfolio_values = portfolio_values.sort_index()
                else:
                    print("警告: 无法获取足够的交易数据，使用简化的两点序列")
                    portfolio_values = pd.Series(
                        [initial_cash, final_value], 
                        index=[simulated_data_df.index[0], simulated_data_df.index[-1]]
                    )
        else:
            print("警告: 找不到pyfolio分析器，使用简化的投资组合价值序列")
            portfolio_values = pd.Series(
                [initial_cash, final_value], 
                index=[simulated_data_df.index[0], simulated_data_df.index[-1]]
            )
    except Exception as e:
        print(f"处理投资组合价值时出错: {e}")
        print("使用简化的投资组合价值序列")
        initial_cash = backtest_config.get('cash', 100000.0)
        final_value = cerebro.broker.getvalue()
        portfolio_values = pd.Series(
            [initial_cash, final_value], 
            index=[simulated_data_df.index[0], simulated_data_df.index[-1]]
        )
    
    # 计算绩效指标
    freq = config.get('data_generator', {}).get('frequency', 'D')
    periods_map = {'D': 252, 'H': 252*24, 'M': 252*24*60}
    periods_per_year = periods_map.get(freq, 252)
    
    calculated_metrics = calculate_metrics(portfolio_values, periods_per_year=periods_per_year)
    
    # 汇总结果
    analysis_results = {
        'initial_cash': initial_cash,
        'final_value': final_value,
        'total_return_abs': final_value - initial_cash,
        'total_return_pct': (final_value / initial_cash - 1) * 100,
        'sharpe_ratio': safe_get(strat.analyzers.sharpe, 'sharperatio'),
        'max_drawdown': safe_get(strat.analyzers.drawdown, 'max.drawdown'),
        'num_trades': safe_get(strat.analyzers.tradeanalyzer, 'total.total'),
        'winning_trades': safe_get(strat.analyzers.tradeanalyzer, 'won.total'),
        'losing_trades': safe_get(strat.analyzers.tradeanalyzer, 'lost.total'),
    }
    analysis_results.update(calculated_metrics)

    # 打印结果
    print("\n--- 回测结果 ---")
    for key, value in analysis_results.items():
        print(f"{key}: {value}")
    print("-----------------")

    # 绘图
    if plot:
        try:
            cerebro.plot()
        except Exception as e:
            print(f"绘制backtrader图表时出错: {e}")
        
        try:
            plot_equity_curve(portfolio_values, title=f"权益曲线 - {strategy_type}", 
                             save_path=os.path.join(results_dir, f"{strategy_type}_equity_curve.png"))
            plot_drawdown(portfolio_values, title=f"回撤 - {strategy_type}", 
                         save_path=os.path.join(results_dir, f"{strategy_type}_drawdown.png"))
        except Exception as e:
            print(f"绘制性能图表时出错: {e}")

    return analysis_results

if __name__ == '__main__':
    import yaml
    config_path = 'config/config.yaml'
    
    # 查找配置文件
    if not os.path.exists(config_path):
        print(f"未找到配置文件: {os.path.abspath(config_path)}")
        alt_paths = [
            os.path.join(os.path.dirname(__file__), config_path),
            os.path.join(os.path.dirname(__file__), '..', config_path)
        ]
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                config_path = alt_path
                print(f"使用替代配置文件: {config_path}")
                break
        else:
            print("无法找到配置文件，使用默认配置")
            config = {}
    else:
        # 加载配置
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
    
    # 设置默认值
    if 'strategies' not in config:
        config['strategies'] = {}
    if 'type' not in config['strategies']:
        config['strategies']['type'] = 'SampleStrategy'
    if config['strategies']['type'] not in config['strategies']:
        config['strategies'][config['strategies']['type']] = {}
    if 'data_generator' not in config:
        config['data_generator'] = {}
    if 'type' not in config['data_generator']:
        config['data_generator']['type'] = 'monte_carlo'

    # 运行回测
    results = run_backtest(config, plot=True)
    print("\n详细结果字典:")
    print(results)
