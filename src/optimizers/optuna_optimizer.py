import numpy as np
import optuna
import backtrader as bt
import pandas as pd  # Added for portfolio_values series
import json
import os
import datetime
from typing import Dict, Any, Callable, Type, List, Tuple, Optional
import importlib  # Added for dynamic strategy loading
import os  # Added for path joining

# Assuming these are correctly placed for import
from src.data_generators.base import BaseDataGenerator  # For type hinting and usage
from src.utils.metrics import calculate_metrics  # For calculating metrics


# Helper to get data generator (similar to run_backtest.py)
def get_data_generator(config: Dict[str, Any]) -> BaseDataGenerator:
    generator_type = config.get('data_generator', {}).get('type', 'monte_carlo')
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
    elif generator_type == 'multi_asset':
        from src.data_generators.multi_asset import MultiAssetGenerator
        return MultiAssetGenerator(data_config)
    elif generator_type == 'stress_test':
        from src.data_generators.stress_test import StressTestGenerator
        return StressTestGenerator(data_config)
    else:
        raise ValueError(f"Unknown data generator type: {generator_type}")


# Helper to get strategy class (similar to run_backtest.py)
def get_strategy_class(strategy_name: str) -> Type[bt.Strategy]:
    """
    根据策略名称获取策略类
    
    参数:
        strategy_name: 策略名称
        
    返回:
        策略类
    """
    # 处理不同的策略名称格式
    if strategy_name == 'SampleStrategy':
        module_name = 'src.strategies.sample_strategy'
    elif strategy_name == 'DualMovingAverageStrategy':
        module_name = 'src.strategies.dual_moving_average_strategy'
    elif strategy_name == 'MeanReversionStrategy':
        module_name = 'src.strategies.mean_reversion_strategy'
    elif strategy_name == 'MomentumStrategy':
        module_name = 'src.strategies.momentum_strategy'
    else:
        # 尝试使用默认格式
        module_name = f"src.strategies.{strategy_name.lower()}_strategy"
    
    try:
        module = importlib.import_module(module_name)
        return getattr(module, strategy_name)
    except ImportError as e:
        raise ImportError(f"无法导入策略模块: {module_name}. 错误: {e}")
    except AttributeError:
        raise AttributeError(f"在模块中未找到策略类 {strategy_name}.")


class OptunaOptimizer:
    """使用Optuna进行策略参数优化的实现"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化Optuna优化器

        参数:
            config: 配置字典，包含参数优化的相关参数
        """
        self.config = config
        self.trials = config.get('optimization', {}).get('trials', 100)
        self.metric = config.get('optimization', {}).get('metric', 'sharpe_ratio')
        self.direction = config.get('optimization', {}).get('direction', 'maximize')
        # 结果保存路径
        self.results_dir = 'results'
        os.makedirs(self.results_dir, exist_ok=True)

    def optimize(self,
                 strategy_name: str,  # Changed from strategy_cls to name for dynamic loading
                 base_data_df: Optional[pd.DataFrame] = None,  # Allow passing base data for generation
                 study_name: Optional[str] = None,
                 storage_url: Optional[str] = None
                 ) -> optuna.Study:
        """
        执行参数优化

        参数:
            strategy_name: 要优化的策略名称
            base_data_df: 可选的基础数据，用于模拟数据生成
            study_name: Optuna study的名称 (用于持久化)
            storage_url: Optuna study的存储URL (例如, 'sqlite:///example.db')

        返回:
            Optuna study 对象包含优化结果
        """
        StrategyClass = get_strategy_class(strategy_name)
        param_space = self._get_param_space(StrategyClass)

        # 检查是否有已保存的优化结果
        result_file = os.path.join(self.results_dir, f"{strategy_name}_optimization_results.json")
        if os.path.exists(result_file) and not storage_url:
            print(f"发现已保存的优化结果: {result_file}")
            print("使用 --force-optimize 参数重新优化")
            
            try:
                # 加载并显示已保存的优化结果
                with open(result_file, 'r') as f:
                    saved_results = json.load(f)
                
                print(f"已保存的最佳参数 ({saved_results['date']}):")
                for param, value in saved_results['best_params'].items():
                    print(f"  {param}: {value}")
                print(f"最佳{self.metric}: {saved_results['best_value']}")
                
                # 创建一个假的study用于返回
                dummy_study = optuna.create_study(direction=self.direction)
                return dummy_study
            except Exception as e:
                print(f"读取保存的结果时出错: {e}. 正在进行新的优化...")

        # Create or load Optuna study
        study = optuna.create_study(
            study_name=study_name or f"{strategy_name}_optimization",
            storage=storage_url,
            direction=self.direction,
            load_if_exists=True  # Load if study_name already exists in storage
        )

        # Generate data once or per trial based on config (for simplicity, generate once here)
        data_generator = get_data_generator(self.config)
        simulated_data_df = data_generator.generate(base_data=base_data_df)

        study.optimize(
            lambda trial: self.objective(trial, StrategyClass, param_space, simulated_data_df.copy()),
            n_trials=self.trials
        )

        print(f"优化完成: {strategy_name}.")
        print(f"完成的试验数量: {len(study.trials)}")
        print(f"最佳试验 ({self.metric}):")
        
        best_trial = study.best_trial
        print(f"  值: {best_trial.value}")
        print("  参数: ")
        for key, value in best_trial.params.items():
            print(f"    {key}: {value}")
        
        # 保存优化结果
        self.save_optimization_results(strategy_name, study)
        
        return study

    def save_optimization_results(self, strategy_name: str, study: optuna.Study) -> None:
        """保存优化结果到JSON文件"""
        
        if hasattr(study, 'best_trial') and study.best_trial:
            results = {
                'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'strategy': strategy_name,
                'metric': self.metric,
                'trials': len(study.trials),
                'best_value': float(study.best_value) if not np.isnan(study.best_value) and not np.isinf(study.best_value) else "N/A",
                'best_params': dict(study.best_trial.params),
                'direction': self.direction
            }
            
            # 保存完整的trials信息
            trial_records = []
            for trial in study.trials:
                if trial.state == optuna.trial.TrialState.COMPLETE and not np.isnan(trial.value) and not np.isinf(trial.value):
                    trial_records.append({
                        'number': trial.number,
                        'params': trial.params,
                        'value': float(trial.value)
                    })
            
            results['trial_records'] = trial_records
            
            # 保存到文件
            file_path = os.path.join(self.results_dir, f"{strategy_name}_optimization_results.json")
            with open(file_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"优化结果已保存到: {file_path}")
        else:
            print("没有可保存的最佳结果")

    def _get_param_space(self, strategy_cls: Type[bt.Strategy]) -> Dict[str, Dict[str, Any]]:
        """
        从策略类中提取参数空间定义。
        期望策略的params是一个元组的元组，例如:
        params = (
            ('fast_period', 10, {'type': 'int', 'low': 5, 'high': 20}),
            ('slow_period', 30, {'type': 'int', 'low': 20, 'high': 50}),
        )
        或者，如果只有名称和默认值，则需要手动在config中定义范围。
        这里我们假设config中会提供详细的优化参数范围。
        """
        strategy_name = strategy_cls.__name__
        opt_params_config = self.config.get('optimization', {}).get('param_space', {}).get(strategy_name, None)

        if opt_params_config:
            return opt_params_config
        else:
            print(f"警告: 在配置中未找到 {strategy_name} 的详细参数空间。尝试进行基本推断。")
            space = {}
            if hasattr(strategy_cls, 'params') and isinstance(strategy_cls.params, tuple):
                for p_tuple in strategy_cls.params:
                    if isinstance(p_tuple, tuple) and len(p_tuple) >= 2:
                        name = p_tuple[0]
                        if isinstance(p_tuple[1], int):
                            space[name] = {'type': 'int', 'low': max(1, p_tuple[1] // 2), 'high': p_tuple[1] * 2}
                        elif isinstance(p_tuple[1], float):
                            space[name] = {'type': 'float', 'low': max(0.001, p_tuple[1] / 2), 'high': p_tuple[1] * 2}
            if not space:
                raise ValueError(f"无法确定 {strategy_name} 的参数空间。请在配置中定义它。")
            return space

    def objective(self,
                  trial: optuna.Trial,
                  strategy_cls: Type[bt.Strategy],
                  param_space: Dict[str, Dict[str, Any]],
                  data_df: pd.DataFrame,
                  ) -> float:
        """
        Optuna优化的目标函数

        参数:
            trial: Optuna trial对象
            strategy_cls: 要优化的策略类
            param_space: 参数空间定义
            data_df: 回测数据 (Pandas DataFrame)

        返回:
            优化指标的值 (e.g., Sharpe Ratio)
        """
        cerebro = bt.Cerebro()

        data_feed = bt.feeds.PandasData(dataname=data_df.copy())
        cerebro.adddata(data_feed)

        suggested_params = {}
        for name, p_config in param_space.items():
            param_type = p_config.get('type')
            if param_type == 'int':
                suggested_params[name] = trial.suggest_int(name, p_config['low'], p_config['high'], step=p_config.get('step', 1))
            elif param_type == 'float':
                suggested_params[name] = trial.suggest_float(name, p_config['low'], p_config['high'], step=p_config.get('step'))
            elif param_type == 'categorical':
                suggested_params[name] = trial.suggest_categorical(name, p_config['choices'])
            else:
                raise ValueError(f"不支持的参数类型 {param_type} (参数: {name})")

        cerebro.addstrategy(strategy_cls, **suggested_params)

        backtest_config = self.config.get('backtest', {})
        cerebro.broker.setcash(backtest_config.get('cash', 100000.0))
        cerebro.broker.setcommission(commission=backtest_config.get('commission', 0.001))

        cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', 
                           riskfreerate=0.0, annualize=True, timeframe=bt.TimeFrame.Days)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

        try:
            results = cerebro.run()
            strat = results[0]

            # 首先尝试使用PyFolio分析器
            if hasattr(strat.analyzers, 'pyfolio'):
                portfolio_values_dict = strat.analyzers.pyfolio.get_analysis().get('portfolio_value', {})
                if portfolio_values_dict:
                    portfolio_values = pd.Series(list(portfolio_values_dict.values()), 
                                               index=pd.to_datetime(list(portfolio_values_dict.keys())))

                    if not portfolio_values.empty and len(portfolio_values) >= 2:
                        freq = self.config.get('data_generator', {}).get('frequency', 'D')
                        periods_map = {'D': 252, 'H': 252 * 24, 'M': 252 * 24 * 60}
                        periods_per_year = periods_map.get(freq, 252)

                        all_metrics = calculate_metrics(portfolio_values, periods_per_year=periods_per_year)
                        metric_value = all_metrics.get(self.metric, None)
                        
                        # 确保返回有效值
                        if metric_value is not None and np.isfinite(metric_value):
                            print(f"试验 {trial.number} 参数: {suggested_params}, {self.metric}: {metric_value:.4f}")
                            return metric_value

            # 尝试使用特定分析器
            if self.metric == 'sharpe_ratio' and hasattr(strat.analyzers, 'sharpe'):
                sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0.0)
                if np.isfinite(sharpe):
                    print(f"试验 {trial.number} 参数: {suggested_params}, 夏普比率: {sharpe:.4f}")
                    return sharpe
                
            if self.metric == 'max_drawdown' and hasattr(strat.analyzers, 'drawdown'):
                max_dd = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)
                if np.isfinite(max_dd):
                    # 优化最小化回撤 (负值以便在最大化优化方向时使用)
                    return -max_dd / 100.0  # 转换为小数
                
            if self.metric == 'total_return' and hasattr(strat.analyzers, 'returns'):
                ret = strat.analyzers.returns.get_analysis().get('rtot', 0.0)
                if np.isfinite(ret): 
                    return ret
            
            # 如果所有方法都失败，则返回一个默认的无效值
            print(f"警告: 试验 {trial.number} 无法计算 {self.metric}, 返回无效值")
            return float('-inf') if self.direction == 'maximize' else float('inf')
            
        except Exception as e:
            print(f"试验 {trial.number} 出错, 参数 {suggested_params}: {e}")
            return float('-inf') if self.direction == 'maximize' else float('inf')
