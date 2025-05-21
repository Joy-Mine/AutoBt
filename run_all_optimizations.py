import yaml
import json
import os
import pandas as pd
import copy

# 导入 run_optimization 函数
from run_optimization import run_optimization

def main():
    # 1. 加载基础配置
    config_path = 'config/config.yaml'
    with open(config_path, 'r') as file:
        base_config = yaml.safe_load(file)

    # 2. 定义数据模式和策略列表
    data_modes = [
        'monte_carlo',
        'garch',
        'regime',
        'extreme',
        'multi_asset',
        'stress_test'
    ]

    # 从配置中获取所有定义的策略
    strategies = list(base_config.get('strategies', {}).keys())
    # 移除非策略键，例如 'type'
    strategies = [s for s in strategies if s != 'type']

    # 存储结果的列表
    all_results = []

    # 3. 遍历所有组合
    for data_mode in data_modes:
        for strategy_name in strategies:
            print(f"\n{'*'*80}")
            print(f"正在优化组合: 数据模式={data_mode}, 策略={strategy_name}")
            print(f"{'*'*80}")

            # 4. 动态修改配置
            current_config = copy.deepcopy(base_config)
            current_config['data_generator']['type'] = data_mode

            # 注意: run_optimization 函数会尝试加载 results 目录下的 json 文件
            # 为了避免不同数据模式/策略组合之间结果混淆，或者强制重新优化，
            # 可以在调用 run_optimization 时设置 force_optimize=True
            # 或者修改结果文件的命名逻辑（如果 run_optimization 支持）
            # 当前 run_optimization 默认命名是 {strategy_name}_optimization_results.json
            # 这意味着如果不同数据模式使用同一个策略，它们会覆盖结果文件。
            # 为了得到每个组合独立的结果，我们将设置 force_optimize=True。

            try:
                # 5. 调用 run_optimization 函数
                # run_optimization 返回一个字典，包含 'best_value' 和 'best_params'
                # 我们强制重新优化以确保每个组合结果独立
                results = run_optimization(current_config, strategy_name, force_optimize=True)

                # 6. 收集结果
                all_results.append({
                    '数据模式': data_mode,
                    '策略': strategy_name,
                    '最佳指标值': results.get('best_value', 'N/A'),
                    '最佳参数': results.get('best_params', {})
                })

            except Exception as e:
                print(f"优化组合失败 (数据模式={data_mode}, 策略={strategy_name}): {e}")
                all_results.append({
                    '数据模式': data_mode,
                    '策略': strategy_name,
                    '最佳指标值': 'Error',
                    '最佳参数': 'Error'
                })

    # 7. 将结果整理成表格
    results_df = pd.DataFrame(all_results)

    # 打印结果表格
    print("\n" + "="*80)
    print("所有优化组合结果")
    print("="*80)
    print(results_df.to_string())

    # 可以选择将结果保存到 CSV 文件
    # results_df.to_csv('all_optimizations_summary.csv', index=False)
    # print("\n结果已保存到 all_optimizations_summary.csv")

if __name__ == "__main__":
    main() 