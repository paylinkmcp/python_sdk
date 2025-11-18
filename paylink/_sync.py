from typing import Any, Awaitable
import asyncio
import concurrent.futures
import warnings


def run_sync(awaitable: Awaitable[Any]) -> Any:
    """
    Run an async coroutine in a synchronous context.
    
    Handles both cases:
    - No running event loop: uses asyncio.run()
    - Event loop already running (Jupyter/IPython): runs in a separate thread
    """
    try:
        asyncio.get_running_loop()
        # If we get here, there's a running loop
        has_running_loop = True
    except RuntimeError:
        # no running loop: safe to use asyncio.run
        has_running_loop = False
    
    if not has_running_loop:
        return asyncio.run(awaitable)

    # already inside a loop: run in a separate thread with its own event loop
    def run_in_thread():
        # In a new thread, there's no running loop, so we can use asyncio.run()
        # which properly handles cleanup of all tasks and resources
        # asyncio.run() ensures all tasks are completed before closing
        # Suppress warnings about pending tasks from MCP library's HTTP client
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited")
            warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*Task was destroyed.*")
            return asyncio.run(awaitable)
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        return future.result()
