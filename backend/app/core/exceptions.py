class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str = "app_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ConfigurationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="configuration_error")


class ExtractionError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="extraction_error")


class NotFoundError(AppError):
    def __init__(self, resource: str, id_value: str) -> None:
        super().__init__(f"{resource} not found: {id_value}", code="not_found")
