from flask import Blueprint, jsonify
from .auth import current_user
from . import service

bp = Blueprint("invoices", __name__)


@bp.get("/invoices")
def list_invoices():
    user = current_user()
    return jsonify(service.invoices_for(user))
