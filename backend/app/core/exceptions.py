class AppError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "An unexpected error occurred") -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message)


class ConflictError(AppError):
    status_code = 409
    error_code = "CONFLICT"

    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(message)


class ForbiddenError(AppError):
    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message)


class ValidationError(AppError):
    status_code = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message)


class PaymentError(AppError):
    status_code = 402
    error_code = "PAYMENT_ERROR"

    def __init__(self, message: str = "Payment processing failed") -> None:
        super().__init__(message)


class AIServiceError(AppError):
    status_code = 503
    error_code = "AI_SERVICE_ERROR"

    def __init__(self, message: str = "AI service unavailable") -> None:
        super().__init__(message)


class ExternalServiceError(AppError):
    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, message: str = "External service error") -> None:
        super().__init__(message)
