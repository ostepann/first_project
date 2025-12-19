#!/bin/bash

# Скрипт для запуска проекта backtest_platform

echo "Запуск проекта backtest_platform..."
cd /workspace/backtest_platform || { echo "Ошибка: директория /workspace/backtest_platform не найдена"; exit 1; }

python run_example.py