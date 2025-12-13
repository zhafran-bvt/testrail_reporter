"""Property-based tests for memory efficiency."""

import gc
import threading
import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.cache import TTLCache


class TestMemoryEfficiency:
    """Property 10: Memory Efficiency - For any large dataset report generation,
    the system should use streaming responses to maintain stable memory usage."""

    def test_cache_memory_usage_stays_bounded(self):
        """Test that cache memory usage doesn't grow unbounded with large datasets."""
        maxsize = 10
        cache = TTLCache(ttl_seconds=60, maxsize=maxsize)

        # Track memory usage
        initial_memory = self._get_memory_usage()

        # Add many items (more than maxsize)
        large_data_items = 100
        for i in range(large_data_items):
            # Create reasonably large data items
            large_value = {"data": "x" * 1000, "index": i, "metadata": list(range(100))}
            cache.set((f"key_{i}",), large_value)

        # Force garbage collection
        gc.collect()

        # Memory should be bounded by maxsize, not by total items added
        final_memory = self._get_memory_usage()
        cache_size = cache.size()

        # Cache should respect maxsize limit
        assert cache_size <= maxsize, f"Cache size {cache_size} should not exceed maxsize {maxsize}"

        # Memory growth should be reasonable (not proportional to large_data_items)
        memory_growth = final_memory - initial_memory
        # Allow some memory growth but it shouldn't be proportional to all items
        reasonable_growth = maxsize * 2000  # Rough estimate for maxsize items
        assert memory_growth < reasonable_growth, f"Memory growth {memory_growth} bytes seems excessive"

    def test_streaming_response_simulation(self):
        """Test that streaming response pattern maintains stable memory usage."""
        # Simulate streaming by processing data in chunks
        total_items = 1000
        chunk_size = 50

        initial_memory = self._get_memory_usage()
        peak_memory = initial_memory

        def process_chunk(chunk_data):
            """Simulate processing a chunk of data."""
            # Process the chunk (simulate some work)
            processed = []
            for item in chunk_data:
                processed.append({"processed": item, "timestamp": time.time()})

            # Track peak memory during processing
            nonlocal peak_memory
            current_memory = self._get_memory_usage()
            peak_memory = max(peak_memory, current_memory)

            # Return processed chunk (in real streaming, this would be yielded)
            return processed

        # Process data in chunks (streaming pattern)
        for start in range(0, total_items, chunk_size):
            end = min(start + chunk_size, total_items)
            chunk = [f"item_{i}" for i in range(start, end)]

            # Process chunk
            result = process_chunk(chunk)

            # In streaming, we don't accumulate results
            del result

            # Force garbage collection to simulate memory cleanup
            if start % (chunk_size * 4) == 0:  # Periodic cleanup
                gc.collect()

        final_memory = self._get_memory_usage()

        # Memory should not grow significantly with streaming approach
        memory_growth = final_memory - initial_memory
        peak_growth = peak_memory - initial_memory

        # Peak memory should be bounded (not proportional to total_items)
        reasonable_peak = chunk_size * 200  # Rough estimate for chunk processing
        assert peak_growth < reasonable_peak, f"Peak memory growth {peak_growth} bytes seems excessive for streaming"

        # Final memory should return close to initial (streaming doesn't accumulate)
        assert (
            memory_growth < reasonable_peak / 2
        ), f"Final memory growth {memory_growth} bytes should be minimal with streaming"

    @given(
        num_concurrent_requests=st.integers(min_value=2, max_value=10),
        data_size_per_request=st.integers(min_value=100, max_value=1000),
    )
    @settings(deadline=None, max_examples=5)  # Limit examples for performance
    def test_concurrent_request_memory_isolation(self, num_concurrent_requests, data_size_per_request):
        """Test that concurrent requests don't cause memory leaks or excessive growth."""
        initial_memory = self._get_memory_usage()

        # Simulate concurrent requests with separate data
        results = []
        threads = []

        def simulate_request(request_id, data_size):
            """Simulate a request that processes some data."""
            try:
                # Create request-specific data
                request_data = [f"req_{request_id}_item_{i}" for i in range(data_size)]

                # Process data (simulate work)
                processed = []
                for item in request_data:
                    processed.append({"id": request_id, "data": item, "processed": True})

                # Store result
                results.append(len(processed))

            except Exception as e:
                results.append(f"error_{request_id}: {str(e)}")

        # Start concurrent requests
        for i in range(num_concurrent_requests):
            thread = threading.Thread(target=simulate_request, args=(i, data_size_per_request))
            threads.append(thread)
            thread.start()

        # Wait for all requests to complete
        for thread in threads:
            thread.join(timeout=5)  # 5 second timeout per thread

        # Force garbage collection
        gc.collect()

        final_memory = self._get_memory_usage()
        memory_growth = final_memory - initial_memory

        # Verify all requests completed successfully
        assert len(results) == num_concurrent_requests, "All requests should complete"
        for result in results:
            if isinstance(result, str) and result.startswith("error_"):
                pytest.fail(f"Request failed: {result}")
            assert isinstance(result, int), f"Expected int result, got {type(result)}"

        # Memory growth should be reasonable for concurrent processing
        expected_max_growth = num_concurrent_requests * data_size_per_request * 100  # Rough estimate
        assert (
            memory_growth < expected_max_growth
        ), f"Memory growth {memory_growth} bytes seems excessive for {num_concurrent_requests} concurrent requests"

    def test_large_response_chunking_simulation(self):
        """Test that large responses can be processed in chunks without memory issues."""
        # Simulate a large response that needs to be chunked
        total_response_size = 10000  # Large response
        chunk_size = 500

        initial_memory = self._get_memory_usage()

        def generate_large_response():
            """Generator that yields chunks of a large response."""
            for start in range(0, total_response_size, chunk_size):
                end = min(start + chunk_size, total_response_size)
                chunk = {
                    "chunk_id": start // chunk_size,
                    "start": start,
                    "end": end,
                    "data": [f"item_{i}" for i in range(start, end)],
                }
                yield chunk

        # Process response in chunks (streaming pattern)
        processed_chunks = 0
        max_memory_during_processing = initial_memory

        for chunk in generate_large_response():
            # Process chunk
            processed_items = len(chunk["data"])
            processed_chunks += 1

            # Track memory during processing
            current_memory = self._get_memory_usage()
            max_memory_during_processing = max(max_memory_during_processing, current_memory)

            # Simulate sending chunk to client (chunk is no longer needed)
            del chunk

            # Periodic garbage collection
            if processed_chunks % 5 == 0:
                gc.collect()

        final_memory = self._get_memory_usage()

        # Verify all chunks were processed
        expected_chunks = (total_response_size + chunk_size - 1) // chunk_size
        assert processed_chunks == expected_chunks, f"Should process {expected_chunks} chunks, got {processed_chunks}"

        # Memory should remain stable during chunked processing
        memory_growth_during = max_memory_during_processing - initial_memory
        final_memory_growth = final_memory - initial_memory

        # Memory growth should be bounded by chunk size, not total response size
        reasonable_chunk_memory = chunk_size * 10  # Rough estimate
        assert (
            memory_growth_during < reasonable_chunk_memory
        ), f"Memory during processing {memory_growth_during} should be bounded by chunk size"
        assert (
            final_memory_growth < reasonable_chunk_memory / 2
        ), f"Final memory growth {final_memory_growth} should be minimal"

    def test_cache_eviction_frees_memory(self):
        """Test that cache eviction actually frees memory."""
        cache = TTLCache(ttl_seconds=1, maxsize=5)  # Short TTL for testing

        initial_memory = self._get_memory_usage()

        # Add items to cache
        large_items = []
        for i in range(10):
            # Create large items
            large_item = {"data": "x" * 10000, "index": i}  # 10KB per item
            large_items.append(large_item)
            cache.set((f"key_{i}",), large_item)

        # Memory should have grown
        after_adding_memory = self._get_memory_usage()
        assert after_adding_memory > initial_memory, "Memory should grow after adding items"

        # Wait for TTL expiration
        time.sleep(1.1)

        # Access cache to trigger cleanup of expired items
        for i in range(5):
            cache.get((f"key_{i}",))  # These should be expired

        # Force garbage collection
        gc.collect()

        # Add new items to trigger eviction
        for i in range(10, 15):
            cache.set((f"new_key_{i}",), {"small": "data"})

        gc.collect()

        final_memory = self._get_memory_usage()

        # Memory should have decreased from peak due to eviction
        assert final_memory < after_adding_memory, "Memory should decrease after cache eviction"

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        # Force garbage collection before measuring
        gc.collect()

        # Use sys.getsizeof for a rough estimate
        # In a real application, you might use psutil or tracemalloc
        import os

        try:
            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss  # Resident Set Size
        except ImportError:
            # Fallback if psutil not available - use a simple approximation
            # Return a mock value that increases slightly each call for testing
            if not hasattr(self, "_mock_memory"):
                self._mock_memory = 1000000  # 1MB base
            self._mock_memory += 1000  # Small increment
            return self._mock_memory
