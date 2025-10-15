import json
import time

import streamlit as st
from openai import OpenAI
from google.oauth2 import service_account
from google.cloud import storage

# Local imports
from src.config import (
    BUCKET_NAME, CACHE_PATH, UI_TEXT, CATEGORY_OPTIONS_EN,
    CATEGORY_OPTIONS_SR, SLEEP_TIME
)
from src.gcs import read_csv_from_gcs, get_image_from_gcs
from src.caching import ResponseCacheManager
from src.ui import render_sidebar, render_language_selection, render_main_interface
from src.analysis import (
    get_indicator_analysis, prepare_regional_analysis_data, filter_projects
)
from src.llm import (
    translate_en_to_sr, get_regional_narrative, get_background_research,
    get_initial_recommendations, get_final_projects
)

# --- App Configuration ---
st.set_page_config(
    page_title="LDT Decision Engine",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- State Management ---
if 'stage' not in st.session_state:
    st.session_state.stage = 0 # 0: Start, 1: Indicators, 2: Regional, 3: Projects done

# --- Initialization ---
@st.cache_resource
def init_gcs_client():
    """Initialize Google Cloud Storage client using credentials from Streamlit secrets."""
    creds_dict = {
        "type": "service_account",
        "project_id": st.secrets["gcs"]["project_id"],
        "private_key_id": st.secrets["gcs"]["private_key_id"],
        "private_key": st.secrets["gcs"]["private_key"], 
        "client_email": st.secrets["gcs"]["client_email"],
        "client_id": st.secrets["gcs"]["client_id"],
        "auth_uri": st.secrets["gcs"]["auth_uri"],
        "token_uri": st.secrets["gcs"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcs"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcs"]["client_x509_cert_url"],
        "universe_domain": "googleapis.com"
    }
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    return storage.Client(credentials=credentials)

@st.cache_resource
def init_openai_client():
    """Initialize OpenAI client using API key from Streamlit secrets."""
    return OpenAI(api_key=st.secrets["openai_apikey"])

storage_client = init_gcs_client()
openai_client = init_openai_client()

# --- Data Loading ---
@st.cache_data
def load_data(_storage_client):
    """Load all necessary data from GCS."""
    df_indicatorlist = read_csv_from_gcs(
        _storage_client, BUCKET_NAME, "decision_engine/inputs/Indicator List v2.csv",
        delimiter=",", encoding="cp1252", on_bad_lines="warn"
    )
    df_indicators = read_csv_from_gcs(
        _storage_client, BUCKET_NAME, "decision_engine/inputs/SRB Absolute Full_v4.csv"
    )
    df_projects = read_csv_from_gcs(
        _storage_client, BUCKET_NAME, "decision_engine/inputs/wbif_project_examples_v2.csv", sep=";"
    )
    df_projects = df_projects.drop(
        ["Estimated Completion", "Beneficiary Body", "Total Grant", "Total Loan"], axis=1
    )
    
    regions_en = df_indicators["ENGLISH_NAME"].unique().tolist()
    regions_sr = df_indicators["SERBIAN_NAME_CYRILLIC"].unique().tolist()
    
    averages_df = df_indicators.groupby("year")[df_indicators.columns[4:]].mean().reset_index()
    
    return df_indicatorlist, df_indicators, df_projects, regions_en, regions_sr, averages_df

df_indicatorlist, df_indicators, df_projects, regions_en, regions_sr, averages_df = load_data(storage_client)

# --- UI Rendering ---
cache_manager = ResponseCacheManager(storage_client, BUCKET_NAME, CACHE_PATH, df_indicators)
pimpam_logo = get_image_from_gcs(storage_client, BUCKET_NAME, "decision_engine/inputs/wbg-pimpam.png")
gpbp_logo = get_image_from_gcs(storage_client, BUCKET_NAME, "decision_engine/inputs/GPBP logo.jpg")

render_sidebar(pimpam_logo, gpbp_logo, cache_manager)
lang_code = render_language_selection()

regions = regions_sr if lang_code == "sr" else regions_en
categories = CATEGORY_OPTIONS_SR if lang_code == "sr" else CATEGORY_OPTIONS_EN
ui_text = UI_TEXT[lang_code]

render_main_interface(lang_code, regions, categories)

# --- Main App Logic ---

# --- Stage 0 -> 1: Indicator Analysis ---
if st.session_state.stage == 0:
    if st.button(ui_text['start_button'], use_container_width=True):
        en_category = cache_manager._normalize_category_name(st.session_state.option_category)
        
        # Indicator analysis is deterministic text, no LLM, so no caching needed here.
        indicator_response_en, code_list, code_name_dict = get_indicator_analysis(df_indicatorlist, en_category)
        
        # Store results in session state
        st.session_state.indicator_response_en = indicator_response_en
        st.session_state.code_list = code_list
        st.session_state.code_name_dict = code_name_dict
        
        st.session_state.stage = 1
        st.rerun()

# --- Display Indicator Analysis & Trigger for Stage 2 ---
if st.session_state.stage >= 1:
    st.header(ui_text['relevant_indicators_header'])
    
    indicator_response_en = st.session_state.indicator_response_en
    
    # Handle translation and caching of translation
    if lang_code == 'sr':
        cached_sr = cache_manager.get_cached_response(st.session_state.option_region, st.session_state.option_category, 'indicators', 'sr')
        if cached_sr:
            indicator_response = cached_sr['content']
        else:
            with st.spinner("Translating..."):
                indicator_response = translate_en_to_sr(openai_client, indicator_response_en)
                cache_manager.save_response(st.session_state.option_region, st.session_state.option_category, 'indicators', indicator_response, 'sr')
    else:
        indicator_response = indicator_response_en
        
    st.markdown(indicator_response)

    if st.session_state.stage == 1:
        if st.button(ui_text['regional_analysis_button'], use_container_width=True):
            region = st.session_state.option_region
            category = st.session_state.option_category
            en_category = cache_manager._normalize_category_name(category)
            en_region = cache_manager._normalize_region_name(region)

            with st.spinner(ui_text['status_conducting_regional']):
                # Check cache for English version first
                cached_en = cache_manager.get_cached_response(region, category, 'regional', 'en')
                if cached_en:
                    regional_analysis_en = cached_en['content']
                else:
                    # Generate and save to cache if not found
                    comparison_text = prepare_regional_analysis_data(df_indicators, averages_df, en_region, st.session_state.code_list, st.session_state.code_name_dict)
                    regional_analysis_en = get_regional_narrative(openai_client, en_region, en_category, comparison_text)
                    cache_manager.save_response(region, category, 'regional', regional_analysis_en, 'en')
                
                st.session_state.regional_analysis_en = regional_analysis_en
            
            st.session_state.stage = 2
            st.rerun()

# --- Display Regional Analysis & Trigger for Stage 3 ---
if st.session_state.stage >= 2:
    st.header(ui_text['regional_analysis_header'])
    
    regional_analysis_en = st.session_state.regional_analysis_en
    
    # Handle translation and caching of translation
    if lang_code == 'sr':
        cached_sr = cache_manager.get_cached_response(st.session_state.option_region, st.session_state.option_category, 'regional', 'sr')
        if cached_sr:
            regional_analysis = cached_sr['content']
        else:
            with st.spinner("Translating..."):
                regional_analysis = translate_en_to_sr(openai_client, regional_analysis_en)
                cache_manager.save_response(st.session_state.option_region, st.session_state.option_category, 'regional', regional_analysis, 'sr')
    else:
        regional_analysis = regional_analysis_en

    st.markdown(regional_analysis)

    if st.session_state.stage == 2:
        if st.button(ui_text['project_recommendations_button'], use_container_width=True):
            st.session_state.stage = 3 # Mark stage as "in progress" to hide the button on rerun
            
            region = st.session_state.option_region
            category = st.session_state.option_category
            en_category = cache_manager._normalize_category_name(category)
            en_region = cache_manager._normalize_region_name(region)
            
            # --- Run and Display Background Research ---
            st.header(ui_text['background_research_header'])
            with st.spinner(ui_text['status_background_research'].format(region=region)):
                cached_en = cache_manager.get_cached_response(region, category, 'research', 'en')
                if cached_en:
                    regional_summary_en = cached_en['content']
                else:
                    regional_summary_en = get_background_research(openai_client, en_region, en_category)
                    cache_manager.save_response(region, category, 'research', regional_summary_en, 'en')
                st.session_state.regional_summary_en = regional_summary_en
            
            # Display immediately
            summary = regional_summary_en
            if lang_code == 'sr':
                summary = translate_en_to_sr(openai_client, summary)
            st.markdown(summary)

            # --- Run and Display Initial Recommendations ---
            st.header(ui_text['project_recommendations_header'])
            with st.spinner(ui_text['status_generating_projects']):
                cached_en = cache_manager.get_cached_response(region, category, 'initial_recs', 'en')
                if cached_en:
                    initial_recs_en = cached_en['content']
                else:
                    initial_recs_en = get_initial_recommendations(openai_client, en_region, en_category, st.session_state.regional_analysis_en, st.session_state.regional_summary_en)
                    cache_manager.save_response(region, category, 'initial_recs', initial_recs_en, 'en')
                st.session_state.initial_recs_en = initial_recs_en

            # Display immediately
            initial_recs = initial_recs_en
            if lang_code == 'sr':
                initial_recs = translate_en_to_sr(openai_client, initial_recs)
            st.markdown(initial_recs)

            # --- Run and Display Final Projects ---
            st.header(ui_text['final_projects_header'])
            with st.spinner(ui_text['status_matching_projects']):
                cached_en = cache_manager.get_cached_response(region, category, 'final_projects', 'en')
                if cached_en:
                    final_projects_en = cached_en['content']
                else:
                    filtered_projects = filter_projects(df_projects, en_category)
                    json_projects = filtered_projects.to_json(orient="records")
                    final_projects_en = get_final_projects(openai_client, en_region, en_category, st.session_state.initial_recs_en, json_projects)
                    cache_manager.save_response(region, category, 'final_projects', final_projects_en, 'en')
                st.session_state.final_projects_en = final_projects_en

            # Display immediately
            final_projects = final_projects_en
            if lang_code == 'sr':
                final_projects = translate_en_to_sr(openai_client, final_projects)
            st.markdown(final_projects)
            
            st.rerun() # Rerun once at the end to finalize the state

# --- Display Project Recommendations (on subsequent reruns) ---
if st.session_state.stage >= 3:
    # Background Research
    st.header(ui_text['background_research_header'])
    summary_en = st.session_state.regional_summary_en
    if lang_code == 'sr':
        cached_sr = cache_manager.get_cached_response(st.session_state.option_region, st.session_state.option_category, 'research', 'sr')
        if cached_sr:
            summary = cached_sr['content']
        else:
            with st.spinner("Translating..."):
                summary = translate_en_to_sr(openai_client, summary_en)
                cache_manager.save_response(st.session_state.option_region, st.session_state.option_category, 'research', summary, 'sr')
    else:
        summary = summary_en
    st.markdown(summary)

    # Initial Recommendations
    st.header(ui_text['project_recommendations_header'])
    initial_recs_en = st.session_state.initial_recs_en
    if lang_code == 'sr':
        cached_sr = cache_manager.get_cached_response(st.session_state.option_region, st.session_state.option_category, 'initial_recs', 'sr')
        if cached_sr:
            initial_recs = cached_sr['content']
        else:
            with st.spinner("Translating..."):
                initial_recs = translate_en_to_sr(openai_client, initial_recs_en)
                cache_manager.save_response(st.session_state.option_region, st.session_state.option_category, 'initial_recs', initial_recs, 'sr')
    else:
        initial_recs = initial_recs_en
    st.markdown(initial_recs)

    # Final Project Selections
    st.header(ui_text['final_projects_header'])
    final_projects_en = st.session_state.final_projects_en
    if lang_code == 'sr':
        cached_sr = cache_manager.get_cached_response(st.session_state.option_region, st.session_state.option_category, 'final_projects', 'sr')
        if cached_sr:
            final_projects = cached_sr['content']
        else:
            with st.spinner("Translating..."):
                final_projects = translate_en_to_sr(openai_client, final_projects_en)
                cache_manager.save_response(st.session_state.option_region, st.session_state.option_category, 'final_projects', final_projects, 'sr')
    else:
        final_projects = final_projects_en
    st.markdown(final_projects)

# --- New Analysis Button ---
if st.session_state.stage > 0:
    if st.button(ui_text['new_analysis_button'], use_container_width=True):
        # Clear all session state except for language selection
        for key in st.session_state.keys():
            if key != 'selected_language':
                del st.session_state[key]
        st.rerun()
