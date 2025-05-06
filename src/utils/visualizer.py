import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Optional

def plot_equity_curve(portfolio_values: pd.Series, title: str = "Equity Curve", save_path: Optional[str] = None) -> None:
    """
    绘制权益曲线
    
    参数:
        portfolio_values: 投资组合价值序列 (pandas Series)
        title: 图表标题
        save_path: 可选，保存图片的路径
    """
    if portfolio_values.empty:
        print("Cannot plot equity curve: portfolio_values is empty.")
        return
    plt.figure(figsize=(10, 6))
    portfolio_values.plot()
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value")
    plt.grid(True)
    if save_path:
        plt.savefig(save_path)
        print(f"Equity curve saved to {save_path}")
    else:
        plt.show()

def plot_drawdown(portfolio_values: pd.Series, title: str = "Drawdown", save_path: Optional[str] = None) -> None:
    """
    绘制回撤曲线
    
    参数:
        portfolio_values: 投资组合价值序列 (pandas Series)
        title: 图表标题
        save_path: 可选，保存图片的路径
    """
    if portfolio_values.empty:
        print("Cannot plot drawdown: portfolio_values is empty.")
        return
    cumulative_max = portfolio_values.cummax()
    drawdown = (portfolio_values - cumulative_max) / cumulative_max
    
    plt.figure(figsize=(10, 6))
    drawdown.plot(kind='area', color='red', alpha=0.3)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Drawdown")
    plt.grid(True)
    if save_path:
        plt.savefig(save_path)
        print(f"Drawdown plot saved to {save_path}")
    else:
        plt.show()

def plot_optimization_results(study: 'optuna.study.Study', 
                             param_names: List[str], 
                             metric_name: str = "Sharpe Ratio", 
                             save_path: Optional[str] = None) -> None:
    """
    绘制优化结果 (例如，参数与目标指标的关系图)
    
    参数:
        study: Optuna study对象
        param_names: 要绘制的参数名称列表
        metric_name: 指标名称
        save_path: 可选，保存图片的路径
    """
    try:
        import optuna.visualization as vis
    except ImportError:
        print("Optuna visualization is not available. Please install it: pip install optuna-dashboard")
        return

    if not study.trials:
        print("No trials to plot for optimization results.")
        return

    # Plot parameter importance
    try:
        fig_importance = vis.plot_param_importances(study)
        fig_importance.show()
        if save_path:
            fig_importance.write_image(save_path.replace('.png', '_importance.png'))
    except Exception as e:
        print(f"Could not plot parameter importance: {e}")

    # Plot optimization history
    try:
        fig_history = vis.plot_optimization_history(study)
        fig_history.show()
        if save_path:
            fig_history.write_image(save_path.replace('.png', '_history.png'))
    except Exception as e:
        print(f"Could not plot optimization history: {e}")

    # Plot slice for each parameter
    for param_name in param_names:
        try:
            fig_slice = vis.plot_slice(study, params=[param_name])
            fig_slice.show()
            if save_path:
                fig_slice.write_image(save_path.replace('.png', f'_slice_{param_name}.png'))
        except Exception as e:
            print(f"Could not plot slice for {param_name}: {e}")

    if save_path:
        print(f"Optimization plots saved near {save_path}")

# Example usage (requires optuna study object)
# if __name__ == '__main__':
#     import optuna
#     def objective(trial):
#         x = trial.suggest_float('x', -10, 10)
#         y = trial.suggest_int('y', 0, 5)
#         return (x - 2) ** 2 + (y - 1)**2

#     study = optuna.create_study(direction='minimize')
#     study.optimize(objective, n_trials=50)
#     plot_optimization_results(study, param_names=['x', 'y'], metric_name='Objective Value', save_path='./optimization_plots.png')

#     # Example for equity and drawdown plots
#     idx = pd.date_range('2020-01-01', periods=100, freq='D')
#     data = np.random.randn(100).cumsum() + 100
#     portfolio_values_example = pd.Series(data, index=idx)
#     plot_equity_curve(portfolio_values_example, save_path='./equity_curve.png')
#     plot_drawdown(portfolio_values_example, save_path='./drawdown_plot.png')
