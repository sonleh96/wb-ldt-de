import pytest
import pandas as pd
from unittest.mock import MagicMock
from src.caching import ResponseCacheManager

@pytest.fixture
def mock_storage_client():
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_blob.exists.return_value = False # Default to cache not existing
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    return mock_client

@pytest.fixture
def sample_df_for_caching():
    data = {
        'ENGLISH_NAME': ['Belgrade', 'Novi Sad'],
        'SERBIAN_NAME_CYRILLIC': ['Београд', 'Нови Сад']
    }
    return pd.DataFrame(data)

@pytest.fixture
def cache_manager(mock_storage_client, sample_df_for_caching):
    return ResponseCacheManager(
        storage_client=mock_storage_client,
        bucket_name="test-bucket",
        cache_path="test-cache",
        df_indicators=sample_df_for_caching
    )

def test_normalize_region_name(cache_manager):
    assert cache_manager._normalize_region_name("Београд") == "Belgrade"
    assert cache_manager._normalize_region_name("Belgrade") == "Belgrade"
    assert cache_manager._normalize_region_name("Unknown Region") == "Unknown Region"

def test_normalize_category_name(cache_manager):
    # Using the real config values for this
    assert cache_manager._normalize_category_name("Образовање") == "Education"
    assert cache_manager._normalize_category_name("Education") == "Education"
    assert cache_manager._normalize_category_name("Unknown") == "Unknown"

def test_generate_cache_key(cache_manager):
    key = cache_manager._generate_cache_key("Београд", "Образовање", "regional", "sr")
    assert key == "belgrade_education_regional_sr"

def test_save_and_get_response(cache_manager):
    assert cache_manager.get_cached_response("Belgrade", "Education", "regional", "en") is None
    
    response_content = "This is a test response."
    cache_manager.save_response("Belgrade", "Education", "regional", response_content, "en")
    
    cached = cache_manager.get_cached_response("Belgrade", "Education", "regional", "en")
    assert cached is not None
    assert cached['content'] == response_content

def test_get_english_response(cache_manager):
    cache_manager.save_response("Novi Sad", "Health", "indicators", "English response", "en")
    
    # Test getting it directly
    response = cache_manager.get_english_response("Novi Sad", "Health", "indicators")
    assert response == "English response"
    
    # Test getting it via Serbian name normalization
    response_sr = cache_manager.get_english_response("Нови Сад", "Health", "indicators")
    assert response_sr == "English response"
