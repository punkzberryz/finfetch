import json
import traceback

class FinFetchError(Exception):
    """Base exception for finfetch"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ValidationError(FinFetchError):
    """Input validation errors"""
    pass

class ProviderError(FinFetchError):
    """External provider errors"""
    pass

class UnknownError(FinFetchError):
    """Unexpected errors"""
    pass

def format_error(e: Exception) -> str:
    """Format exception as JSON string per RULES.md"""
    
    if isinstance(e, FinFetchError):
        error_type = e.__class__.__name__
        message = e.message
        details = e.details
    else:
        error_type = "UnknownError"
        message = str(e)
        details = {
            "traceback": traceback.format_exc().splitlines()
        }

    payload = {
        "ok": False,
        "error": {
            "type": error_type,
            "message": message,
            "details": details
        },
        "meta": {
            "version": 1
        }
    }
    
    return json.dumps(payload, indent=2)
