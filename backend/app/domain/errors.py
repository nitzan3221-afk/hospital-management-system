"""Domain errors. The service layer raises these; the API layer maps them to HTTP status codes."""


class DomainError(Exception):
    """Base class for all expected, business-level errors."""


class NotFoundError(DomainError):
    """The requested entity does not exist."""


class AlreadyExistsError(DomainError):
    """An entity with the same identifier already exists."""


class InvalidOperationError(DomainError):
    """The operation is not valid in the entity's current state."""


class AuthenticationError(DomainError):
    """Invalid credentials or token."""


class PermissionDeniedError(DomainError):
    """The user is authenticated but not allowed to perform the action."""
