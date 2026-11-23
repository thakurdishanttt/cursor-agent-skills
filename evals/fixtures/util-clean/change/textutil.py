"""Small text helpers."""
import re
import unicodedata

_MAX_LEN = 80


def slugify(text: str, max_len: int = _MAX_LEN) -> str:
    """Return a lowercase ASCII slug: letters, digits and single hyphens."""
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    if max_len < 1:
        raise ValueError("max_len must be >= 1")
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:max_len].rstrip("-")
