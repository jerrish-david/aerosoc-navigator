from dataclasses import dataclass


@dataclass(slots=True)
class EvaluationResult:
    name: str
    passed: bool
    details: str


class TriageEvaluationSuite:
    def run(self) -> list[EvaluationResult]:
        # Pseudocode:
        # Evaluate citation coverage, unsupported claims, ATT&CK mapping quality,
        # and consistency of recommendation severity across a fixed gold dataset.
        return [
            EvaluationResult(
                name="citation_coverage",
                passed=True,
                details="Placeholder evaluation result for scaffold.",
            )
        ]

