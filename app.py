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
def run_full_analysis():
    """Orchestrates the full analysis pipeline."""
    region = st.session_state.option_region
    category = st.session_state.option_category
    
    # Get English names for processing
    en_category = cache_manager._normalize_category_name(category)
    en_region = cache_manager._normalize_region_name(region)

    # --- 1. Indicator Analysis ---
    st.header(ui_text['relevant_indicators_header'])
    with st.status(ui_text['status_starting_analysis'].format(category=category, region=region), expanded=True):
        indicator_response_en, code_list, code_name_dict = get_indicator_analysis(df_indicatorlist, en_category)
        if lang_code == 'sr':
            indicator_response = translate_en_to_sr(openai_client, indicator_response_en)
        else:
            indicator_response = indicator_response_en
        st.markdown(indicator_response)

    # --- 2. Regional Analysis ---
    st.header(ui_text['regional_analysis_header'])
    with st.status(ui_text['status_conducting_regional'], expanded=True):
        comparison_text = prepare_regional_analysis_data(df_indicators, averages_df, en_region, code_list, code_name_dict)
        regional_analysis_en = get_regional_narrative(openai_client, en_region, en_category, comparison_text)
        if lang_code == 'sr':
            regional_analysis = translate_en_to_sr(openai_client, regional_analysis_en)
        else:
            regional_analysis = regional_analysis_en
        st.markdown(regional_analysis)

    # --- 3. Project Recommendations ---
    # Background Research
    st.header(ui_text['background_research_header'])
    with st.status(ui_text['status_background_research'].format(region=region), expanded=True):
        regional_summary_en = get_background_research(openai_client, en_region, en_category)
        if lang_code == 'sr':
            regional_summary = translate_en_to_sr(openai_client, regional_summary_en)
        else:
            regional_summary = regional_summary_en
        st.markdown(regional_summary)

    # Initial Recommendations
    st.header(ui_text['project_recommendations_header'])
    with st.status(ui_text['status_generating_projects'], expanded=True):
        initial_recs_en = get_initial_recommendations(openai_client, en_region, en_category, regional_analysis_en, regional_summary_en)
        if lang_code == 'sr':
            initial_recs = translate_en_to_sr(openai_client, initial_recs_en)
        else:
            initial_recs = initial_recs_en
        st.markdown(initial_recs)

    # Final Project Selections
    st.header(ui_text['final_projects_header'])
    with st.status(ui_text['status_matching_projects'], expanded=True):
        filtered_projects = filter_projects(df_projects, en_category)
        json_projects = filtered_projects.to_json(orient="records")
        final_projects_en = get_final_projects(openai_client, en_region, en_category, initial_recs_en, json_projects)
        if lang_code == 'sr':
            final_projects = translate_en_to_sr(openai_client, final_projects_en)
        else:
            final_projects = final_projects_en
        st.markdown(final_projects)


if st.button(ui_text['start_button']):
    st.session_state.start_analysis = True

if 'start_analysis' in st.session_state and st.session_state.start_analysis:
    run_full_analysis()
