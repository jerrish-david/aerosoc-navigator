class PromptGuard:
    SUSPICIOUS_PATTERNS = (
        "ignore previous instructions",
        "system prompt",
        "developer message",
        "override policy",
        "act as administrator",
    )

    def sanitize(self, text: str) -> str:
        sanitized = text
        for pattern in self.SUSPICIOUS_PATTERNS:
            sanitized = sanitized.replace(pattern, "[redacted-instruction-pattern]")
        return sanitized

    def detect(self, text: str) -> bool:
        lowered = text.lower()
        return any(pattern in lowered for pattern in self.SUSPICIOUS_PATTERNS)

