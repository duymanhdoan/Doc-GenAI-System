"""
Custom Exceptions
"""


class DocGenAIException(Exception):
    """Base exception for all custom exceptions"""
    pass


class ModelNotFoundError(DocGenAIException):
    """Model not found"""
    pass


class PredictionError(DocGenAIException):
    """Prediction error"""
    pass


class DocumentProcessingError(DocGenAIException):
    """Document processing error"""
    pass


class AuthenticationError(DocGenAIException):
    """Authentication error"""
    pass


class AuthorizationError(DocGenAIException):
    """Authorization error"""
    pass


class RateLimitError(DocGenAIException):
    """Rate limit exceeded"""
    pass


class ValidationError(DocGenAIException):
    """Validation error"""
    pass


class StorageError(DocGenAIException):
    """Storage error"""
    pass


class DatabaseError(DocGenAIException):
    """Database error"""
    pass
