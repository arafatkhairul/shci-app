"""
Logging Configuration and Utilities
"""
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module"""
    return logging.getLogger(name)

def log_exception(logger: logging.Logger, where: str, e: Exception):
    """Log an exception with full traceback"""
    tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    logger.error(f"[EXC] {where}: {e}\n{tb}")

# Main application logger
log = get_logger("main")

