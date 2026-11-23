from .auth import User
from . import repo


def invoices_for(user: User) -> list[dict]:
    return repo.list_invoices_for_tenant(user.tenant_id)
