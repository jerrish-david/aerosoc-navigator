# Security Controls Register

## Zero Trust

Why:
No internal path is inherently trusted in an enterprise environment. Every request and service call should prove identity and authorization.

## Least Privilege

Why:
If an account or service is compromised, reduced permissions limit blast radius and prevent lateral misuse.

## RBAC

Why:
SOC analysts, responders, auditors, and admins should not share the same actions or visibility.

## Input Validation

Why:
Alerts, uploads, and API parameters are untrusted data and must be validated before use.

## Prompt Injection Defenses

Why:
Retrieved documents and user-submitted text may contain instructions designed to manipulate the model.

## Output Validation

Why:
A well-formed but unsupported LLM answer can still be unsafe if persisted or acted on.

## Confidence Thresholds

Why:
Analysts need a clear signal when the system lacks enough evidence for a strong recommendation.

## Source Attribution

Why:
Security decisions must be explainable, reviewable, and defensible during incident reviews or audits.

## Immutable Audit Events

Why:
Cybersecurity workflows need non-repudiation and tamper evidence for governance and post-incident analysis.

## Data Minimization

Why:
The platform should only send the minimum required context to retrieval and model layers to reduce leakage risk.

## Secrets Management

Why:
Embedding secrets in code, images, or CI logs creates long-lived compromise paths.

## Encryption In Transit and At Rest

Why:
Cases, evidence, and identity artifacts remain sensitive both on the wire and in storage.

