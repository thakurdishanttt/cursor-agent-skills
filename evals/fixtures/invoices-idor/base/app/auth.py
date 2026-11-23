"""Authentication helpers. `current_user()` returns the signed-in user or aborts with 401."""
from dataclasses import dataclass
from flask import abort, g


@dataclass(frozen=True)
class User:
    id: int
    tenant_id: int
    is_admin: bool = False


def current_user() -> User:
    user = getattr(g, "user", None)
    if user is None:
        abort(401)
    return user
