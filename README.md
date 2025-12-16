# Backtesting Platform for Trading Strategies

A modular and extensible framework for backtesting trading strategies in Python.

## Overview

This platform provides a comprehensive solution for developing, testing, and optimizing trading strategies. It features:

- Modular architecture for easy strategy development
- Built-in technical indicators
- Performance metrics calculation
- Parameter optimization tools
- Support for custom strategies

## Installation

```bash
pip install -e .
```

## Usage

### Basic Example

```python
from backtest_platform.core.backtester import Backtester
from backtest_platform.strategies.dual_momentum import DualMomentumStrategy

# Create a strategy
strategy = DualMomentumStrategy(lookback_period=20)

# Create a backtester
backtester = Backtester(strategy, initial_capital=10000)

# Load data
backtester.load_data('path/to/your/data.csv')

# Run backtest
results = backtester.run_backtest()

# View results
print(results)
```

### Running the Example

```bash
python -m backtest_platform.run_example
```

## Project Structure

```
backtest_platform/
├── core/
│   ├── __init__.py
│   ├── base_strategy.py
│   ├── backtester.py
│   └── metrics.py
├── strategies/
│   ├── __init__.py
│   ├── dual_momentum.py
│   └── rsi_strategy.py
├── indicators/
│   ├── __init__.py
│   └── volatility.py
├── data/
│   └── sample_data.csv
├── optimizer.py
├── utils.py
└── run_example.py
```

### Core Module
- `base_strategy.py`: Abstract base class for all trading strategies
- `backtester.py`: Main backtesting engine
- `metrics.py`: Performance metrics calculation

### Strategies Module
- `dual_momentum.py`: Implementation of dual momentum strategy
- `rsi_strategy.py`: Implementation of RSI-based strategy

### Indicators Module
- `volatility.py`: Technical indicators including RSI, moving averages, etc.

## Creating Custom Strategies

To create a custom strategy, inherit from `BaseStrategy` and implement the required methods:

```python
from backtest_platform.core.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        # Initialize your strategy parameters here
        
    def calculate_signal(self, data_point):
        # Implement your signal calculation logic here
        # Return -1 for sell, 0 for hold, 1 for buy
        pass
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
