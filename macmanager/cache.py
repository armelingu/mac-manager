"""In-memory cache with per-function TTL.

Useful for expensive collections that don't need to run on every dashboard refresh
(e.g. public IP, security scan, list of macOS updates).

The cache is keyed by function + argument tuple. If the user passes different
arguments, separate entries are kept. Not thread-safe (we don't need it in our
single-thread use case), but it's enough for the dashboard.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar("T")

_STORE: dict[tuple, tuple[float, object]] = {}


def cached(ttl: float):
    """Decorator that caches a function's return for `ttl` seconds.

    Use ttl=0 to disable the cache (useful in tests).
    """

    def deco(fn: Callable[..., T]) -> Callable[..., T]:
        key_fn = (fn.__module__, fn.__qualname__)

        @wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            if ttl <= 0:
                return fn(*args, **kwargs)
            try:
                cache_key = (key_fn, args, tuple(sorted(kwargs.items())))
            except TypeError:
                return fn(*args, **kwargs)

            now = time.monotonic()
            entry = _STORE.get(cache_key)
            if entry and (now - entry[0]) < ttl:
                return entry[1]  # type: ignore[return-value]
            value = fn(*args, **kwargs)
            _STORE[cache_key] = (now, value)
            return value

        wrapper.cache_clear = lambda: _clear_for(key_fn)  # type: ignore[attr-defined]
        return wrapper

    return deco


def _clear_for(key_fn: tuple) -> None:
    for k in list(_STORE.keys()):
        if k[0] == key_fn:
            del _STORE[k]


def clear_all() -> None:
    _STORE.clear()


_MISS = object()


def peek(fn: Callable, *args, **kwargs):
    """Read from the cache without executing the function. Returns `_MISS` if there's no value yet.

    Useful for the dashboard to show "loading..." while heavy collections run
    in the background, without blocking the redraw on the first pass.
    """
    key_fn = (fn.__module__, fn.__qualname__)
    try:
        cache_key = (key_fn, args, tuple(sorted(kwargs.items())))
    except TypeError:
        return _MISS
    entry = _STORE.get(cache_key)
    if entry is None:
        return _MISS
    return entry[1]


def is_miss(value) -> bool:
    return value is _MISS
