import pytest
from textutil import slugify


def test_basic():
    assert slugify("Hello, World!") == "hello-world"


def test_unicode_and_spaces():
    assert slugify("  Crème   Brûlée  ") == "creme-brulee"


def test_empty():
    assert slugify("") == ""


def test_truncates_without_trailing_hyphen():
    assert slugify("a b c d", max_len=3) == "a-b"


def test_rejects_non_str():
    with pytest.raises(TypeError):
        slugify(None)  # type: ignore[arg-type]


def test_rejects_bad_max_len():
    with pytest.raises(ValueError):
        slugify("x", max_len=0)
