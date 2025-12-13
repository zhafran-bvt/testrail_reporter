"""Performance optimization service with advanced caching and streaming."""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Dict, List, cast

from app.core.config import config
from app.services.cache import TTLCache


class PerformanceService:
    """Service for performance optimizations including streaming and batching."""

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._cache_warming_active = False
        self._cache_warming_lock = threading.Lock()

    async def stream_large_dataset(
        self, data_generator: Callable[..., Any], chunk_size: int = 100, **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream large datasets in chunks to maintain stable memory usage.

        Args:
            data_generator: Function that generates data
            chunk_size: Size of each chunk to yield
            **kwargs: Arguments to pass to data_generator

        Yields:
            Dict containing chunk data and metadata
        """
        chunk_count = 0
        total_items = 0
        start_time = time.time()

        try:
            # Get data from generator
            data: List[Any] = await asyncio.get_event_loop().run_in_executor(self._executor, data_generator, **kwargs)

            # Stream data in chunks
            for i in range(0, len(data), chunk_size):
                chunk = data[i : i + chunk_size]
                chunk_count += 1
                total_items += len(chunk)

                yield {
                    "chunk_id": chunk_count,
                    "data": chunk,
                    "chunk_size": len(chunk),
                    "total_processed": total_items,
                    "has_more": i + chunk_size < len(data),
                    "processing_time": time.time() - start_time,
                }

                # Allow other coroutines to run
                await asyncio.sleep(0)

        except Exception as e:
            yield {"error": str(e), "chunk_id": chunk_count, "total_processed": total_items, "has_more": False}

    def warm_cache(self, cache: TTLCache, warm_data: List[tuple]) -> Dict[str, Any]:
        """
        Warm cache with frequently accessed data.

        Args:
            cache: Cache instance to warm
            warm_data: List of (key, value) tuples to preload

        Returns:
            Dict with warming statistics
        """
        with self._cache_warming_lock:
            if self._cache_warming_active:
                return {"status": "already_warming", "warmed_count": 0}

            self._cache_warming_active = True

        try:
            start_time = time.time()
            warmed_count = 0

            for key, value in warm_data:
                cache.set(key, value)
                warmed_count += 1

            duration = time.time() - start_time

            return {
                "status": "completed",
                "warmed_count": warmed_count,
                "duration_ms": round(duration * 1000, 2),
                "cache_size": cache.size(),
            }

        finally:
            with self._cache_warming_lock:
                self._cache_warming_active = False

    async def batch_process(
        self, items: List[Any], processor: Callable[[Any], Any], batch_size: int = 10, max_concurrent: int = 3
    ) -> List[Any]:
        """
        Process items in batches with concurrency control.

        Args:
            items: List of items to process
            processor: Function to process each item
            batch_size: Size of each batch
            max_concurrent: Maximum concurrent batches

        Returns:
            List of processed results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_batch(batch):
            async with semaphore:
                return await asyncio.get_event_loop().run_in_executor(
                    self._executor, lambda: [processor(item) for item in batch]
                )

        # Create batches
        batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

        # Process batches concurrently
        batch_results = await asyncio.gather(*[process_batch(batch) for batch in batches])

        # Flatten results
        results = []
        for batch_result in batch_results:
            results.extend(batch_result)

        return results

    def optimize_query_patterns(self, cache: TTLCache, access_patterns: Dict[str, int]) -> Dict[str, Any]:
        """
        Optimize cache based on access patterns.

        Args:
            cache: Cache instance to optimize
            access_patterns: Dict mapping cache keys to access frequency

        Returns:
            Optimization statistics
        """
        # Sort by access frequency (most accessed first)
        sorted_patterns = sorted(access_patterns.items(), key=lambda x: x[1], reverse=True)

        # Calculate optimal TTL based on access frequency
        optimizations = {}
        for key, frequency in sorted_patterns:
            base_ttl: int = config.DASHBOARD_PLANS_CACHE_TTL
            if frequency > 100:  # High frequency
                optimal_ttl = base_ttl * 2  # Longer TTL
            elif frequency > 50:  # Medium frequency
                optimal_ttl = base_ttl  # Default TTL
            else:  # Low frequency
                optimal_ttl = base_ttl // 2  # Shorter TTL

            optimizations[key] = {
                "frequency": frequency,
                "optimal_ttl": optimal_ttl,
                "recommendation": "extend" if optimal_ttl > base_ttl else "reduce",
            }

        return {
            "total_keys": len(optimizations),
            "high_frequency": len([k for k, v in optimizations.items() if cast(int, v["frequency"]) > 100]),
            "medium_frequency": len([k for k, v in optimizations.items() if 50 <= cast(int, v["frequency"]) <= 100]),
            "low_frequency": len([k for k, v in optimizations.items() if cast(int, v["frequency"]) < 50]),
            "optimizations": optimizations,
        }

    @asynccontextmanager
    async def memory_monitor(self, threshold_mb: int = 100):
        """
        Context manager to monitor memory usage during operations.

        Args:
            threshold_mb: Memory threshold in MB to warn about
        """
        import gc

        # Force garbage collection before starting
        gc.collect()

        start_memory = self._get_memory_usage()
        start_time = time.time()

        try:
            yield {"start_memory_mb": start_memory / (1024 * 1024), "threshold_mb": threshold_mb}
        finally:
            # Force garbage collection after operation
            gc.collect()

            end_memory = self._get_memory_usage()
            duration = time.time() - start_time
            memory_growth = (end_memory - start_memory) / (1024 * 1024)  # MB

            if memory_growth > threshold_mb:
                print(f"⚠️  Memory usage exceeded threshold: {memory_growth:.2f}MB > {threshold_mb}MB")

            print(f"📊 Memory usage: {memory_growth:+.2f}MB over {duration:.2f}s")

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            # Fallback without psutil
            return 0


# Global performance service instance
performance_service = PerformanceService()
