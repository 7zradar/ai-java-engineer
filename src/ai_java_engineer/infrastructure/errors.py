"""Core exception hierarchy for the AI Java Engineer platform."""

from typing import Any


class PlatformError(Exception):
    """Root class for all application errors with structured error codes."""

    def __init__(self, message: str, code: str = "E500", details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(PlatformError):
    """Raised when application settings are invalid or missing."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="E101", details=details)


class SecurityViolationError(PlatformError):
    """Raised when an operation violates security boundaries or permissions."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="E007", details=details)


class PathOutOfBoundsError(SecurityViolationError):
    """Raised when an agent attempts to access a path outside the workspace boundary."""

    def __init__(self, path: str, workspace_root: str):
        super().__init__(
            f"Access denied: Path '{path}' resolves outside workspace root '{workspace_root}'",
            details={"requested_path": path, "workspace_root": workspace_root},
        )


class BudgetExceededError(PlatformError):
    """Raised when execution limits (tokens, API calls, time) are breached."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="E102", details=details)


class ExecutionBackendError(PlatformError):
    """Raised when remote or local execution fails unexpectedly."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="E009", details=details)
