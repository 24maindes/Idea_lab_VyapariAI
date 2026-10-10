"""
services/cache.py - a tiny in-memory TTL cache.

    @ttl_cache(seconds=60)
    def expensive(shop_id, ...): ...

The FIRST argument must be the shop id (so one shop's results can be thrown away with
invalidate_shop(shop_id) after that shop writes data). Works per process; fine for this project.
"""
import functools
import threading
import time

_lock = threading.Lock()
_store: dict = {}          # key -> (expires_at, value)
_shop_keys: dict = {}      # shop_id -> set(keys)


def ttl_cache(seconds: int):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(shop_id, *args, **kwargs):
            key = (fn.__module__, fn.__name__, shop_id, args, tuple(sorted(kwargs.items())))
            now = time.time()
            with _lock:
                hit = _store.get(key)
                if hit and hit[0] > now:
                    return hit[1]
            value = fn(shop_id, *args, **kwargs)
            with _lock:
                _store[key] = (now + seconds, value)
                _shop_keys.setdefault(shop_id, set()).add(key)
            return value
        wrapper.__wrapped__ = fn
        return wrapper
    return decorator


def invalidate_shop(shop_id) -> None:
    """Forget everything cached for this shop (call after purchases, sales, product changes, imports)."""
    with _lock:
        for key in _shop_keys.pop(shop_id, set()):
            _store.pop(key, None)


def clear_all() -> None:
    with _lock:
        _store.clear()
        _shop_keys.clear()


def get_or_set(shop_id, key, seconds: int, producer):
    """
    Cache the result of producer() for `seconds`, under (shop_id, key).
    Unlike ttl_cache the arguments of producer() are NOT part of the key, so it can use a database session.
    invalidate_shop(shop_id) throws the value away.
    """
    full_key = ("get_or_set", shop_id, key)
    now = time.time()
    with _lock:
        hit = _store.get(full_key)
        if hit and hit[0] > now:
            return hit[1]
    value = producer()
    with _lock:
        _store[full_key] = (now + seconds, value)
        _shop_keys.setdefault(shop_id, set()).add(full_key)
    return value
