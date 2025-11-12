import json
import time
import re
from datetime import datetime
import html as _html
import difflib

import streamlit as st
from openai import OpenAI
from google.oauth2 import service_account
from google.cloud import storage
import numpy as np
import pandas as pd
import esda
import libpysal as lps

import plotly.express as px
import plotly.graph_objects as go

# Local imports
from src.config import (
    BUCKET_NAME, CACHE_PATH, UI_TEXT, CATEGORY_OPTIONS_EN,
    CATEGORY_OPTIONS_SR, SLEEP_TIME
)
from src.gcs import read_csv_from_gcs, get_image_from_gcs, read_geojson_from_gcs
from src.caching import ResponseCacheManager
from src.ui import (render_sidebar, render_language_selection, render_main_interface, chart_latest_comparison_bar, chart_trend_sparkline, 
                    render_delta_chip, spacer, render_transparency_badges, render_sources_badges, render_map_options, render_scatterplot_options, 
                    remove_unit_suffix, normalize, render_choropleth_text)
from src.analysis import (
    get_indicator_analysis, prepare_regional_analysis_data, filter_projects, get_indicator_series, calculate_indicator_score
)
from src.config import INDICATOR_SOURCES, COLUMN_ORDER
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
    
    gdf_score_geom = read_geojson_from_gcs(
        _storage_client, BUCKET_NAME, "decision_engine/inputs/SRB_Score_geom_v6.json"
    )
    
    regions_en = df_indicators["ENGLISH_NAME"].unique().tolist()
    regions_sr = df_indicators["SERBIAN_NAME_CYRILLIC"].unique().tolist()
    
    averages_df = df_indicators.groupby("year")[df_indicators.columns[4:]].mean().reset_index()
    
    return df_indicatorlist, df_indicators, df_projects, regions_en, regions_sr, averages_df, gdf_score_geom

df_indicatorlist, df_indicators, df_projects, regions_en, regions_sr, averages_df, gdf_score_geom = load_data(storage_client)

# --- UI Rendering ---
cache_manager = ResponseCacheManager(storage_client, BUCKET_NAME, CACHE_PATH, df_indicators)
pimpam_logo = get_image_from_gcs(storage_client, BUCKET_NAME, "decision_engine/inputs/wbg-pimpam.png")
gpbp_logo = get_image_from_gcs(storage_client, BUCKET_NAME, "decision_engine/inputs/GPBP logo.jpg")

render_sidebar(pimpam_logo, gpbp_logo, cache_manager)


choropleth, scatterplot,decision_engine = st.tabs(["🗺️ Map", 
                                       "📊 Scatterplot",
                                       "🤖 Decision Engine"])

with choropleth:
    st.header("🗺️ Spatial Mapping")
    # st.write("This is a map of Serbia.")
    
    df_choropleth = gdf_score_geom.drop(['population_total'], axis=1)
    df_choropleth = df_choropleth[COLUMN_ORDER]
    
    render_map_options(df_choropleth['year'].unique().tolist(), df_choropleth.columns[3:-1].to_list())
    
    year = st.session_state.option_year
    indicator = st.session_state.option_indicator
    
    slice_choropleth = df_choropleth[['ENGLISH_NAME', 'year', indicator, 'geometry']]
    slice_choropleth = slice_choropleth[slice_choropleth['year'] == year]
    slice_choropleth[f'{indicator}_score'] = calculate_indicator_score(indicator, slice_choropleth)
    geojson_data = slice_choropleth.__geo_interface__
    
    wq = lps.weights.Queen.from_dataframe(slice_choropleth, use_index=False, silence_warnings=True)
    wq.transform = "r"
    y = slice_choropleth[indicator]
    np.random.seed(12345)
    global_mi = esda.moran.Moran(y, wq)
    global_significance = 'Significant' if global_mi.p_sim < 0.05 else 'Not Significant'
    
    local_mi = esda.moran.Moran_Local(y, wq)
    region_local_significance = f'{((local_mi.p_sim < 0.05).sum() / len(slice_choropleth)) * 100:.1f}'
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Municipalities", len(slice_choropleth))
    col2.metric("Global Spatial Autocorrelation", global_significance)
    col3.metric("Municipalities with Significant Local Spatial Autocorrelation", f'{region_local_significance}%')
    
    
    # Plot
    fig = px.choropleth(
        slice_choropleth,
        geojson=geojson_data,
        locations='ENGLISH_NAME',
        featureidkey='properties.ENGLISH_NAME',
        color=f'{indicator}_score',
        color_continuous_scale="RdYlGn",
        range_color=(0, 100),
        hover_data=['ENGLISH_NAME', indicator],
        labels={"ENGLISH_NAME": "Municipality",
                indicator: f"{indicator}", 
                f'{indicator}_score': f'{remove_unit_suffix(indicator)} Score'},
        title=f'{remove_unit_suffix(indicator)} in Serbia, {year}',
        scope='europe',
        width=1000,
        height=1000
    )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0},
                      coloraxis_colorbar_title_text=f'{remove_unit_suffix(indicator)} Score' if "Score" not in indicator else remove_unit_suffix(indicator),
                      coloraxis_colorbar_title_font=dict(
                        size=15,
                        color="black"),
                      title=dict(text=f'{remove_unit_suffix(indicator)} in Serbia, {year}',
                                 font=dict(size=30, color="black")),
                      )
    
    st.plotly_chart(fig, use_container_width=True)
    
    render_choropleth_text()
    
    np.random.seed(12345)
    sig = 1 * (local_mi.p_sim < 0.05)
    hh = 1 * (sig * local_mi.q == 1)
    ll = 2 * (sig * local_mi.q == 2)
    hl = 3 * (sig * local_mi.q == 3)
    lh = 4 * (sig * local_mi.q == 4)
    spots = hh + ll + hl + lh
    
    spot_labels = [
        "Not Significant",
        "High-High (Hotspot)",
        "Low-Low (Coldspot)",
        "High-Low",
        "Low-High",
    ]
    labels = [spot_labels[i] for i in spots]

    # attach label to the GeoDataFrame slice
    slice_choropleth["cl"] = labels

    # consistent legend order + colors
    category_order = {"cl": spot_labels}
    color_map = {
        "Not Significant": "lightgrey",
        "High-High (Hotspot)": "red",
        "Low-Low (Coldspot)": "lightblue",
        "High-Low (Outlier)": "green",
        "Low-High (Outlier)": "yellow",
    }

    # geojson from the slice itself (ensures one-to-one match)
    geojson_data = json.loads(slice_choropleth.to_json())

    fig_li = px.choropleth(
        slice_choropleth,
        geojson=geojson_data,
        locations="ENGLISH_NAME",
        featureidkey="properties.ENGLISH_NAME",
        color="cl",
        category_orders=category_order,
        color_discrete_map=color_map,
        hover_data=["ENGLISH_NAME", "cl"],
        labels={"ENGLISH_NAME": "Municipality", "cl": "Cluster Type"},
        scope="europe",
    )

    # styling: thin white borders, fit to data, ensure legend shows
    fig_li.update_traces(marker_line_width=0.5, marker_line_color="white")
    fig_li.update_geos(fitbounds="locations", visible=False)
    fig_li.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        legend_title_text="Cluster Type",
        showlegend=True,
        legend=dict(
            orientation="v",          # vertical legend
            yanchor="middle",
            y=0.8,                    # center vertically
            xanchor="left",
            x=0.6,                   # 1.02 = just outside the map
            bgcolor="rgba(255,255,255,0.7)",  # semi-transparent white box
            # bordercolor="black",
            borderwidth=0.5,
            font=dict(size=14)
        ),
        title=dict(
            text=f"Local Spatial Autocorrelation of {remove_unit_suffix(indicator)} in Serbia, {year}",
            font=dict(size=24),
            x=0, xanchor="left"
        ),
        plot_bgcolor="white",
        height=1000,
        width=1000,
    )

    st.plotly_chart(fig_li, use_container_width=True)
    

with scatterplot:
    st.header("📊 Scatterplot")
    st.write("This is a scatterplot of Serbia.")
    
    df_scatter = pd.DataFrame(gdf_score_geom.drop(['population_total'], axis=1))
    
    indicators_x = ["Accessibility to Healthcare Services (unit: %)",
                    "Accessibility to School Services (unit: %)",
                    "Diversity of Health Services",
                    "PM 2.5 concentration (unit: µg/m3)",
                    "PM 10 concentration (unit: µg/m3)",
                    "NO2 concentration (unit: µg/m3)",
                    "Total Methane Emissions (unit: tonnes)",
                    "Total CO2-Equivalent Emissions (unit: tonnes)",
                    "Total CO2-Equivalent Emissions from Coal Power Plants (unit: tonnes)",
                    "Livability Score"]
    
    indicators_y = ["Nighttime Luminosity (unit: nWatts/(cm2 x sr)",
                    "Key Structure Average Broadband Download Speed (unit: megabites per second)",
                    "Average Cellular Download Speed (unit: megabites per second)",
                    "Key Structures without Internet Access (unit: %)",
                    "Railway Flood Risk (unit: km)",
                    "Road Flood Risk (unit: km)",
                    "Railway Heatwave Risk (unit: km)",
                    "Road Heatwave Risk (unit: km)",
                    "Prosperity Score"]
    
    render_scatterplot_options(df_scatter['year'].unique().tolist(), indicators_x, indicators_y)
    
    year = st.session_state.option_year_scatterplot
    indicator_x = st.session_state.option_indicator_x
    indicator_y = st.session_state.option_indicator_y
    
    slice_scatter = df_scatter[['ENGLISH_NAME', 'year', indicator_x, indicator_y]]
    slice_scatter = slice_scatter[slice_scatter['year'] == year]
    
    x_score_name = remove_unit_suffix(indicator_x)
    y_score_name = remove_unit_suffix(indicator_y)

    slice_scatter[x_score_name] = calculate_indicator_score(indicator_x, df_scatter)
    slice_scatter[y_score_name] = calculate_indicator_score(indicator_y, df_scatter)
    
    custom_data = slice_scatter[['ENGLISH_NAME', 
                         x_score_name, y_score_name,
                         indicator_x, indicator_y]]
    
    x_vals = slice_scatter[x_score_name].astype(float)
    y_vals = slice_scatter[y_score_name].astype(float)
    x_min, x_max = 0, 100
    y_min, y_max = 0, 100
    x_mid = (x_min + x_max) / 2
    y_mid = (y_min + y_max) / 2
    
    # Build normalized lookup table
    name_lookup = {normalize(s): s for s in slice_scatter["ENGLISH_NAME"].unique()}
    
    # Text input box
    highlight_txt = st.text_input(
        "🔎 Highlight a municipality (you can type partial or accent-free name, e.g., sabac or Nis):",
        value="Veliko Gradište", placeholder="e.g., sabac or Nis"
    )
    
    fig = px.scatter(
        slice_scatter,
        x=x_score_name,
        y=y_score_name,
        hover_data=None,
        custom_data=custom_data,
        labels={
            "ENGLISH_NAME": "Municipality",
            x_score_name: f'{x_score_name} Score',
            y_score_name: f'{y_score_name} Score',
            indicator_x: f"{indicator_x}",
            indicator_y: f"{indicator_y}",
        },
        title=f'{indicator_x} vs {indicator_y} in Serbia, {year}',
        width=1000, height=1000
    )
    
    # Set explicit axis ranges so shapes align perfectly
    fig.update_xaxes(range=[x_min, x_max])
    fig.update_yaxes(range=[y_min, y_max])

    # Add quadrant shading (low opacity so points stay visible)
    fig.add_shape(type="rect", xref="x", yref="y",
                x0=x_mid, x1=x_max, y0=y_mid, y1=y_max,
                fillcolor="green", opacity=0.10, line_width=0, layer="below")     # Top Right

    fig.add_shape(type="rect", xref="x", yref="y",
                x0=x_min, x1=x_mid, y0=y_mid, y1=y_max,
                fillcolor="yellow", opacity=0.10, line_width=0, layer="below")    # Top Left

    fig.add_shape(type="rect", xref="x", yref="y",
                x0=x_mid, x1=x_max, y0=y_min, y1=y_mid,
                fillcolor="yellow", opacity=0.10, line_width=0, layer="below")    # Bottom Right

    fig.add_shape(type="rect", xref="x", yref="y",
                x0=x_min, x1=x_mid, y0=y_min, y1=y_mid,
                fillcolor="red", opacity=0.10, line_width=0, layer="below")       # Bottom Left
    
    # Add quadrant labels at each quadrant center
    fig.add_annotation(x=(x_mid + x_max)/2, y=(y_mid + y_max)/2,
                    text="High Prosperity and Livability", showarrow=False, font=dict(size=20, color="green"))
    fig.add_annotation(x=(x_min + x_mid)/2, y=(y_mid + y_max)/2,
                    text="High Prosperity, Low Livability", showarrow=False, font=dict(size=20, color="#a67c00"))
    fig.add_annotation(x=(x_mid + x_max)/2, y=(y_min + y_mid)/2,
                    text="Low Prosperity, High Livability", showarrow=False, font=dict(size=20, color="#a67c00"))
    fig.add_annotation(x=(x_min + x_mid)/2, y=(y_min + y_mid)/2,
                    text="Low Prosperity and Livability", showarrow=False, font=dict(size=20, color="red"))

    # Add crosshair lines at the midpoints
    fig.add_vline(x=x_mid, line_width=2, line_dash="dash", line_color="black")
    fig.add_hline(y=y_mid, line_width=2, line_dash="dash", line_color="black")

    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            f"{x_score_name} Score: %{{customdata[1]:.0f}}<br>"
            f"{y_score_name} Score: %{{customdata[2]:.0f}}<br>"
            f"{indicator_x}: %{{customdata[3]:.2f}}<br>"
            f"{indicator_y}: %{{customdata[4]:.2f}}"
            "<extra></extra>"
        ),
        marker=dict(color='black')
    )
    
    fig.update_layout(
        title=dict(text=f"{y_score_name} vs {x_score_name} in Serbia, {year}",
                font=dict(size=27), x=0.5, xanchor='center'),
        xaxis_title=f'{x_score_name} Score',
        yaxis_title=f'{y_score_name} Score',
        xaxis=dict(tickfont=dict(size=19), showline=True, linecolor="black", linewidth=2, ticks="outside", tickwidth=2, tickcolor="black"),
        yaxis=dict(tickfont=dict(size=19), showline=True, linecolor="black", linewidth=2, ticks="outside", tickwidth=2, tickcolor="black"),
        xaxis_title_font=dict(size=23),
        yaxis_title_font=dict(size=23),
        plot_bgcolor="white",
        height=1000,
        width=1000
    )

    # Hide the colorbar
    fig.update_coloraxes(showscale=False)
    
    if highlight_txt.strip():
        norm_input = normalize(highlight_txt)
        
        # 1️⃣ Find substring matches
        matches = [v for k, v in name_lookup.items() if norm_input in k]
        
        # 2️⃣ If no substring matches, find close fuzzy matches
        if not matches:
            all_norms = list(name_lookup.keys())
            close_keys = difflib.get_close_matches(norm_input, all_norms, n=3, cutoff=0.6)
            matches = [name_lookup[k] for k in close_keys]

        # 3️⃣ If exactly one match, highlight it
        if len(matches) == 1:
            name = matches[0]
            sel = slice_scatter[slice_scatter["ENGLISH_NAME"] == name]
            fig.add_trace(
                go.Scatter(
                    x=sel[x_score_name],
                    y=sel[y_score_name],
                    mode="markers+text",
                    text=sel["ENGLISH_NAME"],
                    textposition="top center",
                    name=f"Highlighted: {name}",
                    marker=dict(
                        symbol="diamond",
                        size=20,
                        line=dict(width=2, color="white"),
                        color="crimson"
                    ),
                    customdata=sel[["ENGLISH_NAME", x_score_name, y_score_name, indicator_x, indicator_y]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        f"{x_score_name} Score: %{{customdata[1]:.0f}}<br>"
                        f"{y_score_name} Score: %{{customdata[2]:.0f}}<br>"
                        f"{indicator_x}: %{{customdata[3]:.2f}}<br>"
                        f"{indicator_y}: %{{customdata[4]:.2f}}"
                        "<extra></extra>"
                    ),
                    showlegend=True
                )
            )
            st.success(f"✅ Highlighted: **{name}**")
        elif len(matches) > 1:
            st.info(f"Found multiple matches: {', '.join(matches[:5])}...")
        else:
            st.warning("No match found. Try typing part of the name or removing accents.")

    st.plotly_chart(fig, use_container_width=True)


with decision_engine:
    lang_code = render_language_selection()

    regions = regions_sr if lang_code == "sr" else regions_en
    categories = CATEGORY_OPTIONS_SR if lang_code == "sr" else CATEGORY_OPTIONS_EN
    ui_text = UI_TEXT[lang_code]

    render_main_interface(lang_code, regions, categories)

    # --- Main App Logic ---

    # --- Helpers: SWOT parsing and rendering ---
    def _parse_swot_from_markdown(md: str) -> dict:
        """Extract Strengths, Weaknesses, Opportunities, Challenges bullet lists from LLM markdown."""
        if not isinstance(md, str):
            return {"strengths": [], "weaknesses": [], "opportunities": [], "challenges": []}
        def _extract(section: str) -> list:
            # Capture text block after **Section:** until next bold heading or end
            m = re.search(rf"\*\*{re.escape(section)}\s*:\s*\*\*(.*?)(\n\s*\*\*|$)", md, re.IGNORECASE | re.DOTALL)
            block = m.group(1) if m else ""
            # Lines starting with '-' or '•'
            items = []
            for line in block.splitlines():
                stripped = line.strip()
                if stripped.startswith("-") or stripped.startswith("•"):
                    val = stripped.lstrip("-• ").strip()
                    if val and val not in ("...", "-"):
                        items.append(val)
            return items
        return {
            "strengths": _extract("Strengths"),
            "weaknesses": _extract("Weaknesses"),
            "opportunities": _extract("Opportunities"),
            "challenges": _extract("Challenges"),
        }

    def _translate_list_if_needed(client: OpenAI, items: list, lang: str) -> list:
        if lang != 'sr' or not items:
            return items
        joined = "\n".join(f"- {it}" for it in items)
        try:
            translated = translate_en_to_sr(client, joined)
            # Re-split to bullets (keep order)
            out = []
            for line in translated.splitlines():
                line = line.strip()
                if line.startswith("-") or line.startswith("•"):
                    line = line.lstrip("-• ").strip()
                if line:
                    out.append(line)
            return out or items
        except Exception:
            return items

    def _render_swot(swot: dict, lang: str, region_label: str, subcategory_label: str):
        title_prefix = "SWOT Summary" if lang == 'en' else "SWOT резиме"
        st.markdown(f"### 💡 {subcategory_label} {title_prefix} for {region_label}")

        strengths = swot.get("strengths", [])
        weaknesses = swot.get("weaknesses", [])
        opportunities = swot.get("opportunities", [])
        challenges = swot.get("challenges", [])

        def _to_html_with_links(text: str) -> str:
            """Escape text but convert Markdown links or bare URLs/domains into HTML anchors.
            Supports [label](transparentnost.org.rs) and bare domains by prepending https:// when missing.
            """
            if not isinstance(text, str):
                return ""
            md_link = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
            combined = re.compile(r"\[([^\]]+)\]\(([^)]+)\)|(?<!@)\b(?:https?://)?(?:www\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s)]+)?")
            out = []
            idx = 0
            for m in combined.finditer(text):
                start, end = m.span()
                if start > idx:
                    out.append(_html.escape(text[idx:start]))
                frag = text[start:end]
                mm = md_link.match(frag)
                if mm:
                    label = _html.escape(mm.group(1))
                    raw_url = mm.group(2).strip()
                    if not raw_url.lower().startswith(("http://", "https://")):
                        raw_url = "https://" + raw_url
                    url = _html.escape(raw_url)
                    out.append(f"<a href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">{label}</a>")
                else:
                    raw_url = frag.strip()
                    if not raw_url.lower().startswith(("http://", "https://")):
                        raw_url = "https://" + raw_url
                    url = _html.escape(raw_url)
                    label = _html.escape(frag.strip())
                    out.append(f"<a href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">{label}</a>")
                idx = end
            if idx < len(text):
                out.append(_html.escape(text[idx:]))
            return "".join(out)

        def _box_html(title: str, items: list, bg: str, icon: str) -> str:
            lis = "\n".join(f"<li>{_to_html_with_links(str(i))}</li>" for i in items) if items else "<li>-</li>"
            return (
                f"""
                <div style='background-color:{bg};padding:1.1em;border-radius:12px;'>
                <h4>{icon} {title}</h4>
                <ul style='margin-bottom:0;'>
                {lis}
                </ul>
                </div>
                """
            )

        # Row 1
        col1, col2 = st.columns(2)
        with col1:
            title = "Strengths" if lang == 'en' else "Снаге"
            st.markdown(_box_html(title, strengths, "#A9D8C2", "💪"), unsafe_allow_html=True)
        with col2:
            title = "Weaknesses" if lang == 'en' else "Слабости"
            st.markdown(_box_html(title, weaknesses, "#B9D6F2", "⚠️"), unsafe_allow_html=True)

        # Row 2
        col3, col4 = st.columns(2)
        with col3:
            title = "Opportunities" if lang == 'en' else "Могућности"
            st.markdown(_box_html(title, opportunities, "#FBE7A1", "🌱"), unsafe_allow_html=True)
        with col4:
            title = "Challenges" if lang == 'en' else "Изазови"
            st.markdown(_box_html(title, challenges, "#F7B6A3", "🚧"), unsafe_allow_html=True)

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
                
            # Transparency badges: year, coverage %, gaps
            render_transparency_badges(stats.get("latest_year"), stats.get("years_min"), stats.get("years_max"), stats.get("coverage_pct"), stats.get("missing_years"))

            # Sources badges (multiple supported)
            render_sources_badges(INDICATOR_SOURCES.get(full_name))

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
                
                # Display immediately (SWOT layout + CBD context card)
                summary = regional_summary_en
                swot = _parse_swot_from_markdown(summary)
                # Translate bullets if Serbian
                if lang_code == 'sr':
                    for k in list(swot.keys()):
                        swot[k] = _translate_list_if_needed(openai_client, swot[k], lang_code)
                _render_swot(swot, lang_code, region, category)
                # Render CBD context card if present
                context_items = swot.get("cbd_context", [])
                if context_items:
                    st.write("")
                    title = "Context from the PIMxPAM Country Benchmarking Dashboard" if lang_code == 'en' else "Контекст из PIMxPAM Country Benchmarking Dashboard"
                    st.markdown(
                        f"""
                        <div style='background-color:#EDE7F6;padding:1.1em;border-radius:12px;'>
                        <h4>📊 {title}</h4>
                        <ul style='margin-bottom:0;'>
                        {''.join(f"<li>{_to_html_with_links(str(i))}</li>" for i in context_items)}
                        </ul>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

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
        # Background Research (SWOT)
        st.header(ui_text['background_research_header'])
        summary_en = st.session_state.regional_summary_en
        swot = _parse_swot_from_markdown(summary_en)
        if lang_code == 'sr':
            for k in list(swot.keys()):
                swot[k] = _translate_list_if_needed(openai_client, swot[k], lang_code)
        _render_swot(swot, lang_code, st.session_state.option_region, st.session_state.option_category)
        context_items = swot.get("cbd_context", [])
        if context_items:
            st.write("")
            title = "Context from the PIMxPAM Country Benchmarking Dashboard" if lang_code == 'en' else "Контекст из PIMxPAM Country Benchmarking Dashboard"
            st.markdown(
                f"""
                <div style='background-color:#EDE7F6;padding:1.1em;border-radius:12px;'>
                <h4>📊 {title}</h4>
                <ul style='margin-bottom:0;'>
                {''.join(f"<li>{_to_html_with_links(str(i))}</li>" for i in context_items)}
                </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Initial Recommendations
        spacer(24)
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
                        md = get_project_review_document(openai_client, p["url"], model=None, temperature=None)
                        cache_manager.save_project_details(p["url"], md, language='en', metadata={"title": p["title"]})
                    except Exception as e:
                        st.info(f"Could not prefetch details for {p['title']}: {e}")

        # --- Render per-project details expander ---
        st.write("")
        st.subheader("More Project Details")
        for p in parsed_projects:
            with st.expander(f"{p['title']} — More details"):
                details_en = cache_manager.get_cached_project_details(p["url"], language='en')
                if not details_en:
                    with st.spinner("Researching project details..."):
                        try:
                            md = get_project_review_document(openai_client, p["url"], model=None, temperature=None)
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

                    # Try to extract structured JSON block for deterministic tables
                    def _extract_json_block(md: str):
                        try:
                            m = re.search(r"```json\s*([\s\S]*?)\s*```", md)
                            if not m:
                                return None
                            import json as _json
                            return _json.loads(m.group(1))
                        except Exception:
                            return None

                    json_block = _extract_json_block(content_md)
                    if json_block and isinstance(json_block, dict):
                        narrative = (json_block.get("narrative_markdown") or "").strip()

                        # Build tables as Markdown strings
                        def build_financing_table(fs_list):
                            if not isinstance(fs_list, list) or not fs_list:
                                return ""
                            lines = ["| Instrument | Amount | Source |", "|---|---|---|"]
                            for row in fs_list:
                                inst = str(row.get("instrument", "")).replace('|','\\|')
                                amt = str(row.get("amount_text", "")).replace('|','\\|')
                                sl = str(row.get("source_label", "")).replace('|','\\|')
                                su = str(row.get("source_url", ""))
                                src = f"[{sl}]({su})" if su else sl
                                lines.append(f"| {inst} | {amt} | {src} |")
                            return "\n".join(lines)

                        def build_timeline_table(tl_list):
                            if not isinstance(tl_list, list) or not tl_list:
                                return ""
                            lines = ["| Date | Milestone | Source |", "|---|---|---|"]
                            for row in tl_list:
                                dt = str(row.get("date_iso", "")).replace('|','\\|')
                                ms = str(row.get("milestone", "")).replace('|','\\|')
                                sl = str(row.get("source_label", "")).replace('|','\\|')
                                su = str(row.get("source_url", ""))
                                src = f"[{sl}]({su})" if su else sl
                                lines.append(f"| {dt} | {ms} | {src} |")
                            return "\n".join(lines)

                        financing_md = build_financing_table(json_block.get("financing_structure") or [])
                        timeline_md = build_timeline_table(json_block.get("updated_timeline") or [])

                        # Helper: insert a table after a heading line that mentions a keyword
                        def insert_after_heading(doc: str, keyword: str, table: str) -> str:
                            if not table:
                                return doc
                            try:
                                pattern = re.compile(rf"^.*{re.escape(keyword)}.*$", re.IGNORECASE | re.MULTILINE)
                                m = pattern.search(doc)
                                if not m:
                                    return doc + ("\n\n" + table)
                                insert_pos = m.end()
                                return doc[:insert_pos] + "\n\n" + table + doc[insert_pos:]
                            except Exception:
                                return doc + ("\n\n" + table)

                        # Start from narrative; inject tables near their semantic headings
                        content_md = narrative
                        if financing_md:
                            content_md = insert_after_heading(content_md, "Financing Structure", financing_md)
                        if timeline_md:
                            content_md = insert_after_heading(content_md, "Updated Timeline", timeline_md)

                    # Normalize common table variants into GitHub-style Markdown tables
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

                        # Also handle bullet-line blocks like "- field1 | field2 | [label](url)"
                        lines = doc.split('\n')
                        out_lines = []
                        i = 0
                        while i < len(lines):
                            if lines[i].lstrip().startswith('- ') and '|' in lines[i]:
                                block = []
                                j = i
                                while j < len(lines) and lines[j].lstrip().startswith('- ') and '|' in lines[j]:
                                    block.append(lines[j].lstrip()[2:].strip())
                                    j += 1
                                rows = [[c.strip() for c in r.strip('|').split('|')] for r in block if '|' in r]
                                col_count = max((len(r) for r in rows), default=0)
                                if col_count >= 2 and all(len(r) == col_count for r in rows[: min(3, len(rows))]):
                                    header = ['Instrument', 'Amount', 'Source'] if col_count == 3 else [f'Col {k+1}' for k in range(col_count)]
                                    table_lines = ['|' + ' | '.join(header) + '|', '|' + '|'.join(['---'] * len(header)) + '|']
                                    for r in rows:
                                        table_lines.append('|' + ' | '.join(r) + '|')
                                    out_lines.append('\n'.join(table_lines))
                                    i = j
                                    continue
                            if '||' in lines[i] and '|' in lines[i]:
                                out_lines.append(reformat_inline_table(lines[i]))
                            else:
                                out_lines.append(lines[i])
                            i += 1
                        return '\n'.join(out_lines)

                    # Fallback: if JSON missing, try a stricter retry (JSON-only). Then normalize if needed.
                    if not json_block:
                        try:
                            with st.spinner("Standardizing format..."):
                                md_retry = get_project_review_document(openai_client, p["url"], model=None, temperature=None, json_only=True)
                                import json as _json
                                jb = _json.loads(md_retry) if md_retry else None
                                if isinstance(jb, dict) and (jb.get("financing_structure") or jb.get("updated_timeline")):
                                    # Render tables + narrative
                                    fs = jb.get("financing_structure") or []
                                    tl = jb.get("updated_timeline") or []
                                    parts = []
                                    if fs:
                                        parts.append("| Instrument | Amount | Source |\n|---|---|---|")
                                        for row in fs:
                                            inst = str(row.get("instrument", "")).replace('|','\\|')
                                            amt = str(row.get("amount_text", "")).replace('|','\\|')
                                            sl = str(row.get("source_label", "")).replace('|','\\|')
                                            su = str(row.get("source_url", ""))
                                            src = f"[{sl}]({su})" if su else sl
                                            parts.append(f"| {inst} | {amt} | {src} |")
                                    if tl:
                                        parts.append("\n| Date | Milestone | Source |\n|---|---|---|")
                                        for row in tl:
                                            dt = str(row.get("date_iso", "")).replace('|','\\|')
                                            ms = str(row.get("milestone", "")).replace('|','\\|')
                                            sl = str(row.get("source_label", "")).replace('|','\\|')
                                            su = str(row.get("source_url", ""))
                                            src = f"[{sl}]({su})" if su else sl
                                            parts.append(f"| {dt} | {ms} | {src} |")
                                    content_md = "\n".join(parts) + "\n\n" + (jb.get("narrative_markdown") or content_md)
                                    # Save standardized content for future loads
                                    cache_manager.save_project_details(p["url"], content_md, language='en', metadata={"title": p["title"], "standardized": True})
                        except Exception:
                            pass

                    # Fallback: normalize loose table patterns
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
