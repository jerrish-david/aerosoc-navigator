# Testing Strategy

## Unit Tests

Focus on deterministic logic:

- risk scoring
- authorization checks
- prompt guard detection
- output validation
- audit hashing

## Integration Tests

Focus on workflow seams:

- alert ingestion to case creation
- case triage generation
- approval flow
- document upload to chunking queue

## Security Tests

Focus on abuse cases:

- IDOR attempts
- invalid roles
- malformed alert payloads
- dependency vulnerabilities
- container configuration issues

## Prompt Injection Tests

Focus on untrusted content:

- direct instruction override text
- encoded malicious strings
- fake citations
- hidden control phrases inside documents

