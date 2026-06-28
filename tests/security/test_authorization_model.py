import pytest

from app.core.exceptions import AuthorizationError
from app.security.authn import AuthenticatedUser
from app.security.authz import AuthorizationService


def test_authorization_blocks_user_without_required_role() -> None:
    service = AuthorizationService()
    user = AuthenticatedUser(subject="1", email="analyst@example.com", roles=["soc_analyst"])
    with pytest.raises(AuthorizationError):
        service.require_role(user=user, allowed_roles={"admin"})

