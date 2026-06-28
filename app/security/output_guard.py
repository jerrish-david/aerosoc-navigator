from app.core.exceptions import LowConfidenceError, ValidationError
from app.rag.validators import CitationValidator, ConfidenceValidator


class OutputGuard:
    def __init__(self) -> None:
        self._citation_validator = CitationValidator()
        self._confidence_validator = ConfidenceValidator()

    def validate(self, recommendation: str, citations: list[str], confidence_score: float) -> None:
        if not recommendation.strip():
            raise ValidationError("Recommendation cannot be empty.")
        if not self._citation_validator.validate(citations):
            raise ValidationError("Recommendation does not have enough citations.")
        if not self._confidence_validator.validate(confidence_score):
            raise LowConfidenceError("Recommendation confidence is below threshold.")

