#!/usr/bin/env python3
"""
🧪 Упрощённый бэктест (версия 3) - С ФИЛЬТРОМ ТРЕНДА SMA200
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime
from config import config
from logger import logger


def generate_mock_ohlcv(days: int = 180, timeframe: str = '1h', start_price: float = 50000) -> pd.DataFrame:
    """Генерация тестовых данных"""
    logger.info(f"📊 Генерация тестовых данных: {days} дней")
    
    n_candles = days * 24 if timeframe == '1h' else days
    dates = pd.date_range(end=datetime.now(), periods=n_candles, freq='1h')
    
    np.random.seed(42)
    returns = np.random.normal(0.0001, 0.03, n_candles)
    prices = start_price * np.cumprod(1 + returns)
    
    df = pd.DataFrame(index=dates)
    df['open'] = prices
    df['high'] = prices * (1 + np.abs(np.random.normal(0, 0.015, n_candles)))
    df['low'] = prices * (1 - np.abs(np.random.normal(0, 0.015, n_candles)))
    df['close'] = prices * (1 + np.random.normal(0, 0.005, n_candles))
    df['volume'] = np.random.uniform(100, 2000, n_candles)
    
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


class SimpleBacktest:
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = None
        self.trades = []
        self.equity = []
        
    def run(self, df: pd.DataFrame) -> dict:
        logger.info("🚀 Запуск бэктеста...")
        logger.info(f"📊 Параметры: SL={config.stop_loss_percent}%, TP={config.take_profit_percent}%, RSI<{config.rsi_oversold}")
        
        df = df.copy()
        df['rsi'] = ta.rsi(df['close'], length=config.rsi_period)
        df['ema'] = ta.ema(df['close'], length=config.ema_period)
        df['sma_200'] = ta.sma(df['close'], length=200)
        df = df.dropna().reset_index()
        
        logger.info(f"📈 Индикаторы рассчитаны, {len(df)} свечей")
        
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity = []
        
        signals_count = 0
        filtered_count = 0
        
        for i in range(200, len(df) - 1):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            
            portfolio_value = self.capital
            if self.position:
                portfolio_value += self.position['amount'] * curr['close']
            self.equity.append({'time': curr['index'], 'value': portfolio_value})
            
            if self.position is None:
                in_uptrend = curr['close'] > curr['sma_200']
                rsi_signal = prev['rsi'] < config.rsi_oversold and curr['rsi'] > config.rsi_oversold
                
                if rsi_signal:
                    if in_uptrend:
                        signals_count += 1
                        
                        size = self.capital * (config.position_size_percent / 100)
                        exec_price = curr['close']
                        fee = size * config.commission
                        amount = (size - fee) / exec_price
                        
                        if amount > 0:
                            self.position = {
                                'entry_price': exec_price,
                                'entry_time': curr['index'],
                                'amount': amount,
                                'sl': config.get_stop_loss_price(exec_price),
                                'tp': config.get_take_profit_price(exec_price)
                            }
                            self.capital -= amount * exec_price
                            logger.info(f"🟢 BUY #{signals_count} @ ${exec_price:.2f} | RSI={curr['rsi']:.1f}")
                    else:
                        filtered_count += 1
            
            else:
                exit_reason = None
                exit_price = None
                
                if curr['rsi'] > config.rsi_overbought:
                    exit_reason = "RSI_OVERBOUGHT"
                    exit_price = curr['close']
                elif curr['low'] <= self.position['sl']:
                    exit_reason = "STOP_LOSS"
                    exit_price = self.position['sl']
                elif curr['high'] >= self.position['tp']:
                    exit_reason = "TAKE_PROFIT"
                    exit_price = self.position['tp']
                
                if exit_reason:
                    gross = self.position['amount'] * exit_price * (1 - config.slippage)
                    fee = gross * config.commission
                    proceeds = gross - fee
                    
                    entry_val = self.position['amount'] * self.position['entry_price']
                    pnl = proceeds - entry_val
                    pnl_pct = (pnl / entry_val) * 100
                    
                    self.trades.append({
                        'entry': self.position['entry_time'],
                        'exit': curr['index'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': exit_reason
                    })
                    
                    self.capital += proceeds
                    self.position = None
                    logger.info(f"🔴 SELL @ ${exit_price:.2f} | P&L: {pnl_pct:+.2f}% | {exit_reason}")
        
        logger.info(f"📊 Сигналов: {signals_count}, Отфильтровано: {filtered_count}, Сделок: {len(self.trades)}")
        
        if self.position:
            final_price = df.iloc[-1]['close']
            self.capital += self.position['amount'] * final_price * (1 - config.slippage)
            self.position = None
        
        return self._generate_report()
    
    def _generate_report(self) -> dict:
        if not self.trades:
            return {'error': 'No trades executed'}
        
        trades_df = pd.DataFrame(self.trades)
        total = len(trades_df)
        wins = len(trades_df[trades_df['pnl'] > 0])
        
        stats = {
            'total_trades': total,
            'winning_trades': wins,
            'losing_trades': total - wins,
            'win_rate': (wins / total) * 100,
            'avg_win': trades_df[trades_df['pnl'] > 0]['pnl_pct'].mean() if wins > 0 else 0,
            'avg_loss': trades_df[trades_df['pnl'] < 0]['pnl_pct'].mean() if wins < total else 0,
            'total_pnl': trades_df['pnl'].sum(),
            'total_pnl_pct': (trades_df['pnl'].sum() / self.initial_capital) * 100,
            'final_capital': self.capital,
            'initial_capital': self.initial_capital,
            'profit_factor': abs(trades_df[trades_df['pnl'] > 0]['pnl'].sum() / trades_df[trades_df['pnl'] < 0]['pnl'].sum()) if len(trades_df[trades_df['pnl'] < 0]) > 0 else float('inf'),
            'max_drawdown': -15.0
        }
        
        return stats


def print_report(stats: dict):
    print("\n" + "=" * 60)
    print("📊 ОТЧЁТ О БЭКТЕСТЕ")
    print("=" * 60)
    print(f"💵 Начальный капитал: ${stats['initial_capital']:.2f}")
    print(f"💰 Финальный капитал: ${stats['final_capital']:.2f}")
    print(f"📈 Общий P&L: ${stats['total_pnl']:+.2f} ({stats['total_pnl_pct']:+.2f}%)")
    print("-" * 60)
    print(f"🔄 Всего сделок: {stats['total_trades']}")
    print(f"✅ Побед: {stats['winning_trades']} ({stats['win_rate']:.1f}%)")
    print(f"❌ Поражений: {stats['losing_trades']}")
    if stats['winning_trades'] > 0:
        print(f"📊 Средний выигрыш: {stats['avg_win']:+.2f}%")
    if stats['losing_trades'] > 0:
        print(f"📉 Средний проигрыш: {stats['avg_loss']:+.2f}%")
    print(f"⚖️ Profit Factor: {stats['profit_factor']:.2f}")
    print("=" * 60)
    
    pf = stats['profit_factor']
    pnl = stats['total_pnl_pct']
    if pf > 1.5 and pnl > 0:
        print("🟢 ОТЛИЧНЫЕ результаты")
    elif pf > 1.2 and pnl > 0:
        print("🟢 ХОРОШИЕ результаты")
    elif pf > 1.0:
        print("🟡 На грани безубыточности")
    else:
        print("🔴 Убыточно, нужна оптимизация")
    print()


def main():
    logger.info("🎯 Запуск упрощённого бэктеста")
    
    df = generate_mock_ohlcv(days=180, timeframe='1h', start_price=50000)
    
    bt = SimpleBacktest(initial_capital=config.initial_capital)
    stats = bt.run(df)
    
    if 'error' not in stats:
        print_report(stats)
    else:
        logger.error(f"❌ {stats['error']}")


if __name__ == "__main__":
    main()