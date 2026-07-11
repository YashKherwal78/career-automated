import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name: str) -> logging.Logger:
    """Creates a structured logger that writes to file and console."""
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.INFO)
    os.makedirs('logs', exist_ok=True)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 1. Pipeline Log (Everything)
    pipeline_handler = RotatingFileHandler('logs/pipeline.log', maxBytes=5*1024*1024, backupCount=3)
    pipeline_handler.setLevel(logging.INFO)
    pipeline_handler.setFormatter(formatter)
    
    # 2. Daily Log (Routine)
    daily_handler = RotatingFileHandler('logs/daily.log', maxBytes=5*1024*1024, backupCount=5)
    daily_handler.setLevel(logging.INFO)
    daily_handler.setFormatter(formatter)
    
    # 3. Error Log
    error_handler = RotatingFileHandler('logs/errors.log', maxBytes=5*1024*1024, backupCount=5)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # 4. Console Log
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(pipeline_handler)
    logger.addHandler(daily_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    return logger
