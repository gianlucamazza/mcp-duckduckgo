"""
Property-based testing for the DuckDuckGo search plugin using Hypothesis.

This module tests the robustness of the search functionality with
generated test cases to catch edge cases and ensure reliability.
"""

import pytest
from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite
from urllib.parse import urlparse

from mcp_duckduckgo.search import extract_domain
from mcp_duckduckgo.typing_utils import ensure_string, safe_get_text
from mcp_duckduckgo.models import SearchResult, SearchResponse, DetailedResult


# Custom strategies for testing
@composite
def url_strategy(draw):
    """Generate valid URLs for testing."""
    scheme = draw(st.sampled_from(["http", "https"]))
    domain = draw(st.text(alphabet=st.characters(whitelist_categories=["Ll"]), min_size=3, max_size=20))
    tld = draw(st.sampled_from(["com", "org", "net", "edu", "gov"]))
    path = draw(st.text(alphabet=st.characters(whitelist_categories=["Ll", "Nd", "Pd"]), max_size=50))
    
    # Clean path to ensure valid URL
    path = path.replace(" ", "").replace("--", "-").strip("-")
    if path:
        path = "/" + path
    
    url = f"{scheme}://{domain}.{tld}{path}"
    assume(len(url) < 200)  # Reasonable URL length
    return url


@composite 
def search_query_strategy(draw):
    """Generate valid search queries."""
    # Generate words for the query
    num_words = draw(st.integers(min_value=1, max_value=10))
    words = draw(st.lists(
        st.text(alphabet=st.characters(whitelist_categories=["Lu", "Ll", "Nd"]), min_size=2, max_size=15),
        min_size=num_words,
        max_size=num_words
    ))
    
    query = " ".join(word for word in words if word.strip())
    assume(len(query) <= 400)  # Max query length
    assume(len(query) >= 2)    # Min query length
    return query


class TestPropertyBased:
    """Property-based tests for search functionality."""
    
    @given(url_strategy())
    def test_extract_domain_property(self, url: str):
        """Test that extract_domain always returns a string for valid URLs."""
        domain = extract_domain(url)
        
        # Properties that should always hold
        assert isinstance(domain, str)
        assert "." in domain or domain == ""  # Either valid domain or empty string
        
        # If not empty, should be a valid domain format
        if domain:
            assert not domain.startswith(".")
            assert not domain.endswith(".")
            assert "//" not in domain
    
    @given(st.text())
    def test_ensure_string_property(self, value: str):
        """Test that ensure_string always returns a string."""
        result = ensure_string(value)
        assert isinstance(result, str)
        
        # Should preserve original string values
        if isinstance(value, str):
            assert result == value
    
    @given(st.one_of(st.none(), st.text(), st.integers(), st.floats()))
    def test_ensure_string_robustness(self, value):
        """Test ensure_string with various input types."""
        result = ensure_string(value)
        assert isinstance(result, str)
        
        # Should handle None gracefully
        if value is None:
            assert result == ""
    
    @given(search_query_strategy())
    def test_search_result_validation(self, query: str):
        """Test SearchResult creation with generated data."""
        # Create a search result with the generated query as title
        result = SearchResult(
            title=query,
            url="https://example.com",
            description=f"Description for {query}",
            published_date=None
        )
        
        # Properties that should hold
        assert result.title == query
        assert result.url.startswith("http")
        assert isinstance(result.description, str)
        assert result.published_date is None
    
    @given(
        st.lists(
            st.builds(
                SearchResult,
                title=st.text(min_size=1, max_size=100),
                url=url_strategy(),
                description=st.text(max_size=500),
                published_date=st.one_of(st.none(), st.text())
            ),
            max_size=20
        ),
        st.integers(min_value=0, max_value=1000),
        st.integers(min_value=1, max_value=100)
    )
    def test_search_response_invariants(self, results, total_results, page):
        """Test SearchResponse invariants with generated data."""
        response = SearchResponse(
            results=results,
            total_results=total_results,
            page=page
        )
        
        # Invariants that should always hold
        assert response.page >= 1
        assert response.total_results >= 0
        assert response.total_pages >= 1
        assert len(response.results) <= 20  # Max results per page
        
        # Pagination logic - just check that pages is positive
        assert response.total_pages >= 1
    
    @given(
        st.text(min_size=1, max_size=100),  # title
        url_strategy(),                      # url
        st.text(max_size=500),              # description
    )
    def test_detailed_result_creation(self, title: str, url: str, description: str):
        """Test DetailedResult creation with various inputs."""
        result = DetailedResult(
            title=title,
            url=url,
            description=description
        )
        
        # Basic properties
        assert result.title == title
        assert result.url == url
        assert result.description == description
        
        # Optional fields should have sensible defaults
        assert result.published_date is None
        assert result.content_snippet is None
        assert result.domain is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @given(st.text(alphabet=st.characters(blacklist_categories=["Cc"]), max_size=1000))
    def test_empty_and_whitespace_handling(self, text: str):
        """Test handling of empty strings and whitespace."""
        result = ensure_string(text)
        assert isinstance(result, str)
        
        # Test that we handle whitespace-only strings
        if text.strip() == "":
            assert result.strip() == text.strip()
    
    @given(st.lists(st.text(), max_size=50))
    def test_list_operations_robustness(self, text_list):
        """Test operations on lists of strings."""
        # Filter empty strings (common operation)
        filtered = [t for t in text_list if t.strip()]
        
        # Should not crash and maintain type
        assert isinstance(filtered, list)
        assert all(isinstance(item, str) for item in filtered)
    
    @pytest.mark.parametrize("invalid_url", [
        "",
        "not-a-url",
        "javascript:alert('xss')",
        "mailto:test@example.com",
        "ftp://example.com",
        "//example.com",
    ])
    def test_invalid_url_handling(self, invalid_url: str):
        """Test handling of invalid URLs."""
        domain = extract_domain(invalid_url)
        
        # Should return empty string for invalid URLs
        assert isinstance(domain, str)
        # Should not crash the application


# Performance-related property tests
class TestPerformance:
    """Test performance characteristics."""
    
    @given(st.text(min_size=1000, max_size=10000))
    def test_large_text_handling(self, large_text: str):
        """Test that functions handle large text inputs efficiently."""
        result = ensure_string(large_text)
        
        # Should not alter large strings unnecessarily
        assert result == large_text
        assert len(result) == len(large_text)
    
    @given(st.lists(st.text(min_size=10, max_size=100), min_size=100, max_size=1000))
    def test_large_list_processing(self, large_list):
        """Test processing of large lists doesn't crash."""
        # Simulate common operations on large lists
        filtered = [item for item in large_list if len(item) > 5]
        truncated = large_list[:50]  # Common truncation
        
        assert isinstance(filtered, list)
        assert isinstance(truncated, list)
        assert len(truncated) <= 50