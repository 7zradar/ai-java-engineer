"""Secret masking and data loss prevention for prompts and logs."""

import re

# Standard regex patterns for API keys, bearer tokens, and secrets
SECRET_PATTERNS = [
    # OpenAI / generic sk- keys
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE), "[REDACTED_API_KEY]"),
    # Google API Key / AIza...
    (re.compile(r"AIza[0-9A-Za-z-_]{30,40}", re.IGNORECASE), "[REDACTED_GEMINI_KEY]"),
    # GitHub PAT (ghp_, gho_, etc.)
    (re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}", re.IGNORECASE), "[REDACTED_GITHUB_TOKEN]"),
    # Bearer tokens in headers
    (re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE), "Bearer [REDACTED_BEARER_TOKEN]"),
    # Password parameters in connection strings
    (re.compile(r"(password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE), r"\1='[REDACTED_PASSWORD]'"),
    # AWS Access / Secret keys
    (re.compile(r"(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}", re.IGNORECASE), "[REDACTED_AWS_KEY]"),
]


class SecretSanitizer:
    """Sanitizes text by replacing detected secrets and credentials with redacted tokens."""

    @classmethod
    def sanitize(cls, text: str | None) -> str:
        if not text:
            return ""
        sanitized = text
        for pattern, replacement in SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    @classmethod
    def sanitize_dict(cls, data: dict) -> dict:
        """Recursively sanitizes dictionary string values."""
        clean_dict = {}
        for key, value in data.items():
            if isinstance(value, str):
                clean_dict[key] = cls.sanitize(value)
            elif isinstance(value, dict):
                clean_dict[key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                clean_dict[key] = [
                    cls.sanitize(item) if isinstance(item, str) else item for item in value
                ]
            else:
                clean_dict[key] = value
        return clean_dict
