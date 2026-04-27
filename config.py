"""Конфигурация для бэктеста"""
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    # Торговые настройки
    trading_pair = os.getenv('TRADING_PAIR', 'BTC/USDT')
    timeframe = os.getenv('TIMEFRAME', '1h')
    
    # Параметры стратегии
    rsi_period = int(os.getenv('RSI_PERIOD', '14'))
    ema_period = int(os.getenv('EMA_PERIOD', '50'))
    rsi_oversold = int(os.getenv('RSI_OVERSOLD', '30'))
    rsi_overbought = int(os.getenv('RSI_OVERBOUGHT', '70'))
    
    # Управление рисками
    position_size_percent = float(os.getenv('POSITION_SIZE_PERCENT', '5'))
    stop_loss_percent = float(os.getenv('STOP_LOSS_PERCENT', '3'))
    take_profit_percent = float(os.getenv('TAKE_PROFIT_PERCENT', '6'))
    
    # Комиссии и проскальзывание
    commission = float(os.getenv('COMMISSION', '0.001'))
    slippage = float(os.getenv('SLIPPAGE', '0.0005'))
    
    # Капитал
    initial_capital = float(os.getenv('INITIAL_CAPITAL', '10000'))
    
    @staticmethod
    def get_stop_loss_price(entry_price: float) -> float:
        """Расчёт цены стоп-лосса"""
        return entry_price * (1 - Config.stop_loss_percent / 100)
    
    @staticmethod
    def get_take_profit_price(entry_price: float) -> float:
        """Расчёт цены тейк-профита"""
        return entry_price * (1 + Config.take_profit_percent / 100)

# Глобальный экземпляр
config = Config()