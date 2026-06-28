# Resume Bullet Ideas

- Built an AI-assisted SOC triage and vulnerability prioritization platform using FastAPI, PostgreSQL, pgvector, and Azure OpenAI to correlate alerts, CVEs, IOCs, and internal runbooks.
- Implemented secure RAG controls including metadata-filtered retrieval, prompt injection defenses, citation validation, confidence thresholds, and human approval checkpoints.
- Designed zero-trust access patterns with RBAC, audit logging, and structured approval workflows aligned to NIST CSF, NIST AI RMF, CIS Controls, and OWASP guidance.
- Created GitHub Actions security gates for linting, testing, static analysis, and container scanning to support a secure SDLC.

## Interview Questions

### Why did you make the LLM advisory instead of autonomous?

Because incident actions need deterministic controls, role checks, and human accountability. The model helps analysts move faster, but it does not become the system of record.

### How did you reduce hallucination risk?

I required approved-source retrieval, structured outputs, citation minimums, confidence thresholds, and rejection of unsupported responses before persistence.

### Why choose PostgreSQL and pgvector?

They reduce system sprawl, simplify joins between cases and embeddings, and make the architecture more realistic for an intern-scale build.

