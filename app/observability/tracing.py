import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

current_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    return str(uuid.uuid4())


@dataclass
class TimerResult:
    elapsed_ms: int = 0


@contextmanager
def timer() -> Iterator[TimerResult]:
    result = TimerResult()
    started_at = time.perf_counter()
    try:
        yield result
    finally:
        result.elapsed_ms = round((time.perf_counter() - started_at) * 1000)
