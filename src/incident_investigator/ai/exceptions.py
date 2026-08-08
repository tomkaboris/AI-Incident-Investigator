class AIProviderError(Exception):
    """Base exception raised by an AI provider integration."""


class AIAuthenticationError(AIProviderError):
    """The configured provider rejected its credentials."""


class AIRateLimitError(AIProviderError):
    """The configured provider rate-limited the request."""


class AIQuotaError(AIProviderError):
    """The configured provider has no available quota."""


class AIConfigurationError(AIProviderError):
    """The selected provider is not configured correctly."""


class AIResponseError(AIProviderError):
    """The provider returned an unusable response."""
