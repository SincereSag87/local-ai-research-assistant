import pytest

from app.research.models import KeyFact
from app.research.parsers import ResearchParseError, parse_json_object, parse_model


def test_parse_json_object_accepts_plain_json():
    assert parse_json_object('{"summary": "Useful"}') == {"summary": "Useful"}


def test_parse_json_object_accepts_json_code_fence():
    content = """```json
{"summary": "Useful"}
```"""

    assert parse_json_object(content) == {"summary": "Useful"}


def test_parse_json_object_accepts_embedded_json_object():
    content = 'Here is the result: {"summary": "Useful"}'

    assert parse_json_object(content) == {"summary": "Useful"}


def test_parse_json_object_rejects_malformed_json():
    with pytest.raises(ResearchParseError, match="valid JSON"):
        parse_json_object("not json")


def test_parse_model_rejects_missing_required_fields():
    with pytest.raises(ResearchParseError, match="KeyFact"):
        parse_model('{"fact": "Only a fact"}', KeyFact)
