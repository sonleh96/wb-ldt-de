import base64
from io import BytesIO
from datetime import datetime

import streamlit as st
from PIL import Image
import re
import unicodedata

from src.config import UI_TEXT, CHART_COLORS, DELTA_THRESHOLDS
import plotly.graph_objects as go
from src.caching import ResponseCacheManager

def get_base64_from_image(image: Image.Image) -> str:
    """Converts a PIL Image to a base64 encoded string."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def render_sidebar(pimpam_logo: Image.Image, gpbp_logo: Image.Image, cache_manager: ResponseCacheManager):
    """Renders the sidebar, including logos, about text, and cache admin panel."""
    st.sidebar.image(pimpam_logo, use_container_width=True)
    st.logo(gpbp_logo, size='large')

    with st.sidebar:
        st.markdown(
            """
            <style>
                .sidebar-text {
                    text-align: left; font-family: Arial, sans-serif; font-size: 0.9rem;
                    color: black; line-height: 1.5;
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.write("### 🌍 About the App")
        st.markdown(
            """
            <div class="sidebar-text">
                <strong>The Geospatial Planning & Budgeting Platform (GPBP) Local Development Tracker Decision Engine (LDT-DE)</strong> harnesses regional geospatial data developed by the LDT to help policymakers prioritize projects focused on 
                regional environmental and economic development. It was developed by the World Bank Group as part of the 
                <a href="https://pim-pam.net/" target="_blank">PimPam Network</a>.
                This tool not only centralizes and streamlines various remote sensing and geospatial data sources, but also leverages key insights from complementary platforms and digital apps on the PimPam GPBP, such as:
                <li><a href="https://cbd.pim-pam.net/" target="_blank">Country Benchmarking Dashboard</a> (CBD)</li>
                <li><a href="https://gpbp.adamplatform.eu/" target="_blank">Climate Change Screening Tool</a> (CCS)</li>
                <li><a href="https://gpbprtd.eu.pythonanywhere.com/" target="_blank">Climate Risk Threshold Database</a> (RTD)</li>
                <li><a href="https://www.figma.com/proto/MRIuLeqyVOFGJQwVi0sVAg/PIA-final?node-id=14101-76623&p=f&t=wMUuiwyzr7W56K36-0&scaling=min-zoom&content-scaling=fixed&page-id=14101%3A64991&starting-point-node-id=14101%3A76623" target="_blank">Public Infrastructure Access Tool</a> (PIA)</li>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<hr style='border: 1px solid #ccc;'>", unsafe_allow_html=True)
        st.write('### 📄 Documentation')
        st.markdown("""
        <div class ="sidebar-text">
            The following documentation regarding the GPBP LDT - DE is available:
            <li><a href="https://docs.google.com/presentation/d/19iGMTUGeB7LNRGnFxKTYuRexLW0OjAmn/edit?slide=id.g2e47b9337ae_0_98#slide=id.g2e47b9337ae_0_98" 
                target="_blank">Pitch Deck</a></li>
            <li><a href="https://docs.google.com/document/d/1eoCPpdTx9z5NI2lX20aAFzLC1_kHGVfd/edit?usp=sharing&ouid=107640506223612923418&rtpof=true&sd=true" target="_blank">EIG in the WeBA6</a></li>
            <li><a href="https://docs.google.com/document/d/17LhzOH-EnxfAWaBF8_FHCup8E_fsDe4p0VVfrUG4Aac/edit?usp=sharing" target="_blank">Indicator Methodology</a></li>
            <li><a href="https://docs.google.com/document/d/1IaHR46oQ8gcmZwwIH6LLMGyyl76Cf0nsgvEY0wuf9OM/edit?usp=sharing" target="_blank">Technical Documentation</a></li>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<hr style='border: 1px solid #ccc;'>", unsafe_allow_html=True)
        st.write("### ⚠️ Disclaimer")
        st.markdown(
            """
            <div class="sidebar-text">
                <p>
                    The <strong>GPBP LDT - DE</strong> leverages <strong>Generative AI</strong> to analyze data and suggest region-specific and project-level recommendations.
                </p>
                <p>
                    While we strive to deliver <strong>high-quality and accurate outputs</strong>, AI-generated responses may occasionally contain
                    <strong>inaccuracies, outdated information</strong>, or <strong>unintended biases</strong>. Additionally, due to the probabilistic nature of generative AI, 
                    the system may produce <strong>slightly different recommendations</strong> across sessions—even when provided with similar inputs.
                </p>
                <p>
                    We strongly recommend that users <strong>verify critical information independently</strong> before making decisions based on these outputs.
                </p>
            </div>
        """,
        unsafe_allow_html=True
        )
        st.markdown("<hr style='border: 1px solid #ccc;'>", unsafe_allow_html=True)

        with st.expander("🗄️ Cache Management (GCS)", expanded=False):
            stats = cache_manager.get_cache_stats()
            st.write("**Cache Statistics:**")
            st.write(f"- Total responses: {stats['total_responses']}")
            st.write(f"- English responses: {stats['english_responses']}")
            st.write(f"- Serbian responses: {stats['serbian_responses']}")
            st.write(f"- Cache version: {stats['cache_version']}")
            st.write(f"- GCS Path: `{stats['gcs_path']}`")
            if stats['last_updated']:
                st.write(f"- Last updated: {stats['last_updated'][:19]}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear Cache"):
                    cache_manager.clear_cache()
            with col2:
                if st.button("🔄 Reload Cache"):
                    cache_manager.cache = cache_manager._load_cache()
                    st.success("Cache reloaded from GCS")

def render_language_selection():
    """Renders the language selection radio buttons and returns the language code."""
    languages = {"English": "en", "Serbian": "sr"}
    
    query_params = st.query_params
    current_lang_code = query_params.get("lang", ["en"])[0]
    
    reverse_languages = {v: k for k, v in languages.items()}
    default_language = reverse_languages.get(current_lang_code, "English")
    
    def set_language():
        if "selected_language" in st.session_state:
            new_lang_code = languages[st.session_state["selected_language"]]
            st.query_params["lang"] = new_lang_code

    sel_lang = st.radio(
        "Language",
        options=list(languages.keys()),
        index=list(languages.keys()).index(default_language),
        horizontal=True,
        on_change=set_language,
        key="selected_language",
    )
    return languages[sel_lang]

def render_main_interface(lang: str, regions: list, categories: list):
    """Renders the main UI components like titles, selectors, and buttons."""
    ui_text = UI_TEXT[lang]
    
    st.markdown(f"### {ui_text['app_title']}")
    st.write(ui_text['app_subheader'])
    
    default_region_index = regions.index("Veliko Gradište") if "Veliko Gradište" in regions else 0
    if lang == 'sr' and "Велико Градиште" in regions:
        default_region_index = regions.index("Велико Градиште")
    
    region = st.selectbox(
        ui_text['select_region'],
        regions,
        index=default_region_index,
        key="option_region"
    )
    
    category = st.selectbox(
        ui_text['select_category'],
        categories,
        key="option_category"
    )
    
    st.write(ui_text['region_selected'].format(region=region))
    st.write(ui_text['category_selected'].format(category=category))
    

def render_map_options(years: list, indicators: list):
    """Renders the map options, including year and indicator selection."""
        
    default_year_index = years.index(2024)
    defaul_indicator_index = indicators.index('Nighttime Luminosity (unit: nWatts/(cm2 x sr)')
        
    year = st.selectbox(
            "Year",
            years,
            index=default_year_index,
            key="option_year"
    )
    indicator = st.selectbox(
            "Indicator",
            indicators,
            index=defaul_indicator_index,
            key="option_indicator"
    )
    
    return None
    

def render_scatterplot_options(years: list, indicators_x: list, indicators_y: list):
    """Renders the scatterplot options, including year and indicator selection."""
    
    year = st.selectbox(
        "Year",
        years,
        index=years.index(2024),
        key="option_year_scatterplot"
    )
    
    indicator_x = st.selectbox(
        "Livability Indicator",
        indicators_x,
        index=indicators_x.index('Emissions from all sources (unit: kgCO2e/kg)'),
        key="option_indicator_x"
    )
    
    indicator_y = st.selectbox(
        "Prosperity Indicator",
        indicators_y,
        index=indicators_y.index('Nighttime Luminosity (unit: nWatts/(cm2 x sr)'),
        key="option_indicator_y"
    )
    
    return None

# --- Plotly chart helpers ---
def render_delta_chip(delta: float, pct_delta: float, higher_is_better: bool) -> str:
    if not isinstance(delta, (int, float)):
        return ""
    val = pct_delta if pct_delta == pct_delta else 0  # NaN check
    good = DELTA_THRESHOLDS["good"]
    warn = DELTA_THRESHOLDS["warn"]
    is_positive = val >= 0
    favorable = is_positive if higher_is_better else not is_positive
    mag = abs(val)
    color = CHART_COLORS["region_neutral"]
    if mag >= good:
        color = CHART_COLORS["region_good"] if favorable else CHART_COLORS["region_bad"]
    elif mag >= warn:
        color = CHART_COLORS["region_good"] if favorable else CHART_COLORS["region_bad"]
    arrow = "▲" if is_positive else "▼"
    pct_str = f"{val*100:.1f}%"
    return f"<span style='color:{color}; font-weight:600'>{arrow} {pct_str}</span>"


def render_transparency_badges(latest_year, years_min, years_max, coverage_pct, missing_years) -> None:
    """Render small inline badges: freshness, coverage, and gaps."""
    freshness = f"Data year: {latest_year}" if latest_year else "Data year: n/a"
    coverage = f"Coverage: {int(coverage_pct*100)}%" if coverage_pct is not None else "Coverage: n/a"
    gaps = "Gaps: none" if not missing_years else f"Gaps: {', '.join(str(y) for y in missing_years[:6])}{'…' if len(missing_years) > 6 else ''}"
    st.caption(f"{freshness} • {coverage} • {gaps}")


def render_sources_badges(sources) -> None:
    """Render a compact list of source badges (supports multiple)."""
    if not sources:
        return
    parts = []
    for s in sources:
        label = s.get('label', 'Source')
        url = s.get('url')
        if url:
            parts.append(f"<a href=\"{url}\" target=\"_blank\">{label}</a>")
        else:
            parts.append(label)
    joined = " • ".join(parts)
    st.caption(f"Sources: {joined}", unsafe_allow_html=True)


def chart_latest_comparison_bar(title: str, region_value: float, national_value: float, unit: str, higher_is_better: bool) -> go.Figure:
    region_color = CHART_COLORS["region_good"] if (region_value >= national_value) == higher_is_better else CHART_COLORS["region_bad"]
    fig = go.Figure()
    fig.add_bar(name="Municipality", x=["Municipality"], y=[region_value], marker_color=region_color)
    fig.add_bar(name="National avg", x=["Municipality"], y=[national_value], marker_color=CHART_COLORS["national"])
    fig.update_layout(
        barmode='group',
        height=240,
        margin=dict(l=10, r=10, t=60, b=10),
        showlegend=True,
        legend=dict(
            orientation='h',
            x=0,
            xanchor='left',
            y=1.1,
            yanchor='top',
            bgcolor='rgba(255,255,255,0.85)',
            bordercolor='rgba(0,0,0,0.1)',
            borderwidth=1,
            font=dict(size=11)
        ),
        title=dict(text=title, x=0.01, font=dict(size=14)),
        yaxis_title=unit or "",
    )
    return fig


def chart_trend_sparkline(title: str, regional_df, national_df, value_col: str, unit: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=regional_df['year'], y=regional_df[value_col], mode='lines+markers', name='Municipality', line=dict(color=CHART_COLORS['region_neutral']), marker=dict(size=5)))
    fig.add_trace(go.Scatter(x=national_df['year'], y=national_df[value_col], mode='lines', name='National avg', line=dict(color=CHART_COLORS['national'], dash='dot')))
    # Ensure x-axis ticks are integer years only
    try:
        years = list(regional_df['year'].dropna()) + list(national_df['year'].dropna())
        years_int = sorted({int(y) for y in years})
        xaxis_cfg = dict(tickmode='array', tickvals=years_int, ticktext=[str(y) for y in years_int])
    except Exception:
        xaxis_cfg = {}
    fig.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=True,
        legend=dict(
            orientation='h',
            x=1,
            xanchor='right',
            y=1.15,
            yanchor='top',
            bgcolor='rgba(255,255,255,0.85)',
            bordercolor='rgba(0,0,0,0.1)',
            borderwidth=1,
            font=dict(size=11)
        ),
        title=dict(text=title, x=0.01, font=dict(size=13)),
        xaxis=xaxis_cfg,
        yaxis_title=unit or "",
    )
    return fig


def spacer(px=24):
    st.markdown(f"<div style='height:{px}px'></div>", unsafe_allow_html=True)
    
def remove_unit_suffix(text: str) -> str:
    """
    Removes anything from ' (unit' (case-insensitive) onward from a given string.
    Example: 
        'Accessibility to Health Services (unit: %)' 
        → 'Accessibility to Health Services'
    """
    return re.sub(r'\s*\(unit.*', '', text, flags=re.IGNORECASE).strip()

# Function to normalize names (remove accents and lowercase)
def normalize(text):
    return ''.join(
        c for c in unicodedata.normalize('NFKD', str(text))
        if not unicodedata.combining(c)
    ).lower().strip()
