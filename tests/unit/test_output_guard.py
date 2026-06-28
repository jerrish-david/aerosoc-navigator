import pytest

from app.core.exceptions import LowConfidenceError
from app.security.output_guard import OutputGuard


def test_output_guard_rejects_low_confidence_output() -> None:
    guard = OutputGuard()
    with pytest.raises(LowConfidenceError):
        guard.validate(
            recommendation="Investigate",
            citations=["doc-1", "doc-2"],
            confidence_score=0.25,
        )

