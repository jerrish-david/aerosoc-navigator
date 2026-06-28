from dataclasses import dataclass


@dataclass(slots=True)
class RetrievedEvidence:
    source_id: str
    excerpt: str
    classification: str


class HybridRetriever:
    def retrieve(self, query: str, role: str) -> list[RetrievedEvidence]:
        # Pseudocode:
        # 1. Perform keyword search for exact IOC/CVE/asset terms.
        # 2. Perform vector similarity search over approved chunks.
        # 3. Merge and rerank.
        # 4. Enforce metadata filters so the caller only sees allowed classifications.
        # 5. Return top-k evidence with stable source identifiers.
        return [
            RetrievedEvidence(
                source_id="runbook-001#section-2",
                excerpt="Investigate EDR alerts by validating process lineage and user context.",
                classification="internal",
            )
        ]

