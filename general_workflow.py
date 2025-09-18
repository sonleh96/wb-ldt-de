import json
import os
import re
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import hashlib
from io import BytesIO
import time

from openai import OpenAI
import pandas as pd
import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account

os.environ["OPENAI_API_KEY"] = os.getenv('openai_apikey')
sleep_t = 0


class ResponseCacheManager:
    """
    Manages caching of LLM responses using Google Cloud Storage for consistent outputs across app instances.
    
    The cache is organized by region and subcategory combinations, with separate
    entries for English and Serbian responses. This ensures deterministic outputs
    and reduces API costs.
    """
    
    def __init__(self, storage_client: storage.Client, bucket_name: str = "wb-ldt", 
                 cache_path: str = "decision_engine/cached_responses", df_indicators: pd.DataFrame = None):
        """
        Initialize the cache manager with GCS client.
        
        Args:
            storage_client (storage.Client): Google Cloud Storage client
            bucket_name (str): GCS bucket name
            cache_path (str): Path prefix in the bucket for cache files
        """
        self.storage_client = storage_client
        self.bucket_name = bucket_name
        self.cache_path = cache_path
        self.cache_version = "1.0"  # Increment when prompts/functions change
        self.bucket = self.storage_client.bucket(bucket_name)
        self.cache_file_path = f"{cache_path}/response_cache.json"
        
        # Category mappings for cache key normalization
        self.category_options_en = ["Education", "Energy Access", "Environment", "Digitalization", "Health", "Sustainable Transport"]
        self.category_options_sr = ["Образовање", "Приступ енергији", "Животна средина", "Дигитализација", "Здравље", "Одрживи транспорт"]
        self.category_sr_to_en = dict(zip(self.category_options_sr, self.category_options_en))
        self.category_en_to_sr = dict(zip(self.category_options_en, self.category_options_sr))
        
        # Region mappings for cache key normalization
        self.df_indicators = df_indicators
        if df_indicators is not None:
            # Create mappings from Serbian to English region names
            region_mapping = df_indicators[['ENGLISH_NAME', 'SERBIAN_NAME_CYRILLIC']].drop_duplicates()
            self.region_sr_to_en = dict(zip(region_mapping['SERBIAN_NAME_CYRILLIC'], region_mapping['ENGLISH_NAME']))
            self.region_en_to_sr = dict(zip(region_mapping['ENGLISH_NAME'], region_mapping['SERBIAN_NAME_CYRILLIC']))
        else:
            self.region_sr_to_en = {}
            self.region_en_to_sr = {}
        
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load the cache from GCS or create empty cache."""
        try:
            blob = self.bucket.blob(self.cache_file_path)
            if blob.exists():
                cache_content = blob.download_as_text(encoding='utf-8')
                cache_data = json.loads(cache_content)
                
                # Validate cache version
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
            "responses": {}
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
        """
        Normalize region name to English for consistent cache keys.
        
        Args:
            region (str): Region name in either English or Serbian
            
        Returns:
            str: English region name
        """
        if not region or not isinstance(region, str):
            st.warning(f"Invalid region name: {region}")
            return "Unknown Region"
            
        region_clean = region.strip()
        
        # If it's already in English, return as is
        if region_clean in self.region_en_to_sr:
            return region_clean
        
        # If it's in Serbian, convert to English
        if region_clean in self.region_sr_to_en:
            return self.region_sr_to_en[region_clean]
        
        # If not found in mappings, log warning and return original
        # This prevents Serbian names from being used in English prompts
        if region_clean:
            st.warning(f"Region '{region_clean}' not found in region mappings. This may cause Serbian names in English responses.")
            # Try to find a close match or provide a safe fallback
            available_regions = list(self.region_en_to_sr.keys()) + list(self.region_sr_to_en.keys())
            st.info(f"Available regions: {', '.join(available_regions[:5])}...")
        
        return region_clean
    
    def _normalize_category_name(self, category: str) -> str:
        """
        Normalize category name to English for consistent cache keys.
        
        Args:
            category (str): Category name in either English or Serbian
            
        Returns:
            str: English category name
        """
        if not category or not isinstance(category, str):
            st.warning(f"Invalid category name: {category}")
            return "Unknown Category"
            
        category_clean = category.strip()
        
        # If it's already in English, return as is
        if category_clean in self.category_options_en:
            return category_clean
        
        # If it's in Serbian, convert to English
        if category_clean in self.category_sr_to_en:
            return self.category_sr_to_en[category_clean]
        
        # If not found in mappings, log warning and return original
        # This prevents Serbian names from being used in English prompts
        if category_clean:
            st.warning(f"Category '{category_clean}' not found in category mappings. This may cause Serbian names in English responses.")
            st.info(f"Available categories: {', '.join(self.category_options_en)}")
        
        return category_clean
    
    def _generate_cache_key(self, region: str, subcategory: str, analysis_type: str, language: str = 'en') -> str:
        """
        Generate a unique cache key for a specific analysis request.
        Always uses English names for region and subcategory to ensure consistency.
        
        Args:
            region (str): Region name (in any language)
            subcategory (str): Subcategory name (in any language)
            analysis_type (str): Type of analysis ('indicators', 'regional', 'projects')
            language (str): Language code ('en' or 'sr')
            
        Returns:
            str: Unique cache key using English names
        """
        # Normalize region and subcategory to English for consistent cache keys
        normalized_region = self._normalize_region_name(region.strip())
        normalized_subcategory = self._normalize_category_name(subcategory.strip())
        
        # Validation: Check if we accidentally have Serbian names in English cache keys
        if language == 'en':
            # For English responses, ensure we're using English names
            if normalized_region in self.region_sr_to_en.keys():
                st.error(f"Cache key generation error: Serbian region name '{normalized_region}' found in English response generation")
            if normalized_subcategory in self.category_sr_to_en.keys():
                st.error(f"Cache key generation error: Serbian category name '{normalized_subcategory}' found in English response generation")
        
        # Generate cache key using English names
        normalized_key = f"{normalized_region}_{normalized_subcategory}_{analysis_type}_{language}"
        return normalized_key.lower().replace(' ', '_')
    
    def get_cached_response(self, region: str, subcategory: str, analysis_type: str, language: str = 'en') -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached response if it exists.
        
        Args:
            region (str): Region name
            subcategory (str): Subcategory name
            analysis_type (str): Type of analysis ('indicators', 'regional', 'projects')
            language (str): Language code ('en' or 'sr')
            
        Returns:
            Optional[Dict[str, Any]]: Cached response or None if not found
        """
        cache_key = self._generate_cache_key(region, subcategory, analysis_type, language)
        return self.cache["responses"].get(cache_key)
    
    def save_response(self, region: str, subcategory: str, analysis_type: str, response: str, language: str = 'en') -> None:
        """
        Save a response to the cache.
        
        Args:
            region (str): Region name
            subcategory (str): Subcategory name
            analysis_type (str): Type of analysis ('indicators', 'regional', 'projects')
            response (str): The response content to cache
            language (str): Language code ('en' or 'sr')
        """
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
    
    def has_english_response(self, region: str, subcategory: str, analysis_type: str) -> bool:
        """
        Check if an English response exists for the given parameters.
        
        This is useful for Serbian translation caching - we can reuse English responses.
        
        Args:
            region (str): Region name
            subcategory (str): Subcategory name
            analysis_type (str): Type of analysis ('indicators', 'regional', 'projects')
            
        Returns:
            bool: True if English response exists
        """
        return self.get_cached_response(region, subcategory, analysis_type, 'en') is not None
    
    def get_english_response(self, region: str, subcategory: str, analysis_type: str) -> Optional[str]:
        """
        Get the English response content for translation to Serbian.
        
        Args:
            region (str): Region name
            subcategory (str): Subcategory name
            analysis_type (str): Type of analysis ('indicators', 'regional', 'projects')
            
        Returns:
            Optional[str]: English response content or None if not found
        """
        cached_response = self.get_cached_response(region, subcategory, analysis_type, 'en')
        if cached_response:
            return cached_response['content']
        return None
    
    def clear_cache(self) -> None:
        """Clear all cached responses (for admin use)."""
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

    def show_cache_admin_panel(self) -> None:
        """Display cache administration panel in Streamlit sidebar."""
        with st.sidebar.expander("🗄️ Cache Management (GCS)", expanded=False):
            stats = self.get_cache_stats()
            
            st.write("**Cache Statistics:**")
            st.write(f"- Total responses: {stats['total_responses']}")
            st.write(f"- English responses: {stats['english_responses']}")
            st.write(f"- Serbian responses: {stats['serbian_responses']}")
            st.write(f"- Cache version: {stats['cache_version']}")
            st.write(f"- GCS Path: `{stats['gcs_path']}`")
            
            if stats['last_updated']:
                st.write(f"- Last updated: {stats['last_updated'][:19]}")
            
            # Cache management buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📊 View Cache", help="View detailed cache contents"):
                    st.json(self.cache)
            
            with col2:
                if st.button("🗑️ Clear Cache", help="Clear all cached responses"):
                    self.clear_cache()
            
            # Export functionality
            st.write("**Export:**")
            if st.button("📥 Export Cache", help="Download cache as JSON"):
                st.download_button(
                    label="Download cache.json",
                    data=json.dumps(self.cache, ensure_ascii=False, indent=2),
                    file_name=f"response_cache_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            # Reload cache button
            if st.button("🔄 Reload Cache", help="Reload cache from GCS"):
                self.cache = self._load_cache()
                st.success("Cache reloaded from GCS")


def run_analysis(
    df_indicatorlist: pd.DataFrame,
    df_indicators: pd.DataFrame,
    averages_df: pd.DataFrame,
    df_projects: pd.DataFrame,
    regions: List[str],
    storage_client: storage.Client,
    language: str = 'en'
) -> None:
    """
    Main function to run the analysis pipeline for the LDT Decision Engine.
    
    This function orchestrates the entire analysis process including:
    - Indicator analysis
    - Regional analysis
    - Project recommendations
    
    Args:
        df_indicatorlist (pd.DataFrame): DataFrame containing the list of indicators and their metadata
        df_indicators (pd.DataFrame): DataFrame containing the actual indicator values for each region
        averages_df (pd.DataFrame): DataFrame containing national averages for each indicator
        df_projects (pd.DataFrame): DataFrame containing project examples and their details
        regions (List[str]): List of available regions for analysis
        storage_client (storage.Client): Google Cloud Storage client for caching
        language (str, optional): Language code for the interface. Defaults to 'en'.
                                Supported values: 'en' (English), 'sr' (Serbian)
    
    Returns:
        None: This function updates the Streamlit interface directly
    """
    
    # Initialize the response cache manager with GCS client and region mappings
    cache_manager = ResponseCacheManager(storage_client, df_indicators=df_indicators)
    
    # Show cache admin panel in sidebar (for developers/admins)
    cache_manager.show_cache_admin_panel()
    
    ##Functions Required For Analysis##

    @st.cache_data
    def extract_regional_data(
        df: pd.DataFrame,
        region: str,
        relevant_columns: List[str],
        language: str = 'en'
    ) -> pd.DataFrame:
        """
        Filters the DataFrame based on the specified region and relevant columns.

        Args:
            df (pd.DataFrame): The dataset containing all regions and indicators
            region (str): The region to filter by
            relevant_columns (List[str]): List of column names to keep
            language (str, optional): Language code. Defaults to 'en'

        Returns:
            pd.DataFrame: Filtered DataFrame containing only the specified region and columns
        """
        if language == 'en':
            lang_col = "ENGLISH_NAME"
        elif language == 'sr':
            lang_col = 'SERBIAN_NAME_CYRILLIC'
        else:
            lang_col = "ENGLISH_NAME"  # Default fallback

        valid_columns = [col for col in relevant_columns if col in df.columns]
        return df.loc[df[lang_col] == region, valid_columns]

    @st.cache_data
    def extract_national_data(
        df: pd.DataFrame,
        relevant_columns: List[str]
    ) -> pd.DataFrame:
        """
        Extracts national average data for specified columns.

        Args:
            df (pd.DataFrame): DataFrame containing national averages
            relevant_columns (List[str]): List of columns to extract

        Returns:
            pd.DataFrame: DataFrame containing only the specified columns
        """
        valid_columns = [col for col in relevant_columns if col in df.columns]
        return df[valid_columns]
    
    @st.cache_data
    def translate_en_to_sr(text: str) -> str:
        """
        Translates English text to Serbian with caching for better performance.
        
        This function uses GPT-4.1-mini to perform high-quality translations while
        preserving Markdown formatting and following specific translation rules
        for public sector terminology.
        
        Args:
            text (str): The English text to translate
            
        Returns:
            str: The translated Serbian text in Cyrillic script
            
        Note:
            The function uses caching (@st.cache_data) to improve performance
            for repeated translations.
        """
        translation_system_prompt = """
        # Role: You are a professional English-to-Serbian public sector translation assistant

        # Instructions
        -   All translations must be outputed in the form of the Cyrillic alphabet

        """

        translation_task = f"""
        # Task: Accurately translate the input text content into Serbian, ensuring accuracy of terminology and clarity of expression

        # Input
        {text}

        # Requirements:
        - In-depth understanding of the terminology and descriptions in English public sector to ensure correct governance and public policy vocabulary is used in the Serbian translation.
        - Maintain the semantic integrity and accuracy of the original text to avoid omitting important information or introducing errors.
        - Pay attention to the differences in expression habits between English and Serbian, and make appropriate adjustments to make the Serbian translation more natural and fluent.
        - Only the translated content should be given, do not output other irrelevant content!
        - Follow "# Additional Translation Rules" and prioritize it over the above requirements **if and only if** there's a conflict. 
        - Preserve all Markdown formatting exactly as in the original text, including:
          * Bold text markers (**) must remain directly adjacent to the text they surround
          * No spaces should be added between formatting symbols and text
          * All links, lists, and other Markdown elements should maintain their exact format

        # Additional Translation Rules
        - Preserve all instances of "LDT" in English, 
        - No need to produce capital letters for each word in headings or titles, e.g "Мотор за Одлучивање" should be "Мотор за одлучивање."
        - All instances of "Decision Engine" or "decision engine" should be translated as **"алат за подршку одлучивању"**
        - All mentions of "region" or municipality" in the original English input text should be translated to **"општина"**
        - All monetary units (e.g USD, EUR, ...) should be kept in English.

        # Example 1：
        Original sentence: Veliko Gradište is a municipality in Serbia, positioned in the Braničevo District on the right bank of the Danube River, near the Romanian border.
        Translated: Велико Градиште је општина у Србији, која се налази у Браничевском округу на десној обали реке Дунав, близу границе са Румунијом.

        # Example 2:
        Original: **Access to school services (unit: %)**: Measures the percentage...
        Translated: **Приступ услугама у школи (јединица: %)**: Мери проценат...
        """

        messages = [
            {"role": "system", "content": translation_system_prompt},
            {"role": "user", "content": translation_task}
        ]

        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=messages,
            temperature=0.1,  # Even lower temperature for maximum consistency
            seed=42  # Fixed seed for deterministic translations
        )
        return response.choices[0].message.content

    
    #Global Variables for the OpenAI Calls
    client: OpenAI = OpenAI()

    SYSTEM_MESSAGE = """
    # Role
    You're a data scientist with domain expertise in local governance.

    # Instructions
    * Utilize data to help regional policy makers assess the environmental and economic performance of their regions using a set of pre-defined indicators.
    * Compare the performance of each indicator to its national average of the year in order to make logical conclusions. Some of the indicators are available at a multi-year basis.
    * The analysis must be as reasonable as possible. Avoid overly ambitious statements.

    # Context:
    This is what each indicator means:
    -   Accessibility to Health Services (unit: %): Measures the percentage of citizens with healthcare access within a 60-minute walking distance.
    -   Accessibility to School Services (unit: %): Measures the percentage of citizens with school access within a 60-minute walking distance.
    -   Diversity of Health Services: Evaluates healthcare service diversity within a municipality using the Shannon Diversity Index.
    -   CO2 Equivalent Emissions from all sources (unit: kgCO2e/kg): Quantifies total emissions, in terms of CO2, at the municipal level from all sources.
    -   Methane Emissions from all sources (kg): Quantifies total methane emissions at the municipal level from all sources.
    -   Emissions from Coal Power Plants (unit: kgCO2e/kg): Quantifies emissions from coal power plants specifically, aggregating data by emission type.
    -   Nighttime Luminosity (unit: nWatts/(cm2 x sr): Measures artificial nighttime light as an measurement of both the degree of electrification and economic development indicator using NASA's Black Marble data.
    -   Key Structure Average Broadband Download Speed (unit: megabites per second): Calculates the average broadband speed for key structures like schools and hospitals.
    -   Average Cellular Download Speed (unit: megabites per second): Measures average mobile download speeds across sub-national regions.
    -   Key Structures without Internet Access (unit: %): Shows the percentage of hospitals and schools lacking broadband internet access.
    -   Road flood risk per capita (unit: km per capita): Assesses road exposure to 1-in-100-year flood risks per capita for climate adaptation planning. 
    -   Road heatwave risk per capita (unit: km per capita): Measures road length at risk from heatwaves per capita in high-emission climate scenarios.
    -   Railway flood risk per capita (unit: km per capita): Assesses railway exposure to 1-in-100-year flood risks per capita.
    -   Railway heatwave risk per capita (unit: km per capita): Measures railway length at risk from heatwaves per capita in high-emission scenarios.
    -   Road flood risk (unit: km): Assesses road exposure to 1-in-100-year flood risks for climate adaptation planning. 
    -   Road heatwave risk (unit: km): Measures road length at risk from heatwaves in high-emission climate scenarios.
    -   Railway flood risk (unit: km): Assesses railway exposure to 1-in-100-year flood risks.
    -   Railway heatwave risk (unit: km): Measures railway length at risk from heatwaves in high-emission scenarios.
    -   PM 2.5 concentration (unit: µg/m3): Calculates average annual PM 2.5 concentration in sub-national regions, a key health risk factor.
    -   PM 10 concentration (unit: µg/m3): Calculates average annual PM 10 concentration in sub-national regions, a key health risk factor.
    -   NO2 concentration (unit: µg/m3): Calculates average annual NO2 concentration in sub-national regions, a key health risk factor.
    -   Agriculture Emissions (unit: kgCO2e/kg): Quantifies total emissions and emission factors at the municipal level from agriculture sources.
    -   Forestry & Land Use Emissions (unit: kgCO2e/kg): Quantifies total emissions and emission factors at the municipal level from forestry and land-use sources.
        
    Each indicator may fall under one or more of the following subcategories:
    -   Education: Concerns the degree of which the region's population has access to schools and how much access the region's schools has to internet infrastructure for a given year.
    -   Energy Access: Concerns how much the region has access to energy sources and electric power.
    -   Environment: May include areas such as air pollution and emissions
    -   Hospitals: Concerns the degree of which the region's population has access to hospitals and how much access the region's hospitals has to internet infrastructure for a given year.
    -   Digitalization: Concerns the development of the region's internet infrastructure, including both broadband and mobile internet. 
    -   Sustainable Transport: Concerns current development status and potential climate risks faced by of the region's existing land infrastructure such as railways and roads. 
        """

    category_options_en = ["Education", "Energy Access", "Environment", "Digitalization", "Health", "Sustainable Transport"]
    category_options_sr = ["Образовање", "Приступ енергији", "Животна средина", "Дигитализација", "Здравље", "Одрживи транспорт"]

    TOOLS = [{
        "type": "function",
        "function": {
            "name": "extract_relevant_data",
            "description": "Extract relevant columns from a particular dataset based on the region we are interested in and the columns relevant to the subcategory being analyzed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Region being analyzed and of which the data needs to be extracted"
                    },
                    "relevant_columns": {
                        "type": "array",
                        "description": "List of column titles that should be extracted from the dataset because they are relevant to the subcategory we are analyzing",
                        "items": { "type": "string" }  
                    }
                },
                "required": ["region"],  
                "additionalProperties": False
            }
        }
    }]



    if language == 'en':
        if "option_category" not in st.session_state:
            st.session_state.option_category = "Education"

        # Determine the index for "VelikoGradište" in the regions list
        region_index = regions.index("Veliko Gradište") if "Veliko Gradište" in regions else 0

        # Use selectbox to manage session state (Streamlit will handle option_region automatically)
        st.selectbox(
            "Select a Region:", 
            regions, 
            index=region_index,  # Uses computed index
            key="option_region"   # This prevents manual setting conflicts
        )
            # Category selectbox
        option_category = st.selectbox(
            "Select a category:",
            category_options_en,
            key="option_category",
            # index=category_options_en.index(st.session_state.option_category),
        )

        st.write("Region selected:", st.session_state.option_region)
        st.write("Category selected:", st.session_state.option_category)


    if language == 'sr':

        # Ensure session state keys exist for category, but NOT for region (to avoid conflict)
        if "option_category" not in st.session_state:
            st.session_state.option_category = "Образовање"

        # Determine the index for "VelikoGradište" in the regions list
        region_index = regions.index("Велико Градиште") if "Велико Градиште" in regions else 0

        # Use selectbox to manage session state (Streamlit will handle option_region automatically)
        st.selectbox(
            "Изаберите регион:", 
            regions, 
            index=region_index,  # Uses computed index
            key="option_region"   # This prevents manual setting conflicts
        )

        option_category = st.selectbox(
            "Изаберите категорију:",
            category_options_sr,
            key="option_category",
            # index=category_options_sr.index(st.session_state.option_category),
        )

        st.write("Изабран је регион:", st.session_state.option_region)
        st.write("Категорија је изабрана:", st.session_state.option_category)



    def df_indicatorlist_analysis(
        category_temp: str,
        df_temp: pd.DataFrame,
        region_temp: str,
        language: str = 'en'
    ) -> str:
        """
        Analyzes indicators for a specific category and region with response caching.

        Args:
            category_temp (str): Category to analyze
            df_temp (pd.DataFrame): DataFrame containing indicator metadata
            region_temp (str): Region being analyzed
            language (str, optional): Language code. Defaults to 'en'

        Returns:
            str: Formatted analysis text with relevant indicators
        """
        
        # NORMALIZE INPUTS TO ENGLISH FOR CONSISTENT ENGLISH RESPONSE GENERATION
        # Always use English names when generating English responses, regardless of current language mode
        english_category = cache_manager._normalize_category_name(category_temp)
        
        # Use normalized English names for all prompts to prevent Serbian names in English responses
        prompt_category = english_category
        
        # Check cache first
        cached_response = cache_manager.get_cached_response(
            region_temp, category_temp, 'indicators', language
        )
        
        if cached_response:
            # Add 2-second delay with status indicator for cached responses
            if language == 'en':
                flag = f"Starting analysis for {category_temp} in {region_temp}..."
            else:  # Serbian
                flag = f"Почиње анализа категорије {category_temp} у региону {region_temp}..."
                
            with st.status(flag, expanded=True) as status:
                time.sleep(sleep_t)  # 2-second delay
            
            # Return cached response content
            if isinstance(cached_response, dict):
                return cached_response['content']
            return cached_response

        # If Serbian is requested but no Serbian cache exists, check for English version for translation optimization
        if language == 'sr' and not cached_response:
            english_response = cache_manager.get_english_response(
                region_temp, category_temp, 'indicators'
            )
            if english_response:
                # Translate existing English response and cache the Serbian version
                flag = f"Преводим анализу за {category_temp} у региону {region_temp}..."
                with st.status(flag, expanded=True) as status:
                    translated_response = translate_en_to_sr(english_response)
                    # Cache the translated response for future Serbian requests
                    cache_manager.save_response(
                        region_temp, category_temp, 'indicators', 
                        translated_response, language
                    )
                    return translated_response

        # Generate new response if not in cache
        if language == 'en':
            flag = f"Starting analysis on {category_temp} in {region_temp}..."
            df_temp = df_temp[df_temp['SubCategory'].str.contains(category_temp, case=False, na=False)]
        elif language == 'sr':
            flag = f"Почиње анализа категорије {category_temp} у региону {region_temp}..."
            df_temp = df_temp[df_temp['SubCategory'].str.contains(category_options_en[category_options_sr.index(category_temp)], 
                                                                  case=False, na=False)]

        with st.status(flag, expanded=True) as status:
            json_columns = df_temp.to_json(orient='records')
            question_output = f"""
                # Task
                From the attached dataframe, outline the listed indicators.

                # Requirements:
                -   Mention the full name of the indicator from 'indicator_name_full' in **bold**, followed by ':' and its full description in regular text from 'indicator_descrption'.
                -   Ensure the indicators are logically relevant to the category based on the provided information.
                -   Outline the indicators in order of most relevant to {prompt_category}
                
                # Additional Context:
                This is the dataframe: {json_columns}"""
            
            messages = [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": question_output}
            ]

            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.3,
                seed=42
            )
            
            response_content = response.choices[0].message.content
            
            if language == 'en':
                # Cache the English response
                cache_manager.save_response(
                    region_temp, category_temp, 'indicators', 
                    response_content, language
                )
                return response_content
            elif language == 'sr':
                # For Serbian, first cache the English response, then translate
                cache_manager.save_response(
                    region_temp, category_temp, 'indicators', 
                    response_content, 'en'
                )
                translated_response = translate_en_to_sr(response_content)
                cache_manager.save_response(
                    region_temp, category_temp, 'indicators', 
                    translated_response, language
                )
                return translated_response

    def build_comparison_lines(
        regional_df: pd.DataFrame,
        national_df: pd.DataFrame,
        language: str = 'en'
    ) -> str:
        """
        Converts regional and national DataFrames into a formatted comparison string.

        Args:
            regional_df (pd.DataFrame): DataFrame containing regional data
            national_df (pd.DataFrame): DataFrame containing national averages
            language (str, optional): Language code. Defaults to 'en'

        Returns:
            str: Formatted string comparing regional and national values
        
        Example:
            **Indicator (unit)**
            2020: 12.3 Mbps – Veliko Gradište | 18.1 Mbps – National avg
            2021: ...
        """
        if language == 'en':
            col = "ENGLISH_NAME"
        elif language == 'sr':
            col = "SERBIAN_NAME_CYRILLIC"
        else:
            col = "ENGLISH_NAME"  # Default fallback

        lines = []

        for col in regional_df.columns.drop([col, "year"]):
            unit = ""  # ► fill if you store units in a lookup dict
            lines.append(f"**{col}{unit}**")
            for _, r_row in regional_df.iterrows():
                year = int(r_row["year"])
                region_val = r_row[col]
                nat_val   = national_df.loc[national_df["year"] == year, col].iloc[0]
                region_name = r_row[col]
                lines.append(
                    f"{year}: {region_val:.2f} – {region_name} | {nat_val:.2f} – National avg"
                )
            lines.append("")   # blank line between indicators
        return "\n".join(lines) 

    def regional_analysis(
        region_name: str,
        relevant_indicators: str,
        category_temp: str,
        language: str = 'en'
    ) -> str:
        """
        Performs detailed regional analysis using a two-step RAG pipeline with response caching.

        Args:
            region_name (str): Name of the region to analyze
            relevant_indicators (str): Text containing relevant indicators
            category_temp (str): Category being analyzed
            language (str, optional): Language code. Defaults to 'en'

        Returns:
            str: Comprehensive regional analysis text
        """
        
        # NORMALIZE INPUTS TO ENGLISH FOR CONSISTENT ENGLISH RESPONSE GENERATION
        # Always use English names when generating English responses, regardless of current language mode
        english_region = cache_manager._normalize_region_name(region_name)
        english_category = cache_manager._normalize_category_name(category_temp)
        
        # Use normalized English names for all prompts to prevent Serbian names in English responses
        prompt_region = english_region
        prompt_category = english_category
        
        # Check cache first
        cached_response = cache_manager.get_cached_response(
            region_name, category_temp, 'regional', language
        )
        
        if cached_response:
            # Add 2-second delay with status indicator for cached responses
            if language == 'en':
                flag = f"Conducting regional analysis..."
            else:  # Serbian
                flag = f"Извођење регионалне анализе..."
                
            with st.status(flag, expanded=True) as status:
                time.sleep(sleep_t)  # 2-second delay

            if isinstance(cached_response, dict):
                return cached_response['content']
            return cached_response

        # If Serbian is requested but no Serbian cache exists, check for English version for translation optimization
        if language == 'sr' and not cached_response:
            english_response = cache_manager.get_english_response(
                region_name, category_temp, 'regional'
            )
            if english_response:
                # Translate existing English response and cache the Serbian version
                flag = f"Преводим регионалну анализу за {category_temp} у региону {region_name}..."
                with st.status(flag, expanded=True) as status:
                    translated_response = translate_en_to_sr(english_response)
                    # Cache the translated response for future Serbian requests
                    cache_manager.save_response(
                        region_name, category_temp, 'regional', 
                        translated_response, language
                    )
                    return translated_response
        
        # Generate new response if not in cache
        if language == 'en':
            flag = "Conducting regional analysis..."
        elif language == 'sr':
            flag = "Извођење регионалне анализе..."

        with st.status(flag, expanded=True) as status:

            # ---------- 1. GPT *extraction* call ----------
            json_columns = df_indicators.columns[4:].tolist()

            extract_prompt = f"""
            # Task
            From the text below, return JSON with keys:
            • region          (string, should equal "{prompt_region}")
            • relevant_columns (array of dataset column titles)

            # Additional Context
            The following is text that lists indicators
            {relevant_indicators}

            And the following are the dataset column titles
            {json_columns}

            Return *only* the JSON, no prose."""
            
            messages = [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user",   "content": extract_prompt}
            ]
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=1
            )

            # print(response.choices[0].message)
            raw_content = response.choices[0].message.content
            json_str = re.sub(r"```json\s*|```", "", raw_content).strip()
            cols_parsed = json.loads(json_str)
            cols = cols_parsed.get("relevant_columns", [])
            if language == 'en':
                cols.extend(['ENGLISH_NAME', 'year'])
            if language == 'sr':
                cols.extend(["SERBIAN_NAME_CYRILLIC", 'year'])


            # ---------- 2.  deterministic numeric step ----------
            regional_df = extract_regional_data(df_indicators, region_name, cols, language)
            national_df = extract_national_data(averages_df.reset_index(), cols)
            comp_lines  = build_comparison_lines(regional_df, national_df, language)

            # ---------- 3. GPT *narrative* call ----------
            narrative_prompt = f"""
            # Data for {prompt_region}
            {comp_lines}

            # Task
            1. Number and print each indicator's name as a **mini-header (bold)** (e.g., "1. Indicator Name").
            2. Print the indicator metrics using this format `YYYY: Regional Indicator Performance + Unit - Region Name | National Performance + Unit - National Average`
            3. After each indicator's bullet list, add a short **Interpretation** section in regular text format (not as a header).
            4. Finish with an **Overall Summary** as a small header using # markdown syntax (≤ 150 words) for a non-technical policymaker.

            # Requirements
            -   Write for someone in government, who is in charge of **policy or decision-making**, who may not be familiar with these indicators.
            -   For each **interpretation** Explain why this is important regarding the {prompt_region} region and {prompt_category} subcategory
            -   Keep the explanations clear, informative, and concise.
            -   The outputs must strictly follow what is set in the following **# Example** with no deviations.

            # Example
            **1. Key Structure Average Broadband Download Speed **\n
            2021: 33.67 megabits per second - Bor | 37.79 megabits per second - National Average\n2022: 26.43 megabits per second - Bor | 42.19 megabits per second - National Average\n2023: 43.90 megabits per second - Bor | 54.94 megabits per second - National Average\n2024: 44.63 megabits per second - Bor | 65.87 megabits per second - National Average\n\n
            *Interpretation*\n
            Bor's broadband speeds for key structures ...

            **2. Average Cellular Download Speed **\n
            2021: 33.67 megabits per second - Bor | 37.79 megabits per second - National Average\n2022: 26.43 megabits per second - Bor | 42.19 megabits per second - National Average\n2023: 43.90 megabits per second - Bor | 54.94 megabits per second - National Average\n2024: 44.63 megabits per second - Bor | 65.87 megabits per second - National Average\n\n
            *Interpretation:*\n
            Bor shows an improving trend in cellular download speeds ...
            
            ### Overall Summary
            Bor demonstrates notable advancements in terms of digitalization over recent years ...
            """
            
            messages = [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user",   "content": narrative_prompt}
            ]
            narrative_response = client.chat.completions.create(
                model="gpt-4.1",
                messages=messages,
                temperature=0
            )

            response_content = narrative_response.choices[0].message.content
            
            if language == 'en':
                # Cache the English response
                cache_manager.save_response(
                    region_name, category_temp, 'regional', 
                    response_content, language
                )
                return response_content
            elif language == 'sr':
                # For Serbian, first cache the English response, then translate
                cache_manager.save_response(
                    region_name, category_temp, 'regional', 
                    response_content, 'en'
                )
                translated_response = translate_en_to_sr(response_content)
                cache_manager.save_response(
                    region_name, category_temp, 'regional', 
                    translated_response, language
                )
                return translated_response

    def project_recommendation_agent(
        region_temp: str,
        subcategory: str,
        regional_analysis: str,
        language: str = 'en'
    ) -> Tuple[str, str]:
        """
        Generates project recommendations based on regional analysis with response caching.

        Args:
            region_temp (str): Region to generate recommendations for
            subcategory (str): Category/subcategory focus area
            regional_analysis (str): Text of the regional analysis
            language (str, optional): Language code. Defaults to 'en'

        Returns:
            Tuple[str, str]: Tuple containing:
                - Initial recommendations text
                - Final project selections text
        """
        
        # NORMALIZE INPUTS TO ENGLISH FOR CONSISTENT ENGLISH RESPONSE GENERATION
        # Always use English names when generating English responses, regardless of current language mode
        english_region = cache_manager._normalize_region_name(region_temp)
        english_subcategory = cache_manager._normalize_category_name(subcategory)
        
        # Use normalized English names for all prompts to prevent Serbian names in English responses
        prompt_region = english_region
        prompt_subcategory = english_subcategory

        # Check cache for project recommendations
        cached_projects = cache_manager.get_cached_response(
            region_temp, subcategory, 'projects', language
        )
        
        if cached_projects:
            # Add 2-second delay with status indicator for cached responses
            if language == 'en':
                flag = f"Doing some background research on {region_temp}... This may take a moment."
            else:  # Serbian
                flag = f"Проводим нека истраживања о {region_temp}... Ово може потрајати неколико тренутака."
                
            with st.status(flag, expanded=True) as status:
                time.sleep(sleep_t)  # 2-second delay

            # Display cached project recommendations
            if isinstance(cached_projects, dict):
                cached_content = cached_projects['content']
            else:
                cached_content = cached_projects
            
            # Split cached content into research, initial recommendations, and final projects
            if "|||INITIAL_RECOMMENDATIONS|||" in cached_content and "|||FINAL_PROJECTS|||" in cached_content:
                # New 3-part format: research|||INITIAL_RECOMMENDATIONS|||initial|||FINAL_PROJECTS|||final
                parts = cached_content.split("|||INITIAL_RECOMMENDATIONS|||")
                if len(parts) == 2:
                    research_content = parts[0].strip()
                    remaining = parts[1].split("|||FINAL_PROJECTS|||")
                    if len(remaining) == 2:
                        initial_recommendations = remaining[0].strip()
                        final_project_selection = remaining[1].strip()
                    else:
                        initial_recommendations = remaining[0].strip()
                        final_project_selection = remaining[0].strip()
                else:
                    # Fallback
                    research_content = ""
                    initial_recommendations = cached_content
                    final_project_selection = cached_content
            elif "|||FINAL_PROJECTS|||" in cached_content:
                # Old 2-part format: initial|||FINAL_PROJECTS|||final
                research_content = ""
                parts = cached_content.split("|||FINAL_PROJECTS|||")
                if len(parts) == 2:
                    initial_recommendations = parts[0].strip()
                    final_project_selection = parts[1].strip()
                else:
                    initial_recommendations = cached_content
                    final_project_selection = cached_content
            else:
                # No delimiters found
                research_content = ""
                initial_recommendations = cached_content
                final_project_selection = cached_content
            
            # Display cached research and project recommendations
            if research_content:
                if language == 'en':
                    st.subheader("Background Research")
                    st.write(research_content)
                else:
                    st.subheader("Истраживање позадине")
                    st.write(research_content)
            
            # Display Initial Project Recommendations with delay
            if language == 'en':
                flag = f"Generating project recommendations... This may take a moment."
            else:
                flag = f"Генерисање препорука пројеката... Ово може потрајати неколико тренутака."
            
            with st.status(flag, expanded=True) as status:
                time.sleep(sleep_t)  # 2-second delay
            
            if language == 'en':
                st.subheader("Initial Project Recommendations")
                st.write(initial_recommendations)
            else:
                st.subheader("Прве препоруке за пројекте")
                st.write(initial_recommendations)
            
            # Display Final Project Selections with delay
            if language == 'en':
                flag = f"Finalizing project selections..."
            else:
                flag = f"Финализовање избора пројеката..."
            
            with st.status(flag, expanded=True) as status:
                time.sleep(sleep_t)  # 2-second delay
            
            if language == 'en':
                st.subheader("Final Project Selections")
                st.write(final_project_selection)
            else:
                st.subheader("Коначни избор пројеката")
                st.write(final_project_selection)
            
            return initial_recommendations, final_project_selection

        # If Serbian is requested but no Serbian cache exists, check for English version for translation optimization
        if language == 'sr' and not cached_projects:
            english_projects = cache_manager.get_english_response(
                region_temp, subcategory, 'projects'
            )
            if english_projects:
                # First, split the English content into components before translation
                if "|||INITIAL_RECOMMENDATIONS|||" in english_projects and "|||FINAL_PROJECTS|||" in english_projects:
                    # New 3-part format: research|||INITIAL_RECOMMENDATIONS|||initial|||FINAL_PROJECTS|||final
                    parts = english_projects.split("|||INITIAL_RECOMMENDATIONS|||")
                    if len(parts) == 2:
                        english_research = parts[0].strip()
                        remaining = parts[1].split("|||FINAL_PROJECTS|||")
                        if len(remaining) == 2:
                            english_initial = remaining[0].strip()
                            english_final = remaining[1].strip()
                        else:
                            english_initial = remaining[0].strip()
                            english_final = remaining[0].strip()
                    else:
                        english_research = ""
                        english_initial = english_projects
                        english_final = english_projects
                elif "|||FINAL_PROJECTS|||" in english_projects:
                    # Old 2-part format: initial|||FINAL_PROJECTS|||final
                    english_research = ""
                    parts = english_projects.split("|||FINAL_PROJECTS|||")
                    if len(parts) == 2:
                        english_initial = parts[0].strip()
                        english_final = parts[1].strip()
                    else:
                        english_initial = english_projects
                        english_final = english_projects
                else:
                    # No delimiters found
                    english_research = ""
                    english_initial = english_projects
                    english_final = english_projects
                
                # Now translate and display each component sequentially
                flag = f"Преводим препоруке пројеката за {subcategory} у региону {region_temp}..."
                with st.status(flag, expanded=True) as status:
                    # Translate and display research content if it exists
                    research_content = ""
                    if english_research:
                        st.write("Преводим истраживање позадине...")
                        research_content = translate_en_to_sr(english_research)
                        st.subheader("Истраживање позадине")
                        st.write(research_content)
                    
                    # Translate and display initial recommendations
                    st.write("Преводим прве препоруке за пројекте...")
                    initial_recommendations = translate_en_to_sr(english_initial)
                    st.subheader("Прве препоруке за пројекте")
                    st.write(initial_recommendations)
                    
                    # Translate and display final project selection
                    st.write("Преводим коначни избор пројеката...")
                    final_project_selection = translate_en_to_sr(english_final)
                    st.subheader("Коначни избор пројеката")
                    st.write(final_project_selection)
                    
                    # Reconstruct the full translated response for caching
                    if research_content:
                        translated_projects = f"{research_content}|||INITIAL_RECOMMENDATIONS|||{initial_recommendations}|||FINAL_PROJECTS|||{final_project_selection}"
                    else:
                        translated_projects = f"{initial_recommendations}|||FINAL_PROJECTS|||{final_project_selection}"
                    
                    # Cache the translated response for future Serbian requests
                    cache_manager.save_response(
                        region_temp, subcategory, 'projects', 
                        translated_projects, language
                    )
                    
                    return initial_recommendations, final_project_selection

        # CONSISTENT API PARAMETERS FOR ALL CALLS
        RESEARCH_TEMPERATURE = 0.1
        RECOMMENDATION_TEMPERATURE = 0.1
        FINAL_SELECTION_TEMPERATURE = 0.1
        RANDOM_SEED = 42

        # SYSTEM MESSAGE
        research_system_message = """
            # Role
            You are a policy researcher and data scientist specializing in countries located in the Western Balkans. 
            
            # Instructions
            -   You will output only relevant responses 
            -   You will only search for and retain facts
            -   Provide accurate sources (if available) for your information"""

        # FIRST AGENT - General Regional Summary
        task_research = f"""
            # Task
            -   Provide a summary regarding the {prompt_region} municipality of Serbia when it comes to {prompt_subcategory}, focusing on its assets, weaknesses, and most relevant challenges.
            -   Also look for basic information regarding the municipality such as its location, population, etc..,
            
            
            # Requirements
            - Summarize the results in ≤ 150 words.
            - Focus on factual, data-driven insights
            - Maintain consistent structure and terminology
            """

        # Generate and display background research before project recommendations
        if language == 'en':
            st.subheader("Background Research")
            status_temp = f"Doing some background research on {region_temp}... This may take a moment."
        else:
            st.subheader("Истраживање позадине")
            status_temp = f"Проводим нека истраживања о {region_temp}... Ово може потрајати неколико тренутака."
        
        with st.status(status_temp, expanded=True) as status:
            research_messages = [{"role": "system", "content": research_system_message}, 
                                {"role": "user", "content": task_research}]

            research_response = client.chat.completions.create(
                model="gpt-4.1", 
                messages=research_messages, 
                temperature=RESEARCH_TEMPERATURE, 
                seed=RANDOM_SEED,
                max_tokens=200
            )
            regional_summary = research_response.choices[0].message.content
        
        # Display background research
        if language == 'en':
            st.write(regional_summary)
        else:
            translated_research = translate_en_to_sr(regional_summary)
            st.write(translated_research)

        # SECOND AGENT - Project Recommendations
        project_system_message = f"""
            # Role 
            You are a governance specialist with deep expertise in both national and sub-national public policy for countries located in the Western Balkans.

            # Instructions 
            -   Your task is to generate project recommendations for the {prompt_region} municipality in terms of {prompt_subcategory}. 
            -   However, these recommendations must be **strictly based on** 
                    - the regional analysis 
                    - regional summary 
                    - when applicable: Potentially Viable Projects
            
            # Context 
            **# Regional Summary (Only for Refinement, Not Idea Generation):**\n
            The following background information about the region should only be used to refine or adjust the recommendations 
            from the dataset. It should **not** be used to create recommendations that are not supported by the dataset.\n
            {regional_summary}\n\n
            """

        project_task = f"""
            # Task
            -   Generate exactly 5 project recommendations that directly address the specific challenges and opportunities identified in the **Regional Analysis**
            -   Rank projects by implementation feasibility (most feasible first)
            -   Each recommendation must cite specific data points or findings from the Regional Analysis where applicable
            -   Provide exactly 3 concrete policy actions for each project

            # Ranking Criteria (in order of priority)
            1. Addresses critical gaps identified in the regional data
            2. Builds on existing regional strengths/assets  
            3. Feasible given typical municipal budgets and capabilities
            4. Aligns with {prompt_subcategory} sector priorities
            5. Has measurable impact potential

            # Requirements
            -   Policy recommendations must be actionable at the municipal level
            -   Focus on projects that can realistically be implemented within 3-5 years
            -   Prioritize projects that leverage existing infrastructure or capabilities
            -   Follow the exact format specified below without deviation
            -   Maintain consistent terminology and structure

            # Format (Follow Exactly)
            Based on the regional analysis data for {prompt_region}, here are the 5 most viable public investment projects ranked by implementation feasibility:
            
            **1. [Specific Project Name]**
            \n*Project Description:* [50-75 words describing the project scope and components]
            \n*Data-Based Justification:* [Reference specific indicators/findings from Regional Analysis that support this project - 75-100 words]
            \n*Implementation Actions:*
                1. [Specific municipal-level action]
                2. [Specific policy or regulatory action]
                3. [Specific partnership or funding action]

            **2. [Specific Project Name]**
            [Same format as above]

            **3. [Specific Project Name]**
            [Same format as above]

            **4. [Specific Project Name]**
            [Same format as above]

            **5. [Specific Project Name]**
            [Same format as above]

            # Additional Context
            **Regional Analysis Data:**
            {regional_analysis}
            """

        project_messages = [{"role": "system", "content": project_system_message},
                                {"role": "user", "content": project_task}]

        
            

        # Generate initial recommendations first
        if language == 'en':
            st.subheader("Initial Project Recommendations")
            status_message = "Generating project recommendations... This may take a moment."
        else:
            st.subheader("Прве препоруке за пројекте")
            status_message = "Генерисање препорука пројеката... Ово може потрајати неколико тренутака."

        # SHOW INTERMEDIATE RESPONSE (Processing Message)
        with st.status(status_message, expanded=True) as status:
            initial_response = client.chat.completions.create(model="gpt-4.1", messages=project_messages, temperature=RECOMMENDATION_TEMPERATURE, seed=42)
            initial_recommendations = initial_response.choices[0].message.content

            # FILTER RELEVANT PROJECTS (using English category names for consistency)
            df_projects_temp = df_projects[df_projects['Investment Sector'].str.contains(prompt_subcategory, case=False, na=False)]
            if prompt_subcategory == 'Environment':
                df_projects_temp = df_projects_temp[df_projects_temp['Project Description'].str.contains("air | air pollution | emissions | co2 | CO2", na=False)]
            
            if prompt_subcategory == 'Sustainable Transport':
                df_projects_temp = df_projects_temp[df_projects_temp['Status'] != 'Preparation']

            json_projects = df_projects_temp.to_json(orient="records")
            
        # DISPLAY INITIAL RESPONSE
        if language == 'en':
            st.write(initial_recommendations)
        else:
            st.write(translate_en_to_sr(initial_recommendations))

        relevant_projects_q = f"""
        # Task
        -   Select the most relevant projects from the provided dataset based on project description, fit, and title alignment with the recommendations
        -   Present exactly 5 projects with complete information including project description, location, expected beneficiaries, lead IFI, cost, and URL

        # Requirements
        -   Projects should be selected based on relevance to {prompt_subcategory} and alignment with the **# Additional Context** recommendations
        -   The chosen projects serve as examples for policy makers to learn from
        -   If projects are not thematically relevant to the recommendations, select projects from the same industry/theme
        -   Always output exactly 5 projects unless fewer than 5 relevant projects exist
        -   For Lead IFI, always use full institution name and abbreviation in parentheses. Refer to "# Disambiguation"
        -   Follow the exact format structure without deviation
        -   Maintain consistent terminology and project numbering

        # Format (Follow Exactly)
        Here are the projects that align closely with the recommendations for {prompt_region}, focusing particularly on {prompt_subcategory}:
    
        1. **[Project Title]**
            - *Project Description:* [approximately 50 words]
            - *Location:* [specific location]
            - *Beneficiaries:* [target beneficiaries]
            - *Lead IFI:* [Full Institution Name (ABBREVIATION)]
            - *Sector:* {prompt_subcategory}
            - *Type:* [project type]
            - *Total Financing:* [amount]
            - *Project Benefits:* [key benefits]
            - *URL:* [project URL (example: https://www.wbif.eu/project-detail/PRJ-ALB-DII...)]

        2. **[Project Title]**
            [Same format as above]

        3. **[Project Title]**
            [Same format as above]

        4. **[Project Title]**
            [Same format as above]

        5. **[Project Title]**
            [Same format as above]

        # Additional Context
        The project recommendations for reference are: {initial_recommendations}
        
        # Available Projects Dataset
        {str(json_projects)}
        
        # Disambiguation
        - AFD: French Development Agency (AFD)
        - KfW: KfW Bankengruppe (KfW)
        - EIF: European Investment Fund (EIF)
        - CEB: Council of Europe Development Bank (CEB)
        - EIB: European Investment Bank (EIB)
        - EBRD: European Bank of Reconstruction and Development (EBRD)
        - IFC: International Finance Corporation (IFC)
        """
        
        final_project_messages = [{"role": "system", "content": project_system_message},
                                  {"role": "user", "content": relevant_projects_q}]
        
        

        if language == 'en':
            # DISPLAY FINAL OUTPUT
            st.subheader("Final Project Selections")
            with st.status("Matching with similar projects within the region... This may take a moment.", expanded=True) as status:
                
                final_response = client.chat.completions.create(
                    model="gpt-4.1", 
                    messages=final_project_messages, 
                    temperature=FINAL_SELECTION_TEMPERATURE, 
                    seed=RANDOM_SEED
                )
                final_project_selection = final_response.choices[0].message.content

                # Cache the combined results for English with research
                combined_content = f"{regional_summary}|||INITIAL_RECOMMENDATIONS|||{initial_recommendations}|||FINAL_PROJECTS|||{final_project_selection}"
                cache_manager.save_response(
                    region_temp, subcategory, 'projects', 
                    combined_content, language
                )

            st.write(final_project_selection)

            # UPDATE STATUS
            status.update(label="Process Completed!", state="complete")

        elif language == 'sr':
            st.subheader("Коначни избор пројеката")

            with st.status("Усклађивање са сличним пројектима у региону... Ово може потрајати неколико тренутака.", expanded=True) as status:
                # For Serbian, first cache the English version, then translate and cache Serbian
                final_response = client.chat.completions.create(
                    model="gpt-4.1", 
                    messages=final_project_messages, 
                    temperature=FINAL_SELECTION_TEMPERATURE, 
                    seed=RANDOM_SEED
                )
                final_project_selection = final_response.choices[0].message.content
                
                combined_english_content = f"{regional_summary}|||INITIAL_RECOMMENDATIONS|||{initial_recommendations}|||FINAL_PROJECTS|||{final_project_selection}"
                cache_manager.save_response(
                    region_temp, subcategory, 'projects', 
                    combined_english_content, 'en'
                )
                
                # Translate and display Serbian version
                translated_initial = translate_en_to_sr(initial_recommendations)
                translated_final = translate_en_to_sr(final_project_selection)
            
            # DISPLAY FINAL OUTPUT
            
            st.write(translated_final)
            
            # Cache the Serbian version (research was already translated and displayed earlier)
            combined_serbian_content = f"{translated_research}|||INITIAL_RECOMMENDATIONS|||{translated_initial}|||FINAL_PROJECTS|||{translated_final}"
            cache_manager.save_response(
                region_temp, subcategory, 'projects', 
                combined_serbian_content, language
            )

            # UPDATE STATUS
            status.update(label="Process Completed!", state="complete")
            
            # Return translated versions for Serbian
            return translated_initial, translated_final

        return initial_recommendations, final_project_selection

    ## Running Analysis ##

    # Initialize session state flags if they don't exist
    if 'analysis_completed' not in st.session_state:
        st.session_state.analysis_completed = False
    if 'regional_analysis_completed' not in st.session_state:
        st.session_state.regional_analysis_completed = False
    if 'project_recommendations_completed' not in st.session_state:
        st.session_state.project_recommendations_completed = False
    if 'start_analysis' not in st.session_state:
        st.session_state.start_analysis = False  # Ensure session state variable exists

    # Initialize 'messages' key in session state if not already initialized
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []
    
    if language == 'en':
        if st.button("Let's get started"):
            st.session_state.start_analysis = True  # Set flag when button is clicked
    else:
        if st.button("Хајде да почнемо"):
            st.session_state.start_analysis = True  # Set flag when button is clicked

    if st.session_state.start_analysis and not st.session_state.analysis_completed:
        relevant_indicators = df_indicatorlist_analysis(st.session_state.option_category, df_indicatorlist, st.session_state.option_region, language=language) 
        st.session_state.relevant_indicators = relevant_indicators
        st.session_state.analysis_completed = True  # Mark analysis as complete

    # Display the initial analysis result if it exists in session state
    if st.session_state.get("relevant_indicators"):
        # Always show the subheader when displaying results
        if language == 'en':
            st.subheader("Relevant Indicators")
        else:
            st.subheader("Релевантни индикатори")
        st.write(st.session_state.relevant_indicators)


    # Second button only appears after the first analysis is complete
    if st.session_state.analysis_completed:

        if language == 'en':
            if st.button("Let's conduct a Regional Analysis") and not st.session_state.regional_analysis_completed:
                regional_analysis_results = regional_analysis(st.session_state.option_region, st.session_state.relevant_indicators, st.session_state.option_category, language=language)
                st.session_state.regional_analysis_results = regional_analysis_results
                st.session_state.regional_analysis_completed = True
        else:
            if st.button("Хајде да урадимо регионалну анализу") and not st.session_state.regional_analysis_completed:
                regional_analysis_results = regional_analysis(st.session_state.option_region, st.session_state.relevant_indicators, st.session_state.option_category, language=language)
                st.session_state.regional_analysis_results = regional_analysis_results
                st.session_state.regional_analysis_completed = True
        
        

    # Display regional analysis if it exists
    if st.session_state.get("regional_analysis_results"):
        # Always show the subheader when displaying results
        if language == 'en':
            st.subheader("Comprehensive Regional Analysis")
        else:
            st.subheader("Свеобухватна регионална анализа")
        st.write(st.session_state.regional_analysis_results)


    if st.session_state.regional_analysis_completed == True:
        # Ensure function only runs once
        if language == 'en':
            flag = "What Project Recommendations Follow?"
        elif language == 'sr':
            flag = "Које препоруке за пројекте следе?"
        else:
            flag = "What Project Recommendations Follow?"  # Default fallback

        if st.button(flag) and not st.session_state.project_recommendations_completed:
            project_recommendations = project_recommendation_agent(st.session_state.option_region, st.session_state.option_category, st.session_state.regional_analysis_results, language=language)
            st.session_state.project_recommendations_completed = True
            st.session_state.project_recommendations = project_recommendations

    if st.session_state.get("project_recommendations"):
        if language == 'en':
            if st.button("New Analysis"):
                # Clear only analysis-specific session state
                analysis_keys = [
                    'analysis_completed', 'regional_analysis_completed', 
                    'project_recommendations_completed', 'start_analysis',
                    'relevant_indicators', 'regional_analysis_results', 
                    'project_recommendations', 'messages'
                ]
                for key in analysis_keys:
                    if key in st.session_state:
                        del st.session_state[key]

                # Rerun the app without modifying language state
                st.rerun()

        else:
            if st.button("Нова анализа"):
                # Clear only analysis-specific session state
                analysis_keys = [
                    'analysis_completed', 'regional_analysis_completed', 
                    'project_recommendations_completed', 'start_analysis',
                    'relevant_indicators', 'regional_analysis_results', 
                    'project_recommendations', 'messages'
                ]
                for key in analysis_keys:
                    if key in st.session_state:
                        del st.session_state[key]

                # Rerun the app without modifying language state
                st.rerun()