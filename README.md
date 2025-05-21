# AutoBt - 基于模拟数据的量化交易智能回测系统

这是一个基于模拟数据的量化交易智能回测系统，专为解决传统回测中的数据局限性问题而设计。

## 核心功能

- **模拟数据生成器** - 灵活生成多种市场环境下的模拟数据
- **参数优化器** - 使用optuna自动寻找最优策略参数
- **自动化回测系统** - 基于backtrader的高效回测框架，自动处理模拟数据的生成和回测，支持参数优化（基于optuna），生成详细的回测报告和图表

## 模拟数据生成器

解决策略依赖于历史数据的局限性：
- 历史数据有限
- 过拟合风险
- 难以模拟极端市场情况
- 难以进行统计显著性分析

支持的数据生成模式：
- **蒙特卡洛模拟 (GBM)** - 基于几何布朗运动
- **GARCH模型** - 模拟波动率聚集效应
- **极端事件模拟** - 模拟市场崩盘等黑天鹅事件
- **市场状态转换模型** - 模拟牛熊市场切换
- **多资产相关性模拟** - 生成具有特定相关性的多资产数据
- **压力测试模拟** - 专门测试极端市场环境下的策略表现

## 内置交易策略

系统提供多种策略模板，可在不同市场环境下测试：
- **简单移动平均策略** (SampleStrategy)
- **双均线策略** (DualMovingAverageStrategy)
- **均值回归策略** (MeanReversionStrategy)
- **动量策略** (MomentumStrategy)

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行回测

```bash
python main.py --mode backtest
```

### 运行参数优化

```bash
python main.py --mode optimize
```

## 配置说明

所有参数可在`config/config.yaml`中配置，包括：
- 数据生成器参数
- 回测参数
- 策略参数
- 优化参数

### 命令行参数

系统支持以下命令行参数，方便灵活配置：

```
usage: main.py [-h] [--config CONFIG] [--mode {backtest,optimize}]
               [--data-generator {monte_carlo,garch,regime,extreme,multi_asset,stress_test}]
               [--strategy {SampleStrategy,DualMovingAverageStrategy,MeanReversionStrategy,MomentumStrategy}]

选项:
  -h, --help            显示帮助信息
  --config CONFIG       配置文件路径 (默认: config/config.yaml)
  --mode {backtest,optimize}
                        运行模式: backtest(回测)或optimize(优化) (默认: backtest)
  --data-generator {...} 
                        数据生成器类型，覆盖配置文件中的设置
  --strategy {...}      
                        策略类型，覆盖配置文件中的设置
```

命令组合示例：

```bash
# 使用蒙特卡洛数据生成器和均值回归策略进行回测
python main.py --data-generator monte_carlo --strategy MeanReversionStrategy

# 使用压力测试数据生成器和动量策略进行回测
python main.py --data-generator stress_test --strategy MomentumStrategy

# 使用多资产相关性数据生成器和双均线策略进行回测
python main.py --data-generator multi_asset --strategy DualMovingAverageStrategy

# 使用极端事件模拟和简单移动平均策略进行回测
python main.py --data-generator extreme --strategy SampleStrategy

# 使用GARCH模型和均值回归策略进行回测
python main.py --data-generator garch --strategy MeanReversionStrategy

# 使用蒙特卡洛数据生成器和双均线策略进行参数优化
python main.py --mode optimize --data-generator monte_carlo --strategy DualMovingAverageStrategy

# 使用市场状态转换模型和动量策略进行参数优化
python main.py --mode optimize --data-generator regime --strategy MomentumStrategy
```
