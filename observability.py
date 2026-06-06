import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_STANDARD_LOG_FIELDS = frozenset({
    "name", "msg", "args", "created", "relativeCreated", "thread", "threadName",
    "process", "processName", "levelname", "levelno", "pathname", "filename",
    "module", "funcName", "lineno", "exc_info", "exc_text", "stack_info",
    "message", "taskName", "msecs",
})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        log_obj: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.message,
        }
        for key, val in record.__dict__.items():
            if key not in _STANDARD_LOG_FIELDS:
                log_obj[key] = val
        return json.dumps(log_obj)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("story_agent")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger


@dataclass
class Span:
    step_name: str
    start_time: float       # time.time() wall clock
    input_summary: str
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "running"


class TraceCollector:
    def __init__(self) -> None:
        self._spans: list[Span] = []

    def start_span(self, step_name: str, input_summary: str) -> Span:
        span = Span(step_name=step_name, start_time=time.time(), input_summary=input_summary)
        self._spans.append(span)
        return span

    def end_span(self, span: Span, status: str = "success") -> None:
        span.end_time = time.time()
        span.duration_ms = (span.end_time - span.start_time) * 1000
        span.status = status

    def write_trace_file(self, theme: str, age_group: str, language: str = "English") -> Path:
        traces_dir = Path("traces")
        traces_dir.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_theme = theme.replace(" ", "_")
        path = traces_dir / f"{ts}_{safe_theme}.json"

        def to_iso(t: Optional[float]) -> Optional[str]:
            if t is None:
                return None
            return datetime.fromtimestamp(t, tz=timezone.utc).isoformat()

        spans_data = [
            {
                "step_name": s.step_name,
                "start_time": to_iso(s.start_time),
                "end_time": to_iso(s.end_time),
                "duration_ms": round(s.duration_ms, 2) if s.duration_ms is not None else None,
                "status": s.status,
                "input_summary": s.input_summary,
            }
            for s in self._spans
        ]

        trace = {
            "run": {
                "theme": theme,
                "age_group": age_group,
                "language": language,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "spans": spans_data,
        }
        path.write_text(json.dumps(trace, indent=2))
        return path
