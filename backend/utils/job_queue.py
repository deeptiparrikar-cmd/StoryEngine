"""Shared ThreadPoolExecutor for background generation tasks."""

from __future__ import annotations

import atexit
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

_EXECUTOR: ThreadPoolExecutor | None = None
MAX_WORKERS = 8


def _get_executor() -> ThreadPoolExecutor:
    global _EXECUTOR
    if _EXECUTOR is None or _EXECUTOR._shutdown:
        _EXECUTOR = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="se-worker")
        atexit.register(_EXECUTOR.shutdown, wait=False)
    return _EXECUTOR


def submit(fn: Callable, *args: Any, **kwargs: Any) -> Future:
    """Submit *fn* to the shared thread pool and return its Future."""
    return _get_executor().submit(fn, *args, **kwargs)


def shutdown(wait: bool = True) -> None:
    global _EXECUTOR
    if _EXECUTOR is not None:
        _EXECUTOR.shutdown(wait=wait)
        _EXECUTOR = None
