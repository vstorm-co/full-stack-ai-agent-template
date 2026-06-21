{%- if cookiecutter.enable_code_execution %}
"""Code-execution tool backed by the Monty sandbox."""

import json
import logging
from typing import Any

from pydantic_monty import CollectString, Monty, MontyError, ResourceLimits

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_OUTPUT_CHARS = 8000


def _clip(text: str) -> str:
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + "\n…(output truncated)"
    return text


def _format_result(stdout: str, output: Any) -> str:
    parts: list[str] = []
    if stdout.strip():
        parts.append(f"stdout:\n{stdout.rstrip()}")
    if output is not None:
        try:
            rendered = json.dumps(output, default=str)
        except (TypeError, ValueError):
            rendered = str(output)
        parts.append(f"result: {rendered}")
    text = "\n\n".join(parts) if parts else "(code ran successfully with no output)"
    return _clip(text)


async def run_python(code: str) -> str:
    """Execute model-written Python in the Monty sandbox and return its output.

    Args:
        code: The Python source to run. A restricted stdlib subset (``math``,
            ``asyncio``, ``json``, ``datetime``, ``re``) works, but modules like
            ``statistics``/``random``/``itertools`` are unavailable.

    Returns:
        The captured stdout plus the value of the final expression, or an error
        message the model can read and recover from.
    """
    limits: ResourceLimits = {
        "max_duration_secs": settings.CODE_EXECUTION_TIMEOUT_SECS,
        "max_allocations": settings.CODE_EXECUTION_MAX_ALLOCATIONS,
    }
    collector = CollectString()
    try:
        monty = await Monty.acreate(code)
        output = await monty.run_async(print_callback=collector, limits=limits)
    except MontyError as e:
        return _clip(f"Execution failed: {e}")
    except Exception as e:
        logger.exception("run_python execution failed")
        return _clip(f"Execution failed: {e}")

    return _format_result(collector.output, output)
{%- else %}
"""Code-execution tool — not configured (enable_code_execution=false)."""
{%- endif %}
