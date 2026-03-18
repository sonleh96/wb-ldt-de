import base64
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import re
import unicodedata
import numpy as np
import pandas as pd

from src.config import UI_TEXT, CHART_COLORS, DELTA_THRESHOLDS, QUADRANT_COLORS, SPATIAL_AUTOCORR_COLORS, SPATIAL_AUTOCORR_LABELS, SCORE_COLS_DICT, SUB_COLS_DICT
import plotly.graph_objects as go
import plotly.express as px
from src.caching import ResponseCacheManager


def fix_appearance():
    # JS script to force light theme
    detect_theme_js = """
    <script>
    // Always use light theme regardless of system setting
    const theme = "light";

    // send result to Streamlit
    window.parent.postMessage(
        {isDarkMode: false},
        "*"
    );
    </script>
    """

    components.html(detect_theme_js, height=0)

def get_base64_from_image(image: Image.Image) -> str:
    """Converts a PIL Image to a base64 encoded string."""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def render_sidebar(cache_manager: ResponseCacheManager):
    """Renders the sidebar, including logos, about text, and cache admin panel."""

    with st.sidebar:

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
    """Renders the map options (indicator selection only). Year is globally set in sidebar."""
    defaul_indicator_index = indicators.index('Prosperity Score')
    indicator = st.selectbox(
            "Indicator",
            indicators,
            index=defaul_indicator_index,
            key="option_indicator"
    )
    
    return None 

def render_scatterplot_options(years: list, indicators_x: list, indicators_y: list):
    """Renders the scatterplot options (X/Y indicators only). Year is globally set in sidebar."""
    
    indicator_x = st.selectbox(
        "X-axis Indicator",
        indicators_x,
        index=indicators_x.index("Livability Score"),
        key="option_indicator_x"
    )
    
    indicator_y = st.selectbox(
        "Y-axis Indicator",
        indicators_y,
        index=indicators_y.index('Prosperity Score'),
        key="option_indicator_y"
    )
    
    return None

def render_3d_scatterplot_options(years: list):
    """3D scatterplot options (no year control; year is globally set in sidebar)."""
    
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


# --- Plotting Functions ---

def create_3d_scatter(slice_3d, title="Serbia Municipalities: 3D Scatter Plot's Key Pillars"):
    """
    Create 3D scatter plot for composite pillars.
    
    Args:
        slice_3d: DataFrame with Municipality, Livability Score, Infrastructure Score, Prosperity Score
        title: Plot title
        
    Returns:
        plotly figure
    """
    fig = px.scatter_3d(
        slice_3d,
        x='Livability Score', y='Infrastructure Score', z='Prosperity Score',
        hover_data={'Municipality': True,
                    'Infrastructure Score': ':.2f',
                    'Prosperity Score': ':.2f',
                    'Livability Score': ':.2f'},
    )
    
    # Customize marker appearance
    fig.update_traces(
        marker=dict(
            size=10,           # Adjust size (default is usually 6)
            color='gray', # Set color (can use hex '#4682B4', rgb, or name)
            opacity=0.8,      # Optional: adjust transparency
            line=dict(        # Optional: add border
                color='gray',
                width=0.5
            ),
            
        )
    )
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=27), x=0.5, xanchor='center', y=0.9),
        scene=dict(
            xaxis=dict(tickfont=dict(size=17), showline=True, linecolor="black", linewidth=2, 
                      ticks="outside", tickwidth=2, tickcolor="black", range=[0, 100]),
            yaxis=dict(tickfont=dict(size=17), showline=True, linecolor="black", linewidth=2,
                      ticks="outside", tickwidth=2, tickcolor="black", range=[0, 100]),
            zaxis=dict(tickfont=dict(size=17), showline=True, linecolor="black", linewidth=2,
                      ticks="outside", tickwidth=2, tickcolor="black", range=[0, 100]),
            aspectratio=dict(x=1, y=1, z=1),
            aspectmode='manual'
        ),
        showlegend=True,
        legend=dict(
            font=dict(size=20),
            orientation='h',
            yanchor='bottom',
            y=-0.2,
            xanchor='center',
            x=0.5
        ),
        height=1000, width=1500
    )
    
    return fig


def highlight_municipality_3d(fig, sel, name):
    """
    Add highlighted municipality to 3D scatter plot.
    
    Args:
        fig: Existing plotly figure
        sel: DataFrame slice for selected municipality
        name: Municipality name
        
    Returns:
        Modified figure
    """
    sel_muni = sel[sel["Municipality"] == name]
    sel_else = sel[sel["Municipality"] != name]
    district_name = sel_muni["District"].reset_index(drop=True).iloc[0]
    
    customdata1 = sel_muni[["Municipality", "Livability Score", "Infrastructure Score", "Prosperity Score"]]
    fig.add_trace(
        go.Scatter3d(
            x=sel_muni['Livability Score'],
            y=sel_muni['Infrastructure Score'],
            z=sel_muni['Prosperity Score'],
            mode='markers',
            marker=dict(size=10, color='crimson'),
            name=f"Highlighted: {name}",
            showlegend=True,
            customdata=customdata1,
            hovertemplate=(
                "Municipality: %{customdata[0]}<br>"
                "Livability Score: %{x:.2f}<br>"
                "Infrastructure Score: %{y:.2f}<br>"
                "Prosperity Score: %{z:.2f}<extra></extra>"
            )
        )
    )
    
    customdata2 = sel_else[["Municipality", "Livability Score", "Infrastructure Score", "Prosperity Score"]]
    fig.add_trace(
        go.Scatter3d(
            x=sel_else['Livability Score'],
            y=sel_else['Infrastructure Score'],
            z=sel_else['Prosperity Score'],
            mode='markers',
            marker=dict(size=10, color='orange'),
            showlegend=True,
            name=f"Other Municipalities in {district_name}",
            customdata=customdata2,
            hovertemplate=(
                "Municipality: %{customdata[0]}<br>"
                "Livability Score: %{x:.2f}<br>"
                "Infrastructure Score: %{y:.2f}<br>"
                "Prosperity Score: %{z:.2f}<extra></extra>"
            )
        )
    )
    
    return fig

def render_waterfall_chart_options(score_names, score_type="main"):
    if score_type == "main":
        default_idx = score_names.index('Prosperity Score') if 'Prosperity Score' in score_names else 0
        st.selectbox(
            "Choose a score to analyze:",
            score_names,
            index=default_idx,
            key="option_score_name_waterfall")
    if score_type == "sub":
        default_idx = score_names.index('Digitalization Score') if 'Digitalization Score' in score_names else 0
        st.selectbox(
            "Choose a subscore to analyze:",
            score_names,
            index=default_idx,
            key="option_subscore_name_waterfall")
    
    return None


def create_waterfall_chart(slice_waterfall, score_type="main", score_col_override=None):
    """Create a sorted horizontal diverging bar chart showing component contributions."""
    if score_col_override:
        score_col = score_col_override
        if score_col in SCORE_COLS_DICT:
            sub_cols = SCORE_COLS_DICT[score_col]
        else:
            sub_cols = SUB_COLS_DICT[score_col]
    elif score_type == "main":
        score_col = st.session_state.option_score_name_waterfall
        sub_cols = SCORE_COLS_DICT[score_col]
    elif score_type == "sub":
        score_col = st.session_state.option_subscore_name_waterfall
        sub_cols = SUB_COLS_DICT[score_col]
    else:
        return None
    
    weights = {c: 1/len(sub_cols) for c in sub_cols}

    df = slice_waterfall.copy()
    current_year = st.session_state.get("selected_year", 2024)
    try:
        if "year" in df.columns:
            df_year = df[df["year"] == current_year]
            if not df_year.empty:
                df = df_year
    except Exception:
        pass

    muni_input = str(st.session_state.get('highlight_municipality', "Veliko Gradište") or "").strip()
    try:
        available = list(df["ENGLISH_NAME"].dropna().unique())
    except Exception:
        available = []
    lookup = {normalize(name): name for name in available}
    key = normalize(muni_input)
    municipality = lookup.get(key)
    if not municipality and key:
        candidates = [orig for norm, orig in lookup.items() if key in norm]
        if len(candidates) == 1:
            municipality = candidates[0]
        elif len(candidates) > 1:
            municipality = min(candidates, key=len)
    if not municipality:
        municipality = "Veliko Gradište" if "Veliko Gradište" in available else (available[0] if available else None)
    if not municipality:
        return None

    row_df = df.loc[df["ENGLISH_NAME"] == municipality, sub_cols].head(1)
    if row_df.empty:
        try:
            any_year_df = slice_waterfall.loc[slice_waterfall["ENGLISH_NAME"] == municipality, sub_cols].head(1)
            if any_year_df.empty:
                return None
            row_df = any_year_df
        except Exception:
            return None
    row = row_df.iloc[0]
    
    baseline_sub = df[sub_cols].mean()
    baseline_total = np.sum([weights[c]*baseline_sub[c] for c in sub_cols])
    
    muni_sub = row[sub_cols]
    actual_total = np.sum([weights[c]*muni_sub[c] for c in sub_cols])
    
    diff = muni_sub - baseline_sub
    contrib = pd.Series({c: weights[c]*diff[c] for c in sub_cols})
    total_diff = contrib.sum()
    
    contrib_sorted = contrib.reindex(contrib.abs().sort_values(ascending=True).index)
    
    component_names = [name.replace(' Score', '') for name in contrib_sorted.index]
    values = contrib_sorted.values
    colors = ['#54a24b' if v >= 0 else '#e45756' for v in values]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=component_names,
        x=values,
        orientation='h',
        marker=dict(color=colors),
        text=[f"{v:+.2f}" for v in values],
        textposition='outside',
        textfont=dict(size=14, color='black'),
        hovertemplate="<b>%{y}</b><br>Contribution: %{x:+.2f} points<extra></extra>"
    ))
    
    fig.add_vline(x=0, line_width=2, line_color="gray", line_dash="solid")
    
    max_abs = max(abs(values.min()), abs(values.max()), 1) * 1.4
    
    score_label = score_col.replace(' Score', '')
    diff_sign = "+" if total_diff >= 0 else ""
    
    title_text = (
        f"<b>{municipality} {score_label} Score: {actual_total:.1f}</b><br>"
        f"<span style='font-size:16px'>Country average: {baseline_total:.1f} | "
        f"Difference: {diff_sign}{total_diff:.1f} points</span>"
    )
    
    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=20),
            x=0.5,
            xanchor='center',
            y=0.95
        ),
        xaxis=dict(
            title="Contribution to difference from country average (score points)",
            title_font=dict(size=14, color="black"),
            tickfont=dict(size=12, color="black"),
            range=[-max_abs, max_abs],
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='gray',
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=14, color="black"),
            automargin=True
        ),
        showlegend=False,
        margin=dict(l=20, r=40, t=100, b=60),
        height=max(350, 80 + len(sub_cols) * 50),
        plot_bgcolor='white',
        annotations=[
            dict(
                x=-max_abs * 0.5,
                y=1.02,
                xref="x",
                yref="paper",
                text="← Below average",
                showarrow=False,
                font=dict(size=12, color="#e45756"),
                xanchor="center"
            ),
            dict(
                x=max_abs * 0.5,
                y=1.02,
                xref="x",
                yref="paper",
                text="Above average →",
                showarrow=False,
                font=dict(size=12, color="#54a24b"),
                xanchor="center"
            )
        ]
    )
    
    return fig


def create_2d_scatter_with_quadrants(slice_scatter, x_score_name, y_score_name, 
                                      indicator_x, indicator_y, year, custom_data,
                                      x_is_score=False, y_is_score=False):
    """
    Create 2D scatter plot with quadrant shading and labels.
    
    Args:
        slice_scatter: DataFrame with scores
        x_score_name: X-axis score name
        y_score_name: Y-axis score name
        indicator_x: X-axis indicator full name
        indicator_y: Y-axis indicator full name
        year: Year for title
        custom_data: Custom data for hover
        x_is_score: If True, indicator_x is already a score
        y_is_score: If True, indicator_y is already a score
        
    Returns:
        plotly figure
    """
    x_min, x_max = 0, 100
    y_min, y_max = 0, 100
    x_mid = (x_min + x_max) / 2
    y_mid = (y_min + y_max) / 2
    
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
    
    # Set explicit axis ranges
    fig.update_xaxes(range=[x_min, x_max])
    fig.update_yaxes(range=[y_min, y_max])

    # Add quadrant shading
    fig.add_shape(type="rect", xref="x", yref="y",
                x0=x_mid, x1=x_max, y0=y_mid, y1=y_max,
                fillcolor=QUADRANT_COLORS["high_high"], opacity=0.10, line_width=0, layer="below")

    fig.add_shape(type="rect", xref="x", yref="y",
                x0=x_min, x1=x_mid, y0=y_mid, y1=y_max,
                fillcolor=QUADRANT_COLORS["high_low"], opacity=0.10, line_width=0, layer="below")

    fig.add_shape(type="rect", xref="x", yref="y",
                x0=x_mid, x1=x_max, y0=y_min, y1=y_mid,
                fillcolor=QUADRANT_COLORS["low_high"], opacity=0.10, line_width=0, layer="below")

    fig.add_shape(type="rect", xref="x", yref="y",
                x0=x_min, x1=x_mid, y0=y_min, y1=y_mid,
                fillcolor=QUADRANT_COLORS["low_low"], opacity=0.10, line_width=0, layer="below")
    
    # Add quadrant labels
    # fig.add_annotation(x=(x_mid + x_max)/2, y=(y_mid + y_max)/2,
    #                 text="High Prosperity and Livability", showarrow=False, font=dict(size=20, color="green"))
    # fig.add_annotation(x=(x_min + x_mid)/2, y=(y_mid + y_max)/2,
    #                 text="High Prosperity, Low Livability", showarrow=False, font=dict(size=20, color="#a67c00"))
    # fig.add_annotation(x=(x_mid + x_max)/2, y=(y_min + y_mid)/2,
    #                 text="Low Prosperity, High Livability", showarrow=False, font=dict(size=20, color="#a67c00"))
    # fig.add_annotation(x=(x_min + x_mid)/2, y=(y_min + y_mid)/2,
    #                 text="Low Prosperity and Livability", showarrow=False, font=dict(size=20, color="red"))

    # Add crosshair lines
    fig.add_vline(x=x_mid, line_width=2, line_dash="dash", line_color="black")
    fig.add_hline(y=y_mid, line_width=2, line_dash="dash", line_color="black")

    # Build hover template dynamically based on custom_data columns
    # custom_data columns are in the order they were added (deduplicated)
    custom_data_cols = list(custom_data.columns)
    hover_parts = [f"<b>%{{customdata[0]}}</b>"]  # ENGLISH_NAME is always first
    
    # Find indices for each piece of data we want to show
    x_score_idx = custom_data_cols.index(x_score_name) if x_score_name in custom_data_cols else None
    if x_score_idx is not None:
        hover_parts.append(f"{x_score_name}: %{{customdata[{x_score_idx}]:.2f}}")
        
    y_score_idx = custom_data_cols.index(y_score_name) if y_score_name in custom_data_cols else None
    if y_score_idx is not None:
        hover_parts.append(f"{y_score_name}: %{{customdata[{y_score_idx}]:.2f}}")
    
    # Only show indicator values if they're different from scores
    if not x_is_score:
        indicator_x_idx = custom_data_cols.index(indicator_x) if indicator_x in custom_data_cols else None
        if indicator_x_idx is not None:
            hover_parts.append(f"{indicator_x}: %{{customdata[{indicator_x_idx}]:.2f}}")
    
    if not y_is_score:
        indicator_y_idx = custom_data_cols.index(indicator_y) if indicator_y in custom_data_cols else None
        if indicator_y_idx is not None:
            hover_parts.append(f"{indicator_y}: %{{customdata[{indicator_y_idx}]:.2f}}")
    
    hovertemplate = "<br>".join(hover_parts) + "<extra></extra>"
    
    fig.update_traces(
        hovertemplate=hovertemplate,
        marker=dict(color='black')
    )
    
    # Format axis titles - don't add "Score" if it's already in the name
    x_axis_title = x_score_name if "Score" in x_score_name else f'{x_score_name} Score'
    y_axis_title = y_score_name if "Score" in y_score_name else f'{y_score_name} Score'
    
    fig.update_layout(
        title=dict(text=f"{y_score_name} vs {x_score_name} in Serbia, {year}",
                font=dict(size=27), x=0.5, xanchor='center'),
        xaxis_title=x_axis_title,
        yaxis_title=y_axis_title,
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
    
    return fig


def highlight_municipality_2d(fig, sel, x_score_name, y_score_name, indicator_x, indicator_y, name,
                              x_is_score=False, y_is_score=False):
    """
    Add highlighted municipality and other municipalities in the same district to 2D scatter plot.
    
    Args:
        fig: Existing plotly figure
        sel: DataFrame slice for all municipalities in the district
        x_score_name: X-axis score name
        y_score_name: Y-axis score name
        indicator_x: X-axis indicator name
        indicator_y: Y-axis indicator name
        name: Municipality name to highlight
        x_is_score: If True, indicator_x is already a score
        y_is_score: If True, indicator_y is already a score
        
    Returns:
        Modified figure
    """
    # Split into selected municipality and others in the same district
    sel_muni = sel[sel["ENGLISH_NAME"] == name]
    sel_else = sel[sel["ENGLISH_NAME"] != name]
    district_name = sel_muni["NAME_1"].reset_index(drop=True).iloc[0]
    
    # Build custom_data columns avoiding duplicates
    custom_data_cols = ['ENGLISH_NAME']
    for col in [x_score_name, y_score_name, indicator_x, indicator_y]:
        if col not in custom_data_cols:
            custom_data_cols.append(col)
    
    # Build hover template dynamically
    hover_parts = [f"<b>%{{customdata[0]}}</b>"]  # ENGLISH_NAME is always first
    
    x_score_idx = custom_data_cols.index(x_score_name) if x_score_name in custom_data_cols else None
    if x_score_idx is not None:
        hover_parts.append(f"{x_score_name}: %{{customdata[{x_score_idx}]:.2f}}")
        
    y_score_idx = custom_data_cols.index(y_score_name) if y_score_name in custom_data_cols else None
    if y_score_idx is not None:
        hover_parts.append(f"{y_score_name}: %{{customdata[{y_score_idx}]:.2f}}")
    
    # Only show indicator values if they're different from scores
    if not x_is_score:
        indicator_x_idx = custom_data_cols.index(indicator_x) if indicator_x in custom_data_cols else None
        if indicator_x_idx is not None:
            hover_parts.append(f"{indicator_x}: %{{customdata[{indicator_x_idx}]:.2f}}")
    
    if not y_is_score:
        indicator_y_idx = custom_data_cols.index(indicator_y) if indicator_y in custom_data_cols else None
        if indicator_y_idx is not None:
            hover_parts.append(f"{indicator_y}: %{{customdata[{indicator_y_idx}]:.2f}}")
    
    hovertemplate = "<br>".join(hover_parts) + "<extra></extra>"
    
    # Add trace for the highlighted municipality (crimson)
    customdata_muni = sel_muni[custom_data_cols]
    fig.add_trace(
        go.Scatter(
            x=sel_muni[x_score_name],
            y=sel_muni[y_score_name],
            mode="markers+text",
            text=sel_muni["ENGLISH_NAME"],
            textposition="top center",
            name=f"Highlighted: {name}",
            marker=dict(
                symbol="diamond",
                size=20,
                line=dict(width=2, color="white"),
                color="crimson"
            ),
            customdata=customdata_muni,
            hovertemplate=hovertemplate,
            showlegend=True
        )
    )
    
    # Add trace for other municipalities in the same district (orange)
    if not sel_else.empty:
        customdata_else = sel_else[custom_data_cols]
        fig.add_trace(
            go.Scatter(
                x=sel_else[x_score_name],
                y=sel_else[y_score_name],
                mode="markers",
                name=f"Other Municipalities in {district_name}",
                marker=dict(
                    symbol="circle",
                    size=15,
                    line=dict(width=2, color="white"),
                    color="orange"
                ),
                customdata=customdata_else,
                hovertemplate=hovertemplate,
                showlegend=True
            )
        )
    
    return fig


def get_choropleth_labels(indicator):
    """
    Get labels dictionary for choropleth based on indicator type.
    
    Args:
        indicator: Indicator name
        
    Returns:
        Dictionary of labels
    """
    if "Score" not in indicator:
        return {
            "NAME_1": "District",
            "ENGLISH_NAME": "Municipality",
            indicator: f"{indicator}", 
            f'{indicator}_score': f'{remove_unit_suffix(indicator)} Score'
        }
    else:
        return {
            "NAME_1": "District",
            "ENGLISH_NAME": "Municipality",
            indicator: f"{indicator}"
        }


def create_choropleth_map(slice_choropleth, geojson_data, indicator, labels, year, opacity=0.7):
    """
    Create choropleth mapbox with proper styling.
    
    Args:
        slice_choropleth: GeoDataFrame with scores
        geojson_data: GeoJSON data
        indicator: Indicator name
        labels: Labels dictionary
        year: Year for title
        opacity: Map opacity
        
    Returns:
        plotly figure
    """
    fig = px.choropleth_mapbox(
        slice_choropleth,
        geojson=geojson_data,
        locations='ENGLISH_NAME',
        featureidkey='properties.ENGLISH_NAME',
        color=f'{indicator}_score' if "Score" not in indicator else indicator,
        color_continuous_scale="RdYlGn",
        range_color=(0, 100),
        hover_data=['ENGLISH_NAME', indicator],
        labels=labels,
        title=f'{remove_unit_suffix(indicator)} in Serbia, {year}',
        mapbox_style="carto-positron",
        center={"lat": 44.0, "lon": 21.0},
        zoom=6.5,
        opacity=opacity,
        width=1000,
        height=1000
    )
    
    fig.update_layout(
        margin={"r":0,"t":40,"l":0,"b":0},
        coloraxis_colorbar_title_text=f'{remove_unit_suffix(indicator)} Score' if "Score" not in indicator else remove_unit_suffix(indicator),
        coloraxis_colorbar_title_font=dict(size=15, color="black"),
        title=dict(text=f'{remove_unit_suffix(indicator)} in Serbia, {year}',
                   font=dict(size=30, color="black")),
    )
    
    return fig


def highlight_municipality_choropleth(fig, sel, muni_name):
    """
    Add boundary outline to choropleth for highlighted municipality.
    
    Args:
        fig: Existing plotly figure
        sel: GeoDataFrame slice for selected municipality
        
    Returns:
        Modified figure
    """
    muni_geom = sel[sel["ENGLISH_NAME"] == muni_name].geometry.iloc[0]
    other_geom = sel[sel["ENGLISH_NAME"] != muni_name].reset_index(drop=True).geometry
    
    # Handle both Polygon and MultiPolygon
    # if geom.geom_type == 'Polygon':
    #     coords = list(geom.exterior.coords)
    #     lons, lats = zip(*coords)
    #     fig.add_trace(
    #         go.Scattermapbox(
    #             lon=lons,
    #             lat=lats,
    #             mode='lines',
    #             line=dict(width=3, color='black'),
    #             showlegend=False,
    #             hoverinfo='skip'
    #         )
    #     )
    # elif geom.geom_type == 'MultiPolygon':
    
    for i in range(len(other_geom)):
        for polygon in other_geom.iloc[i].geoms:
            coords = list(polygon.exterior.coords)
            lons, lats = zip(*coords)
            fig.add_trace(
                go.Scattermapbox(
                    lon=lons,
                    lat=lats,
                    mode='lines',
                    line=dict(width=4, color='orange'),
                    showlegend=False,
                    hoverinfo='skip'
                )
            )
            
    for polygon in muni_geom.geoms:
        coords = list(polygon.exterior.coords)
        lons, lats = zip(*coords)
        fig.add_trace(
                go.Scattermapbox(
                    lon=lons,
                    lat=lats,
                    mode='lines',
                    line=dict(width=3, color='red'),
                    showlegend=False,
                    hoverinfo='skip'
            )
        )
        
    
    return fig


def create_spatial_autocorr_map(slice_choropleth, geojson_data, indicator, year):
    """
    Create spatial autocorrelation choropleth map.
    
    Args:
        slice_choropleth: GeoDataFrame with cluster labels
        geojson_data: GeoJSON data
        indicator: Indicator name
        year: Year for title
        
    Returns:
        plotly figure
    """
    category_order = {"cl": SPATIAL_AUTOCORR_LABELS}
    color_map = SPATIAL_AUTOCORR_COLORS
    
    fig = px.choropleth_mapbox(
        slice_choropleth,
        geojson=geojson_data,
        locations="ENGLISH_NAME",
        featureidkey="properties.ENGLISH_NAME",
        color="cl",
        category_orders=category_order,
        color_discrete_map=color_map,
        hover_data=["ENGLISH_NAME", "cl"],
        labels={"ENGLISH_NAME": "Municipality", "cl": "Cluster Type"},
        mapbox_style="carto-positron",
        center={"lat": 44.0, "lon": 21.0},
        zoom=6.5,
        opacity=0.7,
    )
    
    fig.update_traces(marker_line_width=0.5, marker_line_color="white")
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        legend_title_text="Cluster Type",
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.8,
            xanchor="left",
            x=0.6,
            bgcolor="rgba(255,255,255,0.7)",
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
    
    return fig


# def render_spatial_metrics(slice_choropleth, global_significance, region_local_significance):
#     """
#     Render the three metrics columns for spatial analysis.
    
#     Args:
#         slice_choropleth: GeoDataFrame
#         global_significance: Global Moran's I significance
#         region_local_significance: % of municipalities with significant local autocorrelation
#     """
#     col1, col2, col3 = st.columns(3)
#     col1.metric("Municipalities", len(slice_choropleth))
#     col2.metric("Global Spatial Autocorrelation", global_significance)
#     col3.metric("Municipalities with Significant Local Spatial Autocorrelation", f'{region_local_significance}%')

def render_spatial_metrics(slice_choropleth, sel, chosen_district):
    """
    Render the three metrics columns for spatial analysis.
    
    Args:
        slice_choropleth: GeoDataFrame
        global_significance: Global Moran's I significance
        region_local_significance: % of municipalities with significant local autocorrelation
    """
    col1, col2, col3 = st.columns(3)
    
    col1.metric("Associated District", chosen_district)
    col2.metric("Number of Municipalities in District", len(sel["ENGLISH_NAME"].unique()))
    col3.metric("Total number of Municipalities", len(slice_choropleth))
    
    st.text("")
    st.text("") 
    st.text("")