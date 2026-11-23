from flask import Blueprint, abort, jsonify
from .auth import current_user
from . import service

bp = Blueprint("invoices", __name__)


@bp.get("/invoices")
def list_invoices():
    user = current_user()
    return jsonify(service.invoices_for(user))


@bp.get("/invoices/<int:invoice_id>")
def get_invoice(invoice_id: int):
    user = current_user()
    invoice = service.invoice_detail(user, invoice_id)
    if invoice is None:
        abort(404)
    return jsonify(invoice)
