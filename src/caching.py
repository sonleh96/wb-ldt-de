import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import streamlit as st
from google.cloud import storage
import pandas as pd

from src.config import (
    CACHE_VERSION,
    CATEGORY_OPTIONS_EN,
    CATEGORY_OPTIONS_SR,
    PROJECT_DETAILS_TTL_HOURS,
    PROJECT_DETAILS_TTL_ENABLED,
)

class ResponseCacheManager:
    """
    Manages caching of LLM responses using Google Cloud Storage for consistent outputs.
    """
    
    def __init__(self, storage_client: storage.Client, bucket_name: str, 
                 cache_path: str, df_indicators: pd.DataFrame):
        """
        Initialize the cache manager.
        """
        self.storage_client = storage_client
        self.bucket_name = bucket_name
        self.cache_path = cache_path
        self.cache_version = CACHE_VERSION
        self.bucket = self.storage_client.bucket(bucket_name)
        self.cache_file_path = f"{cache_path}/response_cache.json"
        
        self.category_options_en = CATEGORY_OPTIONS_EN
        self.category_options_sr = CATEGORY_OPTIONS_SR
        self.category_sr_to_en = dict(zip(self.category_options_sr, self.category_options_en))
        
        self.df_indicators = df_indicators
        if df_indicators is not None:
            region_mapping = df_indicators[['ENGLISH_NAME', 'SERBIAN_NAME_CYRILLIC']].drop_duplicates()
            self.region_sr_to_en = dict(zip(region_mapping['SERBIAN_NAME_CYRILLIC'], region_mapping['ENGLISH_NAME']))
            self.region_en_to_sr = dict(zip(region_mapping['ENGLISH_NAME'], region_mapping['SERBIAN_NAME_CYRILLIC']))
        else:
            self.region_sr_to_en = {}
            self.region_en_to_sr = {}
        
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load the cache from GCS or create an empty one."""
        try:
            blob = self.bucket.blob(self.cache_file_path)
            if blob.exists():
                cache_content = blob.download_as_text(encoding='utf-8')
                cache_data = json.loads(cache_content)
                
                if cache_data.get('version') != self.cache_version:
                    st.warning("Cache version mismatch. Creating new cache.")
                    return self._create_empty_cache()
                return cache_data
            else:
                return self._create_empty_cache()
        except Exception as e:
            st.warning(f"Failed to load cache from GCS: {e}. Creating new cache.")
            return self._create_empty_cache()
    
    def _create_empty_cache(self) -> Dict[str, Any]:
        """Create an empty cache structure."""
        return {
            "version": self.cache_version,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "responses": {},
            "project_details": {}
        }
    
    def _save_cache(self) -> None:
        """Save the cache to GCS."""
        self.cache["last_updated"] = datetime.now().isoformat()
        try:
            blob = self.bucket.blob(self.cache_file_path)
            cache_json = json.dumps(self.cache, ensure_ascii=False, indent=2)
            blob.upload_from_string(cache_json, content_type='application/json')
        except Exception as e:
            st.error(f"Failed to save cache to GCS: {e}")
    
    def _normalize_region_name(self, region: str) -> str:
        """Normalize region name to English for consistent cache keys."""
        if not region or not isinstance(region, str):
            return "Unknown Region"
        region_clean = region.strip()
        if region_clean in self.region_en_to_sr:
            return region_clean
        if region_clean in self.region_sr_to_en:
            return self.region_sr_to_en[region_clean]
        return region_clean

    def _normalize_category_name(self, category: str) -> str:
        """Normalize category name to English for consistent cache keys."""
        if not category or not isinstance(category, str):
            return "Unknown Category"
        category_clean = category.strip()
        if category_clean in self.category_options_en:
            return category_clean
        if category_clean in self.category_sr_to_en:
            return self.category_sr_to_en[category_clean]
        return category_clean
    
    def _generate_cache_key(self, region: str, subcategory: str, analysis_type: str, language: str = 'en') -> str:
        """Generate a unique cache key using English names for region and subcategory."""
        normalized_region = self._normalize_region_name(region.strip())
        normalized_subcategory = self._normalize_category_name(subcategory.strip())
        normalized_key = f"{normalized_region}_{normalized_subcategory}_{analysis_type}_{language}"
        return normalized_key.lower().replace(' ', '_')
    
    def get_cached_response(self, region: str, subcategory: str, analysis_type: str, language: str = 'en') -> Optional[Dict[str, Any]]:
        """Retrieve a cached response if it exists."""
        cache_key = self._generate_cache_key(region, subcategory, analysis_type, language)
        return self.cache["responses"].get(cache_key)
    
    def save_response(self, region: str, subcategory: str, analysis_type: str, response: str, language: str = 'en') -> None:
        """Save a response to the cache."""
        cache_key = self._generate_cache_key(region, subcategory, analysis_type, language)
        self.cache["responses"][cache_key] = {
            "content": response,
            "created_at": datetime.now().isoformat(),
            "region": region,
            "subcategory": subcategory,
            "analysis_type": analysis_type,
            "language": language
        }
        self._save_cache()
    
    def get_english_response(self, region: str, subcategory: str, analysis_type: str) -> Optional[str]:
        """Get the English response content for translation to Serbian."""
        cached_response = self.get_cached_response(region, subcategory, analysis_type, 'en')
        return cached_response['content'] if cached_response else None
    
    def clear_cache(self) -> None:
        """Clear all cached responses."""
        self.cache = self._create_empty_cache()
        self._save_cache()
        st.success("Response cache cleared successfully.")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        total_responses = len(self.cache["responses"])
        english_responses = sum(1 for key in self.cache["responses"].keys() if key.endswith('_en'))
        serbian_responses = sum(1 for key in self.cache["responses"].keys() if key.endswith('_sr'))
        
        return {
            "total_responses": total_responses,
            "english_responses": english_responses,
            "serbian_responses": serbian_responses,
            "cache_version": self.cache_version,
            "created_at": self.cache.get("created_at"),
            "last_updated": self.cache.get("last_updated"),
            "gcs_path": f"gs://{self.bucket_name}/{self.cache_file_path}"
        }

    # --- Project Details (by URL) with TTL ---

    def _normalize_project_url(self, project_url: str) -> str:
        if not project_url or not isinstance(project_url, str):
            return "unknown_project_url"
        return project_url.strip().lower()

    def _generate_project_details_key(self, project_url: str, language: str = 'en') -> str:
        normalized_url = self._normalize_project_url(project_url)
        return f"{normalized_url}__{language}"

    def get_cached_project_details(self, project_url: str, language: str = 'en') -> Optional[Dict[str, Any]]:
        """Retrieve cached project details. If TTL is enabled and exceeded, return None; otherwise return entry."""
        key = self._generate_project_details_key(project_url, language)
        entry = self.cache.get("project_details", {}).get(key)
        if not entry:
            return None
        # If TTL is disabled, do not expire
        if not PROJECT_DETAILS_TTL_ENABLED or (isinstance(PROJECT_DETAILS_TTL_HOURS, (int, float)) and PROJECT_DETAILS_TTL_HOURS <= 0):
            return entry
        # TTL is enabled - enforce expiration
        created_at_str = entry.get("created_at")
        if not created_at_str:
            return None
        try:
            created_at = datetime.fromisoformat(created_at_str)
        except Exception:
            return None
        ttl = timedelta(hours=PROJECT_DETAILS_TTL_HOURS)
        if datetime.now() - created_at > ttl:
            return None
        return entry

    def save_project_details(self, project_url: str, content_markdown: str, language: str = 'en', source_count: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Save project details markdown with metadata and timestamp."""
        key = self._generate_project_details_key(project_url, language)
        if "project_details" not in self.cache:
            self.cache["project_details"] = {}
        self.cache["project_details"][key] = {
            "project_url": project_url,
            "language": language,
            "content": content_markdown,
            "created_at": datetime.now().isoformat(),
            "source_count": source_count,
            "meta": metadata or {}
        }
        self._save_cache()
