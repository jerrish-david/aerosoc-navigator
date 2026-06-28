from app.core.exceptions import AuthorizationError
from app.security.authn import AuthenticatedUser


class AuthorizationService:
    def require_role(self, user: AuthenticatedUser, allowed_roles: set[str]) -> None:
        if not allowed_roles.intersection(user.roles):
            raise AuthorizationError("User lacks required role.")

