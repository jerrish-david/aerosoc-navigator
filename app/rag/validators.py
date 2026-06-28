from app.core.config import get_settings


class CitationValidator:
    def validate(self, citations: list[str]) -> bool:
        settings = get_settings()
        return len(citations) >= settings.default_min_citation_count


class ConfidenceValidator:
    def validate(self, confidence_score: float) -> bool:
        settings = get_settings()
        return confidence_score >= settings.default_low_confidence_threshold

