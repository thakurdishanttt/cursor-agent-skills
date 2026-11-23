"""Currency rates client."""
import requests

RATES_URL = "https://api.exchangerate.host/latest"


def latest_rate(base: str, quote: str) -> float:
    if not (base.isalpha() and quote.isalpha() and len(base) == len(quote) == 3):
        raise ValueError("currency codes must be 3 letters")
    resp = requests.get(RATES_URL, params={"base": base.upper(), "symbols": quote.upper()})
    resp.raise_for_status()
    return float(resp.json()["rates"][quote.upper()])
