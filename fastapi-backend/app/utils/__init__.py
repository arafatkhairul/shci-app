"""
Utilities Package
"""
from .logger import get_logger, log_exception, log

# Helper functions (if needed, can be added later)
def parse_grammar_correction(text: str) -> str:
    """Parse grammar correction from text"""
    return text

def extract_organization_info(text: str) -> dict:
    """Extract organization information from text"""
    return {"text": text}

__all__ = ["get_logger", "log_exception", "log", "parse_grammar_correction", "extract_organization_info"]

