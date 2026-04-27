"""Простой логгер для бэктеста"""
import logging
import os
from datetime import datetime

def setup_logger():
    """Настройка логгера"""
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Имя файла с датой и временем
    log_file = os.path.join(
        logs_dir, 
        f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    
    logger = logging.getLogger("backtest")
    logger.setLevel(logging.INFO)
    
    # Очищаем старые обработчики
    if logger.handlers:
        logger.handlers.clear()
    
    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Файловый обработчик
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Глобальный логгер
logger = setup_logger()