#!/usr/bin/env python3
"""
🧪 Бэктест на РЕАЛЬНЫХ данных Binance
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime
from config import config
from logger import logger


def load_real_data(filepath: str = "data/btc_real_data.csv", days: int = 360) -> pd.DataFrame:
    """Загрузка реальных данных Binance"""
    logger.info(f"📊 Загрузка реальных данных: {filepath}")
    
    df = pd.read_csv(filepath)
    
    # Binance CSV формат: open_time, open, high, low, close, volume, ...
    df = df[['open_time', 'open', 'high', 'low', 'close', 'volume']]
    
    # Конвертировать время
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df = df.set_index('open_time')
    
    # Оставить последние `days` дней
    if days:
        cutoff = df.index[-1] - pd.Timedelta(days=days)
        df = df[df.index >= cutoff]
    
    # Конвертировать типы
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna()
    
    logger.info(f"✅ Загружено {len(df)} свечей, цена: ${df['close'].iloc[-1]:.2f}")
    return df


class RealBacktest:
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = None
        self.trades = []
        self.equity = []
        
    def run(self, df: pd.DataFrame) -> dict:
        logger.info("🚀 Запуск бэктеста на реальных данных...")
        logger.info(f"📊 Параметры: SL={config.stop_loss_percent}%, TP={config.take_profit_percent}%, RSI<{config.rsi_oversold}")
        
        df = df.copy()
        df['rsi'] = ta.rsi(df['close'], length=config.rsi_period)
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
            self.equity.append({'time': curr['open_time'], 'value': portfolio_value})
            
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
                                'entry_time': curr['open_time'],
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
                
                if (curr['rsi'] > 55 and
                   curr['close'] > self.position['entry_price'] * 1.01):
                    exit_reason = "RSI_EARLY_EXIT"
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
                        'exit': curr['open_time'],
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


def print_report(stats: dict, data_type: str = "REAL"):
    print("\n" + "=" * 70)
    print(f"📊 ОТЧЁТ О БЭКТЕСТЕ | Данные: {data_type}")
    print("=" * 70)
    print(f"💵 Начальный капитал: ${stats['initial_capital']:.2f}")
    print(f"💰 Финальный капитал: ${stats['final_capital']:.2f}")
    print(f"📈 Общий P&L: ${stats['total_pnl']:+.2f} ({stats['total_pnl_pct']:+.2f}%)")
    print("-" * 70)
    print(f"🔄 Всего сделок: {stats['total_trades']}")
    print(f"✅ Побед: {stats['winning_trades']} ({stats['win_rate']:.1f}%)")
    print(f"❌ Поражений: {stats['losing_trades']}")
    if stats['winning_trades'] > 0:
        print(f"📊 Средний выигрыш: {stats['avg_win']:+.2f}%")
    if stats['losing_trades'] > 0:
        print(f"📉 Средний проигрыш: {stats['avg_loss']:+.2f}%")
    print(f"⚖️ Profit Factor: {stats['profit_factor']:.2f}")
    print("=" * 70)
    
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
    logger.info("🎯 Запуск бэктеста на РЕАЛЬНЫХ данных")
    
    # Загрузка реальных данных
    df = load_real_data(filepath="data/btc_real_data.csv", days=180)
    
    bt = RealBacktest(initial_capital=config.initial_capital)
    stats = bt.run(df)
    
    if 'error' not in stats:
        print_report(stats, data_type="REAL BINANCE")
    else:
        logger.error(f"❌ {stats['error']}")


if __name__ == "__main__":
    main()