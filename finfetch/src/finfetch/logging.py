import logging
import sys

def configure_logging(level=logging.INFO):
    """Configure logging to stderr"""
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()
        
    root_logger.addHandler(handler)
