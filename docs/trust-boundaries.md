# Trust Boundaries

## Boundary 1: Analyst Browser to Frontend

Risk:
Untrusted client input, token theft, and session misuse.

Controls:
- HTTPS only
- OIDC login with PKCE
- strict input validation on all requests

## Boundary 2: Frontend to Backend API

Risk:
Unauthorized API usage and parameter tampering.

Controls:
- bearer token validation
- server-side RBAC
- rate limiting
- correlation IDs

## Boundary 3: Backend to Datastore

Risk:
Sensitive case and evidence data exposure.

Controls:
- least-privilege service accounts
- parameterized queries
- encryption at rest

## Boundary 4: Backend to LLM Provider

Risk:
Sensitive data leakage and unsupported model behavior.

Controls:
- data minimization
- prompt guards
- structured outputs
- output validation

## Boundary 5: External Feeds to Ingestion Workers

Risk:
Poisoned documents, fake bulletins, or malformed threat data.

Controls:
- allowlisted sources
- checksum retention
- parser hardening
- untrusted-content handling

