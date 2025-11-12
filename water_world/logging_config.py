import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(logger_name=None):
    """
    Setup logging configuration that can be shared across modules.
    
    Parameters:
    - logger_name: Name for the logger (defaults to the calling module's name)
    
    Returns:
    - Logger instance
    """
    # Single line to set logging level for all components
    LOG_LEVEL = logging.INFO
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure root logger only once
    root_logger = logging.getLogger()
    if not root_logger.handlers:  # Only configure if not already configured
        root_logger.setLevel(LOG_LEVEL)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            'logs/water_world.log',  # Shared log file
            maxBytes=1000*1024*1024,  # 1GB
            backupCount=5
        )
        file_handler.setLevel(LOG_LEVEL)
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOG_LEVEL)
        console_handler.setFormatter(formatter)
        
        # Add handlers to root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    # Create and return logger for specific module
    if logger_name is None:
        logger_name = __name__
    
    logger = logging.getLogger(logger_name)
    return logger 