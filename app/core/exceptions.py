class AuthorizationError(Exception):
    """Raised when a user cannot perform an action."""


class ValidationError(Exception):
    """Raised when data fails deterministic checks."""


class LowConfidenceError(Exception):
    """Raised when model output falls below required confidence."""

