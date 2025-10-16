import json
import time
import re
from datetime import datetime

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
from src.ui import render_sidebar, render_language_selection, render_main_interface, chart_latest_comparison_bar, chart_trend_sparkline, render_delta_chip
from src.analysis import (
    get_indicator_analysis, prepare_regional_analysis_data, filter_projects, get_indicator_series
)
from src.llm import (
    translate_en_to_sr, get_regional_narrative, get_background_research,
    get_initial_recommendations, get_final_projects, get_project_review_document
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

    # Charts-only mode: build Plotly visuals per indicator
    region = st.session_state.option_region
    category = st.session_state.option_category
    en_region = cache_manager._normalize_region_name(region)
    code_list = st.session_state.code_list
    code_name_dict = st.session_state.code_name_dict

    # Parse interpretations from the English narrative (robust against formatting variants)
    interpretations_map = {}
    try:
        narrative = st.session_state.regional_analysis_en or ""
        # Split into sections by numbered headers like "1. **Indicator**" or "1. Indicator"
        sections = re.split(r"\n(?=\s*\d+\.\s+\*\*?[^\n]+)", narrative)
        for sec in sections:
            # capture title inside ** ** or plain text after number
            title_match = re.search(r"^\s*\d+\.\s+(?:\*\*(.*?)\*\*|(.*))", sec)
            if not title_match:
                continue
            title = (title_match.group(1) or title_match.group(2) or "").strip()
            if not title:
                continue
            # find Interpretation line (case-insensitive), accept bold or plain
            interp_match = re.search(r"\b\*\*?Interpretation\*\*?\s*:?\s*(.*)$", sec, re.IGNORECASE | re.DOTALL)
            if interp_match:
                interp_raw = interp_match.group(1).strip()
                # stop at next numbered header if leak
                interp_raw = re.split(r"\n\s*\d+\.\s", interp_raw)[0].strip()
                # trim trailing bold markers
                interp_raw = interp_raw.strip('*').strip()
                if interp_raw:
                    interpretations_map[title] = interp_raw
    except Exception:
        interpretations_map = {}

    # Sort indicators by absolute pct delta (latest)
    indicator_stats = []
    for code in code_list:
        r_df, n_df, stats = get_indicator_series(df_indicators, averages_df, en_region, code_name_dict, code)
        indicator_stats.append((code, r_df, n_df, stats))
    indicator_stats = sorted(
        indicator_stats,
        key=lambda x: abs(x[3].get("pct_delta") or 0),
        reverse=True,
    )

    for code, r_df, n_df, stats in indicator_stats:
        full_name = stats["full_name"]
        higher_is_better = stats["higher_is_better"]
        latest_region = stats["latest_region"]
        latest_national = stats["latest_national"]
        unit = ''
        # Extract unit if present in parentheses
        m = re.search(r"\(unit: ([^\)]+)\)", full_name)
        if m:
            unit = m.group(1)

        col1, col2 = st.columns([1, 1])
        base_name = re.sub(r"\s*\(unit: [^\)]+\)", "", full_name).strip()
        with col1:
            bar_title = f"{base_name} — Latest vs National Avg"
            fig = chart_latest_comparison_bar(bar_title, latest_region, latest_national, unit, higher_is_better)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            if not r_df.empty and not n_df.empty:
                trend_title = f"{base_name} — Trend"
                fig2 = chart_trend_sparkline(trend_title, r_df, n_df, full_name, unit)
                st.plotly_chart(fig2, use_container_width=True)
        # Delta chip line
        delta_html = render_delta_chip(stats.get("delta"), stats.get("pct_delta"), higher_is_better)
        if delta_html:
            st.markdown(delta_html, unsafe_allow_html=True)

        # Interpretation paragraph (translated if Serbian)
        interpretation_text = interpretations_map.get(full_name)
        if interpretation_text:
            if lang_code == 'sr':
                try:
                    interpretation_text = translate_en_to_sr(openai_client, interpretation_text)
                except Exception:
                    pass
            st.markdown(f"**Interpretation:** {interpretation_text}")

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

    # --- Parse projects (title + URL) from English source text ---
    def _parse_projects_from_markdown(md_text: str):
        projects = []
        # Split by numbered headings like "1. **Title**"
        blocks = re.split(r"\n(?=\d+\. \*\*)", md_text)
        for block in blocks:
            title_match = re.search(r"^\d+\. \*\*(.*?)\*\*", block)
            if not title_match:
                continue
            title = title_match.group(1).strip()
            # Find URL line
            url = None
            # Prefer explicit URL line
            url_line_match = re.search(r"URL\s*:\s*(.*)", block)
            if url_line_match:
                # Extract first https URL from the URL line
                url_candidate = url_line_match.group(1)
                url_match = re.search(r"https?://[^\s)\]]+", url_candidate)
                if url_match:
                    url = url_match.group(0)
            if not url:
                # Fallback: first URL in the block
                url_match = re.search(r"https?://[^\s)\]]+", block)
                if url_match:
                    url = url_match.group(0)
            if url:
                projects.append({"title": title, "url": url})
        return projects

    parsed_projects = _parse_projects_from_markdown(final_projects_en)

    # --- Prefetch top 2 project details (English) ---
    prefetch_count = min(1, len(parsed_projects))
    for i in range(prefetch_count):
        p = parsed_projects[i]
        if not cache_manager.get_cached_project_details(p["url"], language='en'):
            with st.spinner(f"Fetching details for: {p['title']}"):
                try:
                    md = get_project_review_document(openai_client, p["url"], model="gpt-5", temperature=None)
                    cache_manager.save_project_details(p["url"], md, language='en', metadata={"title": p["title"]})
                except Exception as e:
                    st.info(f"Could not prefetch details for {p['title']}: {e}")

    # --- Render per-project details expander ---
    st.write("")
    st.subheader("More details")
    for p in parsed_projects:
        with st.expander(f"{p['title']} — More details"):
            details_en = cache_manager.get_cached_project_details(p["url"], language='en')
            if not details_en:
                with st.spinner("Researching project details..."):
                    try:
                        md = get_project_review_document(openai_client, p["url"], model="gpt-5", temperature=None)
                        cache_manager.save_project_details(p["url"], md, language='en', metadata={"title": p["title"]})
                        details_en = cache_manager.get_cached_project_details(p["url"], language='en')
                    except Exception as e:
                        st.warning(f"Unable to load project details: {e}")
                        details_en = None

            if details_en:
                created_at = details_en.get("created_at")
                freshness = ""
                try:
                    ts = datetime.fromisoformat(created_at)
                    hours_ago = int((datetime.now() - ts).total_seconds() // 3600)
                    freshness = f"Last updated {hours_ago}h ago"
                except Exception:
                    freshness = "Last updated recently"

                content_md = details_en.get("content", "")

                # Normalize inline pipe-separated tables into valid Markdown tables
                def _normalize_markdown_tables_inline(doc: str) -> str:
                    if not isinstance(doc, str):
                        return doc

                    def reformat_inline_table(line: str) -> str:
                        original = line
                        # Find first pipe; treat anything before as label text (e.g., "Financing Structure")
                        first_pipe_idx = line.find('|')
                        prefix = line[:first_pipe_idx] if first_pipe_idx > -1 else ''
                        table_part = line[first_pipe_idx:] if first_pipe_idx > -1 else line

                        # Split rows by double-pipe separators
                        rows = [r.strip() for r in re.split(r"\s*\|\|\s*", table_part) if r.strip()]
                        if not rows:
                            return original

                        parsed_rows = []
                        for r in rows:
                            cells = [c.strip() for c in r.strip('|').split('|')]
                            # drop empty trailing cells
                            while cells and cells[-1] == '':
                                cells.pop()
                            parsed_rows.append(cells)

                        # Handle header: drop label cell like "Financing Structure" or "Updated Timeline"
                        if parsed_rows and parsed_rows[0]:
                            first_cell_lower = parsed_rows[0][0].lower()
                            if first_cell_lower.startswith('financing') or first_cell_lower.startswith('updated timeline') or first_cell_lower.startswith('timeline'):
                                parsed_rows[0] = parsed_rows[0][1:]

                        if not parsed_rows or not parsed_rows[0]:
                            return original

                        header = parsed_rows[0]
                        # Skip any explicit separator rows containing ---
                        data_rows = [row for row in parsed_rows[1:] if not any('---' in c for c in row)]

                        # Build proper Markdown table
                        table_lines = []
                        table_lines.append('|' + ' | '.join(header) + '|')
                        table_lines.append('|' + '|'.join(['---'] * len(header)) + '|')
                        for row in data_rows:
                            # pad/truncate to header length for stability
                            if len(row) < len(header):
                                row = row + [''] * (len(header) - len(row))
                            elif len(row) > len(header):
                                row = row[:len(header)]
                            table_lines.append('|' + ' | '.join(row) + '|')
                        return '\n'.join(table_lines)

                    out_lines = []
                    for line in doc.split('\n'):
                        if '||' in line and '|' in line:
                            out_lines.append(reformat_inline_table(line))
                        else:
                            out_lines.append(line)
                    return '\n'.join(out_lines)

                content_md = _normalize_markdown_tables_inline(content_md)

                if lang_code == 'sr':
                    try:
                        with st.spinner("Translating details..."):
                            content_md = translate_en_to_sr(openai_client, content_md)
                            # Save translated version for future opens
                            cache_manager.save_project_details(p["url"], content_md, language='sr', metadata={"title": p["title"], "translated_from": created_at})
                    except Exception:
                        pass

                st.caption(f"{freshness} • Web sources")
                st.markdown(content_md)

# --- New Analysis Button ---
if st.session_state.stage > 0:
    if st.button(ui_text['new_analysis_button'], use_container_width=True):
        # Clear all session state except for language selection
        for key in st.session_state.keys():
            if key != 'selected_language':
                del st.session_state[key]
        st.rerun()
