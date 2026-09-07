import json
from typing import Any

from pydantic import BaseModel, ValidationError


class ResearchParseError(Exception):
    """Raised when an LLM response cannot be parsed into the expected research schema."""


def parse_json_object(content: str) -> dict[str, Any]:
    text = _strip_code_fence(content.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = _load_embedded_json(text)

    if not isinstance(data, dict):
        raise ResearchParseError("Expected the model to return a JSON object.")
    return data


def parse_model[T: BaseModel](content: str, model_type: type[T]) -> T:
    data = parse_json_object(content)
    try:
        return model_type.model_validate(data)
    except ValidationError as exc:
        raise ResearchParseError(
            f"Model output did not match {model_type.__name__}: {exc}"
        ) from exc


def _strip_code_fence(content: str) -> str:
    if not content.startswith("```"):
        return content

    lines = content.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return content


def _load_embedded_json(content: str) -> Any:
    decoder = json.JSONDecoder()
    start = content.find("{")
    while start != -1:
        try:
            data, _ = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            start = content.find("{", start + 1)
            continue
        return data

    raise ResearchParseError("Model output was not valid JSON.")
