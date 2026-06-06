import logging
from typing import Any, Optional

from observability import Span, TraceCollector


def pre_step_hook(
    step_name: str,
    inputs: dict[str, Any],
    logger: logging.Logger,
    collector: TraceCollector,
) -> Span:
    parts = []
    for k, v in inputs.items():
        v_str = str(v)
        if len(v_str) > 60:
            v_str = v_str[:57] + "..."
        parts.append(f"{k}={v_str}")
    input_summary = ", ".join(parts)

    logger.info("tool_call_start", extra={"step": step_name, "input_summary": input_summary})
    return collector.start_span(step_name, input_summary)


def post_step_hook(
    step_name: str,
    result: Any,
    span: Span,
    logger: logging.Logger,
    collector: TraceCollector,
    error: Optional[Exception] = None,
) -> None:
    status = "error" if error is not None else "success"
    collector.end_span(span, status=status)

    if error is not None:
        result_summary = f"{type(error).__name__}: {str(error)[:120]}"
    elif isinstance(result, dict):
        result_summary = ", ".join(f"{k}={str(v)[:40]}" for k, v in list(result.items())[:4])
    elif isinstance(result, str):
        result_summary = result[:100] + ("..." if len(result) > 100 else "")
    else:
        result_summary = str(result)[:100]

    logger.info(
        "tool_call_end",
        extra={
            "step": step_name,
            "status": status,
            "duration_ms": round(span.duration_ms, 2) if span.duration_ms is not None else None,
            "result_summary": result_summary,
        },
    )
