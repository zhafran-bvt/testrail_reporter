"""Property-based tests for cache efficiency."""

import time
import pytest
from hypothesis import given, strategies as st

from app.services.cache import TTLCache, cache_meta


class TestCacheEfficiency:
    """Property 8: Cache Efficiency - For any cacheable request, 
    the system should use improved cache key strategies and respect TTL settings."""
    
    @given(
        ttl_seconds=st.integers(min_value=1, max_value=300),
        maxsize=st.integers(min_value=1, max_value=100),
        key_parts=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5),
        value=st.one_of(st.text(), st.integers(), st.dictionaries(st.text(), st.integers()))
    )
    def test_cache_respects_ttl_settings(self, ttl_seconds, maxsize, key_parts, value):
        """Test that cache properly respects TTL settings for any configuration."""
        cache = TTLCache(ttl_seconds=ttl_seconds, maxsize=maxsize)
        key = tuple(key_parts)
        
        # Set value in cache
        expires_at = cache.set(key, value)
        
        # Should be retrievable immediately
        result = cache.get(key)
        assert result is not None, "Value should be retrievable immediately after setting"
        
        cached_value, cached_expires_at = result
        assert cached_expires_at == expires_at, "Expiration time should match"
        
        # Value should match (accounting for dict copying)
        if isinstance(value, dict):
            assert cached_value == value, "Cached dict should match original"
            assert cached_value is not value, "Cached dict should be a copy"
        else:
            assert cached_value == value, "Cached value should match original"
    
    @given(
        ttl_seconds=st.integers(min_value=1, max_value=10),
        key_parts=st.lists(st.text(min_size=1, max_size=5), min_size=1, max_size=3)
    )
    def test_cache_key_strategies_are_unique(self, ttl_seconds, key_parts):
        """Test that cache key strategies produce unique keys for different inputs."""
        cache = TTLCache(ttl_seconds=ttl_seconds)
        
        # Create multiple similar but different keys
        key1 = tuple(key_parts)
        key2 = tuple(key_parts + ["extra"])
        key3 = tuple(["prefix"] + key_parts)
        
        # Set different values for each key
        cache.set(key1, "value1")
        cache.set(key2, "value2") 
        cache.set(key3, "value3")
        
        # Each key should retrieve its own value
        result1 = cache.get(key1)
        result2 = cache.get(key2)
        result3 = cache.get(key3)
        
        assert result1 is not None and result1[0] == "value1"
        assert result2 is not None and result2[0] == "value2"
        assert result3 is not None and result3[0] == "value3"
    
    @given(
        maxsize=st.integers(min_value=2, max_value=10),
        num_items=st.integers(min_value=1, max_value=20)
    )
    def test_cache_size_limits_are_respected(self, maxsize, num_items):
        """Test that cache respects size limits and evicts old items."""
        cache = TTLCache(ttl_seconds=300, maxsize=maxsize)  # Long TTL to test size limits
        
        # Add items up to and beyond the limit
        for i in range(num_items):
            key = (f"key_{i}",)
            cache.set(key, f"value_{i}")
        
        # Cache size should not exceed maxsize
        actual_size = cache.size()
        assert actual_size <= maxsize, f"Cache size {actual_size} should not exceed maxsize {maxsize}"
        
        # If we added more items than maxsize, some should have been evicted
        if num_items > maxsize:
            # The most recent items should still be in cache
            recent_keys = [(f"key_{i}",) for i in range(num_items - maxsize, num_items)]
            for key in recent_keys:
                result = cache.get(key)
                assert result is not None, f"Recent key {key} should still be in cache"
    
    def test_cache_meta_provides_accurate_information(self):
        """Test that cache metadata provides accurate hit/miss and expiration information."""
        cache = TTLCache(ttl_seconds=60, maxsize=10)
        key = ("test_key",)
        value = {"test": "data"}
        
        # Test cache miss
        result = cache.get(key)
        assert result is None, "Should be cache miss initially"
        
        # Set value and test cache hit
        expires_at = cache.set(key, value)
        result = cache.get(key)
        assert result is not None, "Should be cache hit after setting"
        
        cached_value, cached_expires_at = result
        
        # Test cache metadata generation
        hit_meta = cache_meta(True, cached_expires_at)
        miss_meta = cache_meta(False, expires_at)
        
        # Verify metadata structure
        assert "cache" in hit_meta
        assert "cache" in miss_meta
        
        cache_info = hit_meta["cache"]
        assert cache_info["hit"] is True
        assert "expires_at" in cache_info
        assert "seconds_remaining" in cache_info
        assert isinstance(cache_info["seconds_remaining"], int)
        assert cache_info["seconds_remaining"] >= 0
        
        miss_info = miss_meta["cache"]
        assert miss_info["hit"] is False
    
    @given(
        custom_ttl=st.integers(min_value=1, max_value=100)
    )
    def test_cache_supports_custom_ttl_per_item(self, custom_ttl):
        """Test that cache supports setting custom TTL for individual items."""
        cache = TTLCache(ttl_seconds=300)  # Default TTL
        key = ("custom_ttl_key",)
        value = "custom_ttl_value"
        
        # Set with custom TTL
        expires_at = cache.set(key, value, ttl_seconds=custom_ttl)
        
        # Verify the custom TTL is used
        expected_expires_at = time.time() + custom_ttl
        # Allow for small timing differences (within 2 seconds)
        assert abs(expires_at - expected_expires_at) < 2, "Custom TTL should be respected"
        
        # Value should be retrievable
        result = cache.get(key)
        assert result is not None, "Value should be retrievable with custom TTL"
        
        cached_value, cached_expires_at = result
        assert cached_value == value
        assert cached_expires_at == expires_at
    
    def test_cache_statistics_accuracy(self):
        """Test that cache statistics provide accurate information."""
        ttl_seconds = 120
        maxsize = 5
        cache = TTLCache(ttl_seconds=ttl_seconds, maxsize=maxsize)
        
        # Get initial stats
        stats = cache.stats()
        assert stats["size"] == 0
        assert stats["maxsize"] == maxsize
        assert stats["ttl_seconds"] == ttl_seconds
        
        # Add some items
        for i in range(3):
            cache.set((f"key_{i}",), f"value_{i}")
        
        # Check updated stats
        stats = cache.stats()
        assert stats["size"] == 3
        assert stats["maxsize"] == maxsize
        assert stats["ttl_seconds"] == ttl_seconds
        
        # Clear cache and verify
        cache.clear()
        stats = cache.stats()
        assert stats["size"] == 0
    
    @given(
        num_operations=st.integers(min_value=10, max_value=50)
    )
    def test_cache_thread_safety_properties(self, num_operations):
        """Test that cache operations maintain consistency under concurrent access."""
        import threading
        
        cache = TTLCache(ttl_seconds=60, maxsize=20)
        results = []
        errors = []
        
        def cache_operations(thread_id):
            try:
                for i in range(num_operations // 5):  # Reduce operations per thread
                    key = (f"thread_{thread_id}_key_{i}",)
                    value = f"thread_{thread_id}_value_{i}"
                    
                    # Set value
                    cache.set(key, value)
                    
                    # Get value
                    result = cache.get(key)
                    if result is not None:
                        cached_value, _ = result
                        results.append((key, cached_value == value))
                    
                    # Test cache size
                    size = cache.size()
                    results.append(("size_check", isinstance(size, int) and size >= 0))
                    
            except Exception as e:
                errors.append(str(e))
        
        # Run multiple threads
        threads = []
        for i in range(3):  # Use fewer threads to avoid overwhelming
            thread = threading.Thread(target=cache_operations, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # Verify all operations succeeded
        for key, success in results:
            if key != "size_check":
                assert success, f"Cache operation failed for key: {key}"
            else:
                assert success, "Size check failed"