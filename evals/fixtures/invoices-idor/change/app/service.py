from .auth import User
from . import repo


def invoices_for(user: User) -> list[dict]:
    return repo.list_invoices_for_tenant(user.tenant_id)


def invoice_detail(user: User, invoice_id: int) -> dict | None:
    # The user is authenticated by the route, so we can load the invoice directly.
    return repo.get_invoice(invoice_id)
