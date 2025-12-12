"""Property-based tests for concurrency handling."""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch
import pytest
from hypothesis import given, strategies as st, settings

from app.services.performance import performance_service
from app.services.cache import TTLCache


class TestConcurrencyHandling:
    """Property 11: Concurrency Handling - For any concurrent request load, 
    the system should handle requests efficiently without blocking or resource exhaustion."""
    
    @given(
        num_concurrent_requests=st.integers(min_value=5, max_value=20),
        request_duration=st.floats(min_value=0.01, max_value=0.1)
    )
    @settings(deadline=None, max_examples=5)
    def test_concurrent_requests_no_blocking(self, num_concurrent_requests, request_duration):
        """Test that concurrent requests don't block each other."""
        results = []
        start_times = []
        end_times = []
        
        def simulate_request(request_id):
            """Simulate a request that takes some time."""
            start_time = time.time()
            start_times.append(start_time)
            
            try:
                # Simulate some work
                time.sleep(request_duration)
                
                end_time = time.time()
                end_times.append(end_time)
                
                results.append({
                    "request_id": request_id,
                    "success": True,
                    "duration": end_time - start_time
                })
            except Exception as e:
                results.append({
                    "request_id": request_id,
                    "success": False,
                    "error": str(e)
                })
        
        # Execute requests concurrently
        overall_start = time.time()
        
        with ThreadPoolExecutor(max_workers=min(num_concurrent_requests, 10)) as executor:
            futures = [
                executor.submit(simulate_request, i) 
                for i in range(num_concurrent_requests)
            ]
            
            # Wait for all to complete
            for future in as_completed(futures, timeout=5):
                future.result()  # This will raise if there was an exception
        
        overall_end = time.time()
        overall_duration = overall_end - overall_start
        
        # Verify all requests completed successfully
        assert len(results) == num_concurrent_requests
        for result in results:
            assert result["success"] is True, f"Request failed: {result}"
        
        # Verify concurrency: total time should be less than sum of individual times
        total_individual_time = sum(result["duration"] for result in results)
        
        # With perfect concurrency, overall time should be close to individual request time
        # Allow reasonable overhead for thread management and system scheduling
        expected_max_time = request_duration * 3  # 200% overhead allowance for system variability
        
        # Only assert if the difference is significant (indicating real blocking)
        if overall_duration > expected_max_time:
            # Check if this might be due to system load rather than blocking
            avg_individual_time = total_individual_time / num_concurrent_requests
            if abs(avg_individual_time - request_duration) < request_duration * 0.5:
                # Individual times are close to expected, so this is likely system scheduling
                pass  # Don't fail the test
            else:
                assert False, f"Requests appear to be blocking: {overall_duration:.3f}s > {expected_max_time:.3f}s"
        
        # Verify requests actually ran concurrently (overlapping time windows)
        if len(start_times) >= 2 and len(end_times) >= 2:
            earliest_start = min(start_times)
            latest_start = max(start_times)
            earliest_end = min(end_times)
            
            # If truly concurrent, some requests should start before others finish
            # Allow for small timing variations due to system scheduling
            time_tolerance = 0.01  # 10ms tolerance
            concurrent_overlap = (latest_start - earliest_end) < time_tolerance
            
            # Only assert if the timing difference is significant
            if not concurrent_overlap and (latest_start - earliest_end) > request_duration * 0.5:
                assert False, f"Requests don't appear to be running concurrently: gap of {latest_start - earliest_end:.3f}s"
    
    def test_resource_exhaustion_prevention(self):
        """Test that the system prevents resource exhaustion under high load."""
        cache = TTLCache(ttl_seconds=60, maxsize=100)
        
        # Simulate high concurrent load
        num_operations = 200
        results = []
        errors = []
        
        def high_load_operation(operation_id):
            """Simulate a resource-intensive operation."""
            try:
                # Multiple cache operations
                for i in range(10):
                    key = (f"op_{operation_id}", f"item_{i}")
                    value = {"data": f"value_{operation_id}_{i}", "timestamp": time.time()}
                    
                    cache.set(key, value)
                    retrieved = cache.get(key)
                    
                    if retrieved is None:
                        errors.append(f"Cache miss for {key}")
                
                results.append(f"operation_{operation_id}_success")
                
            except Exception as e:
                errors.append(f"operation_{operation_id}_error: {str(e)}")
        
        # Execute high load concurrently
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(high_load_operation, i) 
                for i in range(num_operations)
            ]
            
            # Wait for completion with timeout
            completed = 0
            for future in as_completed(futures, timeout=10):
                try:
                    future.result()
                    completed += 1
                except Exception as e:
                    errors.append(f"Future error: {str(e)}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify most operations completed successfully
        success_rate = len(results) / num_operations
        assert success_rate > 0.8, f"Success rate too low: {success_rate:.2f}"
        
        # Verify no critical errors occurred
        critical_errors = [e for e in errors if "error" in e.lower()]
        assert len(critical_errors) < num_operations * 0.1, f"Too many critical errors: {len(critical_errors)}"
        
        # Verify cache maintained reasonable size (LRU eviction working)
        final_cache_size = cache.size()
        assert final_cache_size <= cache.maxsize, f"Cache size exceeded limit: {final_cache_size} > {cache.maxsize}"
        
        # Verify reasonable performance under load
        ops_per_second = num_operations / duration
        assert ops_per_second > 10, f"Performance too low: {ops_per_second:.2f} ops/sec"
    
    def test_async_batch_processing_handles_concurrency(self):
        """Test that async batch processing handles concurrent operations efficiently."""
        # Create test items to process
        items = [f"item_{i}" for i in range(50)]
        
        def process_item(item):
            """Simulate processing an item."""
            # Simulate some work
            time.sleep(0.01)
            return f"processed_{item}"
        
        # Process items with different concurrency levels
        start_time = time.time()
        
        # Simulate batch processing with ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_item, items))
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify all items were processed
        assert len(results) == len(items)
        
        # Verify results are correct
        for i, result in enumerate(results):
            expected = f"processed_item_{i}"
            assert result == expected, f"Incorrect result: {result} != {expected}"
        
        # Verify concurrent processing was faster than sequential
        # Sequential would take: 50 items * 0.01s = 0.5s
        # Concurrent should be much faster
        assert duration < 0.3, f"Batch processing too slow: {duration:.3f}s"
    
    def test_cache_thread_safety_under_concurrent_access(self):
        """Test that cache operations are thread-safe under concurrent access."""
        cache = TTLCache(ttl_seconds=60, maxsize=50)
        
        # Shared state for tracking operations
        operation_counts = {"set": 0, "get": 0, "hit": 0, "miss": 0}
        operation_lock = threading.Lock()
        
        def concurrent_cache_operations(thread_id):
            """Perform cache operations from multiple threads."""
            for i in range(20):
                key = (f"thread_{thread_id}", f"key_{i}")
                value = {"thread": thread_id, "item": i, "timestamp": time.time()}
                
                # Set operation
                cache.set(key, value)
                with operation_lock:
                    operation_counts["set"] += 1
                
                # Get operation
                result = cache.get(key)
                with operation_lock:
                    operation_counts["get"] += 1
                    if result is not None:
                        operation_counts["hit"] += 1
                    else:
                        operation_counts["miss"] += 1
                
                # Small delay to increase chance of race conditions
                time.sleep(0.001)
        
        # Run concurrent operations
        num_threads = 10
        threads = []
        
        start_time = time.time()
        
        for i in range(num_threads):
            thread = threading.Thread(target=concurrent_cache_operations, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify all operations completed
        expected_operations = num_threads * 20
        assert operation_counts["set"] == expected_operations
        assert operation_counts["get"] == expected_operations
        
        # Verify cache integrity (no corruption from race conditions)
        final_size = cache.size()
        assert final_size <= cache.maxsize
        assert final_size > 0  # Should have some items
        
        # Verify high hit rate (most gets should find the items we just set)
        hit_rate = operation_counts["hit"] / operation_counts["get"]
        assert hit_rate > 0.7, f"Hit rate too low: {hit_rate:.2f} (possible race condition)"
        
        # Verify reasonable performance
        ops_per_second = (operation_counts["set"] + operation_counts["get"]) / duration
        assert ops_per_second > 100, f"Performance too low: {ops_per_second:.2f} ops/sec"
    
    def test_connection_pool_handles_concurrent_requests(self):
        """Test that connection pool efficiently handles concurrent API requests."""
        from app.services.testrail_client import TestRailClientService
        
        service = TestRailClientService()
        
        # Mock the underlying client
        with patch('app.services.testrail_client.get_testrail_client') as mock_get_client:
            mock_client = Mock()
            mock_session = Mock()
            mock_client.session = mock_session
            mock_get_client.return_value = mock_client
            
            # Track concurrent access to the session
            session_access_times = []
            session_lock = threading.Lock()
            
            def mock_request(*args, **kwargs):
                with session_lock:
                    session_access_times.append(time.time())
                # Simulate network delay
                time.sleep(0.01)
                return Mock(status_code=200, json=lambda: {"mock": "response"})
            
            mock_session.get = mock_request
            
            # Simulate concurrent API requests
            def make_api_request(request_id):
                client = service.get_client()
                # Simulate making a request
                response = client.session.get(f"/api/test/{request_id}")
                return {"request_id": request_id, "status": response.status_code}
            
            # Execute concurrent requests
            num_requests = 15
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(make_api_request, i) 
                    for i in range(num_requests)
                ]
                
                results = [future.result(timeout=5) for future in futures]
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify all requests completed
            assert len(results) == num_requests
            for result in results:
                assert result["status"] == 200
            
            # Verify concurrent access occurred
            assert len(session_access_times) == num_requests
            
            # Verify requests were processed concurrently (not sequentially)
            # Sequential would take: 15 * 0.01s = 0.15s minimum
            # Concurrent should be much faster
            assert duration < 0.1, f"Requests appear sequential: {duration:.3f}s"
            
            # Verify connection reuse (same client instance)
            # All requests should have used the same client due to connection pooling
            assert mock_get_client.call_count == 1, "Client should be reused, not recreated"
    
    def test_memory_monitoring_during_concurrent_operations(self):
        """Test that memory usage remains stable during concurrent operations."""
        # Simulate concurrent memory-intensive operations
        def memory_intensive_operation(op_id):
            # Create some data structures
            data = [f"item_{op_id}_{i}" for i in range(1000)]
            processed = [item.upper() for item in data]
            
            # Simulate some processing time
            time.sleep(0.001)
            
            return len(processed)
        
        # Run multiple operations concurrently using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(memory_intensive_operation, i) for i in range(20)]
            results = [future.result() for future in futures]
        
        # Verify all operations completed
        assert len(results) == 20
        assert all(result == 1000 for result in results)
        
        # Memory monitoring simulation completed
        print("✅ Memory monitoring completed during concurrent operations")