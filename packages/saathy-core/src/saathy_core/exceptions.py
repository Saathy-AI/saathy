"""Core exception classes for Saathy."""

from typing import Any, Optional


class SaathyException(Exception):
    """Base exception for all Saathy errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConnectorException(SaathyException):
    """Exception raised by connectors."""
    
    def __init__(
        self,
        connector_name: str,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)
        self.connector_name = connector_name
        self.details["connector"] = connector_name


class ProcessingException(SaathyException):
    """Exception raised during content processing."""
    
    def __init__(
        self,
        processor_name: str,
        message: str,
        content_id: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)
        self.processor_name = processor_name
        self.content_id = content_id
        self.details["processor"] = processor_name
        if content_id:
            self.details["content_id"] = content_id


class EmbeddingException(SaathyException):
    """Exception raised during embedding generation."""
    
    def __init__(
        self,
        model_name: str,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)
        self.model_name = model_name
        self.details["model"] = model_name


class VectorStoreException(SaathyException):
    """Exception raised by vector stores."""
    
    def __init__(
        self,
        store_name: str,
        operation: str,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)
        self.store_name = store_name
        self.operation = operation
        self.details["store"] = store_name
        self.details["operation"] = operation


class ConfigurationException(SaathyException):
    """Exception raised for configuration errors."""
    
    def __init__(
        self,
        config_key: str,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)
        self.config_key = config_key
        self.details["config_key"] = config_key


class AuthenticationException(SaathyException):
    """Exception raised for authentication errors."""
    
    def __init__(
        self,
        service: str,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)
        self.service = service
        self.details["service"] = service


class RateLimitException(SaathyException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(
        self,
        service: str,
        retry_after: Optional[int] = None,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        msg = message or f"Rate limit exceeded for {service}"
        super().__init__(msg, error_code, details)
        self.service = service
        self.retry_after = retry_after
        self.details["service"] = service
        if retry_after:
            self.details["retry_after"] = retry_after


class FeatureNotAvailableException(SaathyException):
    """Exception raised when accessing enterprise features without license."""
    
    def __init__(
        self,
        feature_name: str,
        required_tier: str = "enterprise",
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        msg = message or f"Feature '{feature_name}' requires {required_tier} license"
        super().__init__(msg, error_code, details)
        self.feature_name = feature_name
        self.required_tier = required_tier
        self.details["feature"] = feature_name
        self.details["required_tier"] = required_tier