# Threat Model

## Primary Assets

- alerts and case records
- analyst decisions
- internal security documents
- embeddings and retrieved chunks
- audit events
- credentials and service identities

## Threats

### Prompt Injection

Uploaded or retrieved content may attempt to manipulate the model into ignoring system instructions.

### Privilege Escalation

A user may try to access cases or documents outside their role.

### Evidence Tampering

An attacker may attempt to alter raw alerts, citations, or audit records.

### Hallucinated Recommendations

The model may generate unsupported conclusions.

### Supply Chain Risk

Dependencies or container images may contain known vulnerabilities.

## Mitigations

- RBAC on every resource access
- append-only audit chain
- metadata-filtered retrieval
- citation minimums
- confidence thresholds
- output schema validation
- dependency and container scanning in CI

