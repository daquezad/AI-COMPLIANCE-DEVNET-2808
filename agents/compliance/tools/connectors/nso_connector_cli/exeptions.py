class NSOCLIError(Exception):
    """Base exception for NSO operations."""
    pass

class NSOCLIConnectionError(NSOCLIError):
    """Raised when pyATS cannot connect to NSO."""
    pass

class NSOCLICommandError(NSOCLIError):
    """Raised when NSO returns an error for a command."""
    pass