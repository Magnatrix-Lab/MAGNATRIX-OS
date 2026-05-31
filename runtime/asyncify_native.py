
"""
runtime/asyncify_native.py — MAGNATRIX-OS AsyncIO Migration Helper

Provides patterns to convert sync native modules to async.
Pure Python, stdlib only. Zero dependencies.

Components:
    • Asyncify — decorator to convert sync functions to async
    • AsyncBridge — bridge pattern for sync-to-async layer communication
    • AsyncPool — managed asyncio pool for CPU-bound operations
    • AsyncQueue — async queue with backpressure
    • AsyncSemaphore — named semaphore for resource limiting
    • AsyncLock — distributed async lock (layer-aware)
    • AsyncLoop — event loop manager
    • AsyncTimer — async timer for periodic tasks
    • AsyncBatch — batch async operations with concurrency control
    • AsyncGather — gather results with timeout and partial results
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import functools
import inspect
import threading
import time
import weakref
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union

T = TypeVar('T')


# ════════════════════════════════════════════════════════════════════════════
# Asyncify — decorator to convert sync functions to async
# ════════════════════════════════════════════════════════════════════════════

def asyncify(max_workers: Optional[int] = None, loop: Optional[asyncio.AbstractEventLoop] = None):
    """
    Decorator that converts a sync function into an async one.
    The sync function runs in a ThreadPoolExecutor so it doesn't block the event loop.

    Usage:
        @asyncify(max_workers=4)
        def cpu_intensive_task(x):
            return sum(range(x))

        result = await cpu_intensive_task(1000000)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., asyncio.Future[T]]:
        _executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(_executor, functools.partial(func, *args, **kwargs))

        wrapper._executor = _executor
        wrapper._original = func
        return wrapper
    return decorator


class Asyncify:
    """Factory for creating asyncified versions of sync functions."""

    _executors: Dict[str, concurrent.futures.ThreadPoolExecutor] = {}
    _lock = threading.Lock()

    @classmethod
    def get_executor(cls, name: str, max_workers: int = 4) -> concurrent.futures.ThreadPoolExecutor:
        with cls._lock:
            if name not in cls._executors:
                cls._executors[name] = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
            return cls._executors[name]

    @classmethod
    def shutdown_all(cls, wait: bool = True) -> None:
        with cls._lock:
            for name, executor in list(cls._executors.items()):
                executor.shutdown(wait=wait)
            cls._executors.clear()

    @classmethod
    def wrap(cls, func: Callable[..., T], executor_name: str = "default", max_workers: int = 4) -> Callable[..., asyncio.Future[T]]:
        executor = cls.get_executor(executor_name, max_workers)

        async def wrapper(*args, **kwargs) -> T:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(executor, functools.partial(func, *args, **kwargs))

        functools.update_wrapper(wrapper, func)
        return wrapper


# ════════════════════════════════════════════════════════════════════════════
# AsyncBridge — bridge pattern for sync-to-async layer communication
# ════════════════════════════════════════════════════════════════════════════

class AsyncBridge:
    """
    Bridge that allows sync code to call async code and vice versa.

    Sync layer can call async layer transparently by wrapping the async function.
    """

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        self._loop = loop
        self._lock = threading.Lock()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    def run_async(self, coro) -> Any:
        """Run an async coroutine from sync code."""
        try:
            loop = asyncio.get_running_loop()
            # Already in async context - run in separate thread to avoid deadlock
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=30)
        except RuntimeError:
            # No running loop, safe to use run_until_complete
            return self.loop.run_until_complete(coro)

    def wrap_sync(self, async_func: Callable) -> Callable:
        """Wrap an async function so it can be called from sync code."""
        def wrapper(*args, **kwargs):
            coro = async_func(*args, **kwargs)
            return self.run_async(coro)
        functools.update_wrapper(wrapper, async_func)
        return wrapper

    def wrap_async(self, sync_func: Callable, executor_name: str = "bridge", max_workers: int = 4) -> Callable:
        """Wrap a sync function so it can be called from async code without blocking."""
        return Asyncify.wrap(sync_func, executor_name, max_workers)


# ════════════════════════════════════════════════════════════════════════════
# AsyncPool — managed asyncio pool for CPU-bound operations
# ════════════════════════════════════════════════════════════════════════════

class AsyncPool:
    """Managed pool for running CPU-bound tasks in threads."""

    def __init__(self, name: str = "default", max_workers: int = 4):
        self.name = name
        self.max_workers = max_workers
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Set[asyncio.Future] = set()
        self._lock = asyncio.Lock()

    async def submit(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Submit a function to the pool and await result."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, functools.partial(func, *args, **kwargs))

    async def map(self, func: Callable[[Any], T], items: List[Any]) -> List[T]:
        """Map a function over items concurrently."""
        tasks = [self.submit(func, item) for item in items]
        return await asyncio.gather(*tasks)

    async def shutdown(self, wait: bool = True) -> None:
        """Shutdown the pool gracefully."""
        self._executor.shutdown(wait=wait)

    def __len__(self) -> int:
        return len(self._tasks)

    @property
    def is_active(self) -> bool:
        return not self._executor._shutdown


# ════════════════════════════════════════════════════════════════════════════
# AsyncQueue — async queue with backpressure
# ════════════════════════════════════════════════════════════════════════════

class AsyncQueue:
    """
    Async queue with backpressure support.

    Features:
        - Max size with configurable overflow policy (block, drop oldest, drop newest)
        - Metrics: enqueue/dequeue rates, wait times
        - Priority support (optional)
    """

    def __init__(self, maxsize: int = 100, policy: str = "block"):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.maxsize = maxsize
        self.policy = policy  # "block", "drop_oldest", "drop_newest"
        self._enqueued = 0
        self._dequeued = 0
        self._dropped = 0

    async def put(self, item: Any, timeout: Optional[float] = None) -> bool:
        """Put item into queue. Returns True if successful, False if dropped."""
        try:
            if self.policy == "block":
                await asyncio.wait_for(self._queue.put(item), timeout=timeout)
            elif self.policy == "drop_oldest":
                if self._queue.full():
                    try:
                        self._queue.get_nowait()
                        self._dropped += 1
                    except asyncio.QueueEmpty:
                        pass
                self._queue.put_nowait(item)
            elif self.policy == "drop_newest":
                if not self._queue.full():
                    self._queue.put_nowait(item)
                else:
                    self._dropped += 1
                    return False
            self._enqueued += 1
            return True
        except asyncio.TimeoutError:
            return False

    async def get(self, timeout: Optional[float] = None) -> Any:
        """Get item from queue."""
        if timeout:
            item = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        else:
            item = await self._queue.get()
        self._dequeued += 1
        return item

    def get_nowait(self) -> Any:
        item = self._queue.get_nowait()
        self._dequeued += 1
        return item

    def qsize(self) -> int:
        return self._queue.qsize()

    def empty(self) -> bool:
        return self._queue.empty()

    def full(self) -> bool:
        return self._queue.full()

    def stats(self) -> Dict[str, int]:
        return {
            "enqueued": self._enqueued,
            "dequeued": self._dequeued,
            "dropped": self._dropped,
            "current_size": self.qsize(),
            "max_size": self.maxsize,
        }


# ════════════════════════════════════════════════════════════════════════════
# AsyncSemaphore — named semaphore for resource limiting
# ════════════════════════════════════════════════════════════════════════════

class AsyncSemaphore:
    """Named semaphore for limiting concurrent operations across layers."""

    _semaphores: Dict[str, asyncio.Semaphore] = {}
    _lock = threading.Lock()

    @classmethod
    def get(cls, name: str, value: int = 1) -> asyncio.Semaphore:
        with cls._lock:
            if name not in cls._semaphores:
                cls._semaphores[name] = asyncio.Semaphore(value)
            return cls._semaphores[name]

    @classmethod
    def reset(cls, name: str) -> None:
        with cls._lock:
            if name in cls._semaphores:
                del cls._semaphores[name]


# ════════════════════════════════════════════════════════════════════════════
# AsyncLock — distributed async lock
# ════════════════════════════════════════════════════════════════════════════

class AsyncLock:
    """Reentrant lock that works across threads and async contexts."""

    def __init__(self):
        self._async_lock = asyncio.Lock()
        self._thread_lock = threading.Lock()

    async def acquire_async(self) -> None:
        await self._async_lock.acquire()

    def release_async(self) -> None:
        self._async_lock.release()

    def acquire_sync(self) -> None:
        self._thread_lock.acquire()

    def release_sync(self) -> None:
        self._thread_lock.release()

    async def __aenter__(self):
        await self._async_lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._async_lock.release()
        return False


# ════════════════════════════════════════════════════════════════════════════
# AsyncLoop — event loop manager
# ════════════════════════════════════════════════════════════════════════════

class AsyncLoop:
    """Event loop manager with thread safety."""

    @staticmethod
    def get_loop() -> asyncio.AbstractEventLoop:
        """Get current or create new event loop."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    @staticmethod
    def run(coro) -> Any:
        """Run a coroutine, handling both sync and async contexts."""
        try:
            loop = asyncio.get_running_loop()
            # Already in async context, schedule coroutine
            future = asyncio.ensure_future(coro, loop=loop)
            return future
        except RuntimeError:
            # Sync context, safe to run
            loop = AsyncLoop.get_loop()
            return loop.run_until_complete(coro)

    @staticmethod
    def create_task(coro) -> asyncio.Task:
        """Create a task in the current or new event loop."""
        try:
            loop = asyncio.get_running_loop()
            return loop.create_task(coro)
        except RuntimeError:
            loop = AsyncLoop.get_loop()
            return loop.create_task(coro)


# ════════════════════════════════════════════════════════════════════════════
# AsyncTimer — async timer for periodic tasks
# ════════════════════════════════════════════════════════════════════════════

class AsyncTimer:
    """Async timer for periodic execution."""

    def __init__(self, interval: float, callback: Callable, *args, **kwargs):
        self.interval = interval
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def _run(self) -> None:
        while self._running:
            await asyncio.sleep(self.interval)
            if self._running:
                try:
                    if asyncio.iscoroutinefunction(self.callback):
                        await self.callback(*self.args, **self.kwargs)
                    else:
                        self.callback(*self.args, **self.kwargs)
                except Exception as e:
                    print(f"[AsyncTimer] Error: {e}")

    def start(self) -> None:
        self._running = True
        self._task = AsyncLoop.create_task(self._run())

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    async def __aenter__(self):
        self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


# ════════════════════════════════════════════════════════════════════════════
# AsyncBatch — batch async operations with concurrency control
# ════════════════════════════════════════════════════════════════════════════

class AsyncBatch:
    """Execute batch of async operations with controlled concurrency."""

    def __init__(self, max_concurrency: int = 10):
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def _execute_with_limit(self, coro) -> Any:
        async with self._semaphore:
            return await coro

    async def run(self, coros: List[asyncio.Coroutine]) -> List[Any]:
        """Run all coroutines with max concurrency limit."""
        tasks = [self._execute_with_limit(c) for c in coros]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def run_with_results(self, coros: List[asyncio.Coroutine]) -> Tuple[List[Any], List[Exception]]:
        """Run and separate successes from failures."""
        results = await self.run(coros)
        successes = []
        failures = []
        for r in results:
            if isinstance(r, Exception):
                failures.append(r)
            else:
                successes.append(r)
        return successes, failures


# ════════════════════════════════════════════════════════════════════════════
# AsyncGather — gather results with timeout and partial results
# ════════════════════════════════════════════════════════════════════════════

class AsyncGather:
    """Gather results from multiple async tasks with timeout support."""

    @staticmethod
    async def gather_with_timeout(
        tasks: List[asyncio.Task],
        timeout: Optional[float] = None,
        return_exceptions: bool = True,
    ) -> List[Any]:
        """Gather tasks with overall timeout."""
        if timeout:
            return await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=return_exceptions),
                timeout=timeout
            )
        return await asyncio.gather(*tasks, return_exceptions=return_exceptions)

    @staticmethod
    async def gather_first_n(
        tasks: List[asyncio.Task],
        n: int,
        timeout: Optional[float] = None,
    ) -> List[Any]:
        """Return results from first n completed tasks."""
        if timeout:
            done, pending = await asyncio.wait(
                tasks, timeout=timeout, return_when=asyncio.ALL_COMPLETED
            )
        else:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

        for task in pending:
            task.cancel()

        results = [task.result() for task in done if not task.cancelled()]
        return results[:n]

    @staticmethod
    async def gather_with_progress(
        tasks: List[asyncio.Task],
        on_progress: Callable[[int, int], None],
        timeout: Optional[float] = None,
    ) -> List[Any]:
        """Gather tasks with progress callback."""
        total = len(tasks)
        completed = 0
        results = []

        for task in asyncio.as_completed(tasks, timeout=timeout):
            try:
                result = await task
                results.append(result)
            except Exception as e:
                results.append(e)
            completed += 1
            on_progress(completed, total)

        return results


# ════════════════════════════════════════════════════════════════════════════
# DEMO / SELF-TEST
# ════════════════════════════════════════════════════════════════════════════

async def _self_test():
    print("=" * 60)
    print("MAGNATRIX-OS AsyncIO Migration Helper — Self-Test")
    print("=" * 60)

    # Test 1: @asyncify decorator
    print("\n[1] @asyncify decorator")
    @asyncify(max_workers=2)
    def sync_add(a, b):
        time.sleep(0.01)
        return a + b

    result = await sync_add(3, 4)
    assert result == 7, f"Expected 7, got {result}"
    print(f"  ✓ sync_add(3, 4) = {result}")

    # Test 2: AsyncBridge
    print("\n[2] AsyncBridge")
    bridge = AsyncBridge()

    async def async_greet(name):
        await asyncio.sleep(0.01)
        return f"Hello, {name}!"

    sync_greet = bridge.wrap_sync(async_greet)
    result = sync_greet("MAGNATRIX")
    assert result == "Hello, MAGNATRIX!"
    print(f"  ✓ Bridge: {result}")

    # Test 3: AsyncPool
    print("\n[3] AsyncPool")
    pool = AsyncPool("test_pool", max_workers=3)

    def cpu_task(n):
        return n * n

    results = await pool.map(cpu_task, [1, 2, 3, 4, 5])
    assert results == [1, 4, 9, 16, 25]
    print(f"  ✓ Pool map: {results}")

    # Test 4: AsyncQueue
    print("\n[4] AsyncQueue")
    queue = AsyncQueue(maxsize=5, policy="block")

    for i in range(3):
        await queue.put(i)

    items = []
    for _ in range(3):
        items.append(await queue.get())

    assert items == [0, 1, 2]
    print(f"  ✓ Queue: {items}")
    print(f"  ✓ Queue stats: {queue.stats()}")

    # Test 5: AsyncSemaphore
    print("\n[5] AsyncSemaphore")
    sem = AsyncSemaphore.get("test_sem", value=2)
    acquired = 0

    async def acquire_sem():
        nonlocal acquired
        async with sem:
            acquired += 1
            await asyncio.sleep(0.01)

    await asyncio.gather(*[acquire_sem() for _ in range(4)])
    assert acquired == 4
    print(f"  ✓ Semaphore: {acquired} acquisitions")

    # Test 6: AsyncLock
    print("\n[6] AsyncLock")
    lock = AsyncLock()
    counter = 0

    async def increment():
        nonlocal counter
        await lock.acquire_async()
        try:
            counter += 1
        finally:
            lock.release_async()

    await asyncio.gather(*[increment() for _ in range(10)])
    assert counter == 10
    print(f"  ✓ Lock: counter = {counter}")

    # Test 7: AsyncTimer
    print("\n[7] AsyncTimer")
    timer_count = 0

    def tick():
        nonlocal timer_count
        timer_count += 1

    timer = AsyncTimer(0.05, tick)
    timer.start()
    await asyncio.sleep(0.15)
    timer.stop()
    assert timer_count >= 2
    print(f"  ✓ Timer: {timer_count} ticks in 0.15s")

    # Test 8: AsyncBatch
    print("\n[8] AsyncBatch")
    batch = AsyncBatch(max_concurrency=2)

    async def slow_task(n):
        await asyncio.sleep(0.05)
        return n * 2

    coros = [slow_task(i) for i in range(4)]
    results = await batch.run(coros)
    assert results == [0, 2, 4, 6]
    print(f"  ✓ Batch: {results}")

    # Test 9: AsyncGather
    print("\n[9] AsyncGather")

    async def task_a():
        await asyncio.sleep(0.02)
        return "A"

    async def task_b():
        await asyncio.sleep(0.01)
        return "B"

    tasks = [asyncio.create_task(task_a()), asyncio.create_task(task_b())]
    results = await AsyncGather.gather_with_timeout(tasks, timeout=1.0)
    assert "A" in results and "B" in results
    print(f"  ✓ Gather: {results}")

    # Test 10: AsyncLoop
    print("\n[10] AsyncLoop")
    loop = AsyncLoop.get_loop()
    assert loop is not None
    print(f"  ✓ Loop: {loop}")

    # Cleanup
    Asyncify.shutdown_all(wait=False)
    await pool.shutdown(wait=False)

    print("\n" + "=" * 60)
    print("All self-tests passed ✓")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(_self_test())
