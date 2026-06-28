from dataclasses import dataclass


@dataclass(slots=True)
class AuthenticatedUser:
    subject: str
    email: str
    roles: list[str]


class TokenValidator:
    def validate_bearer_token(self, token: str) -> AuthenticatedUser:
        # Pseudocode:
        # 1. Fetch and cache JWKS from the trusted identity provider.
        # 2. Validate signature, issuer, audience, expiry, and nonce as appropriate.
        # 3. Extract roles or group claims.
        # 4. Return a normalized identity object for downstream authorization.
        return AuthenticatedUser(
            subject="demo-user",
            email="analyst@example.com",
            roles=["soc_analyst"],
        )

