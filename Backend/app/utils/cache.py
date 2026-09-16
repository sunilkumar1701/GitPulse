import asyncio
import time
from functools import wraps
from typing import Callable, Any, Dict, Tuple

def async_ttl_cache(ttl_seconds: int = 60):
    """
    An async-aware TTL cache that also deduplicates concurrent requests.
    If multiple calls are made with the same arguments before the first
    resolves, they will all await the exact same underlying task.
    """
    # Stores cache entries as: { cache_key: (timestamp, asyncio.Task) }
    cache: Dict[str, Tuple[float, asyncio.Task]] = {}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Create a simple deterministic cache key
            key = str(args) + str(sorted(kwargs.items()) if kwargs else [])
            
            now = time.time()
            
            # 1. Clean up expired items to prevent memory leaks
            expired_keys = [k for k, (ts, _) in cache.items() if now - ts > ttl_seconds]
            for k in expired_keys:
                del cache[k]
                
            # 2. Check if the result is already cached (or currently being computed)
            if key in cache:
                _, task = cache[key]
                # Await the existing task (which might be pending or already done)
                return await task
                
            # 3. Create a new task and store it in the cache immediately
            task = asyncio.create_task(func(*args, **kwargs))
            cache[key] = (now, task)
            
            try:
                # 4. Await our newly created task
                return await task
            except Exception:
                # If the task fails, remove it from the cache so future requests will retry
                cache.pop(key, None)
                raise
                
        return wrapper
    return decorator
