class AppException(Exception):
    """所有自定义异常的基类。"""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ConfigError(AppException):
    error_code = "CONFIG_ERROR"
    status_code = 500


class LLMServiceError(AppException):
    error_code = "LLM_SERVICE_ERROR"
    status_code = 502


class VectorStoreError(AppException):
    error_code = "VECTOR_STORE_ERROR"
    status_code = 502


class NotFoundError(AppException):
    error_code = "NOT_FOUND"
    status_code = 404


class PermissionDeniedError(AppException):
    error_code = "PERMISSION_DENIED"
    status_code = 403


class ValidationError(AppException):
    error_code = "VALIDATION_ERROR"
    status_code = 400
