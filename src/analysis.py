from typing import List, Tuple, Dict
import pandas as pd
import streamlit as st
import numpy as np
import difflib

from src.config import CATEGORY_INDICATOR_DICT, INDICATOR_HIGHER_IS_BETTER
from src.ui import normalize

@st.cache_data
def extract_regional_data(df: pd.DataFrame, region: str, relevant_columns: List[str]) -> pd.DataFrame:
    """
    Filters the DataFrame for a specific region and columns.
    """
    valid_columns = [col for col in relevant_columns if col in df.columns]
    return df.loc[df["ENGLISH_NAME"] == region, valid_columns]

@st.cache_data
def extract_national_data(df: pd.DataFrame, relevant_columns: List[str]) -> pd.DataFrame:
    """
    Extracts national average data for specified columns.
    """
    valid_columns = [col for col in relevant_columns if col in df.columns]
    return df[valid_columns]

def get_indicator_analysis(
    df_indicatorlist: pd.DataFrame, 
    category: str
) -> Tuple[str, List, Dict]:
    """
    Generates the text describing relevant indicators for a category.
    """
    relevant_indicators = CATEGORY_INDICATOR_DICT.get(category, [])
    
    df_filtered = df_indicatorlist[df_indicatorlist['indicator_name_full'].isin(relevant_indicators)]
    
    response_content = f"Here is the outline of the indicators relevant to {category}, ordered by their relevance:\n\n"
    
    # Now that df_indicators uses full names as columns, code_list should contain full names
    code_list = df_filtered['indicator_name_full'].tolist()
    name_list = df_filtered['indicator_name_full'].tolist()
    desc_list = df_filtered['indicator_description'].tolist()
    
    for i, name in enumerate(name_list):
        response_content += f"""{i+1}. **{name}**: {desc_list[i]}\n\n"""
        
    # code_name_dict maps full names to themselves (identity mapping)
    code_name_dict = dict(zip(code_list, name_list))
    # print(code_name_dict)
    
    return response_content, code_list, code_name_dict

def prepare_regional_analysis_data(
    df_indicators: pd.DataFrame,
    averages_df: pd.DataFrame,
    region_name: str,
    code_list: List[str],
    code_name_dict: Dict[str, str]
) -> str:
    """
    Prepares the data comparison string for the regional analysis narrative.
    """
    cols = code_list + ['ENGLISH_NAME', 'year']
    
    regional_df = extract_regional_data(df_indicators, region_name, cols)
    regional_df = regional_df.rename(columns=code_name_dict)
    
    national_df = extract_national_data(averages_df.reset_index(), cols)
    national_df = national_df.rename(columns=code_name_dict)

    lines = []
    for col_name in regional_df.columns.drop(['ENGLISH_NAME', "year"]):
        lines.append(f"**{col_name}**")
        for _, r_row in regional_df.iterrows():
            year = int(r_row["year"])
            region_val = r_row[col_name]
            nat_row = national_df[national_df["year"] == year]
            if not nat_row.empty:
                nat_val = nat_row[col_name].iloc[0]
                region_name_display = r_row["ENGLISH_NAME"]
                lines.append(
                    f"{year}: {region_val:.2f} – {region_name_display} | {nat_val:.2f} – National avg"
                )
        lines.append("")
    return "\n".join(lines)


@st.cache_data
def get_indicator_series(
    df_indicators: pd.DataFrame,
    averages_df: pd.DataFrame,
    region_name: str,
    indicator_code_to_full_name: Dict[str, str],
    indicator_code: str,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """
    Returns muni and national series for a single indicator, plus latest-year values and deltas.
    """
    full_name = indicator_code_to_full_name.get(indicator_code, indicator_code)
    cols = [indicator_code, 'ENGLISH_NAME', 'year']
    regional_df = extract_regional_data(df_indicators, region_name, cols).rename(columns={indicator_code: full_name})
    national_df = extract_national_data(averages_df.reset_index(), cols).rename(columns={indicator_code: full_name})

    if regional_df.empty or national_df.empty:
        return regional_df, national_df, {
            "latest_region": float('nan'), 
            "latest_national": float('nan'), 
            "delta": float('nan'), 
            "pct_delta": float('nan'), 
            "higher_is_better": INDICATOR_HIGHER_IS_BETTER.get(full_name, True),
            "full_name": full_name,
            "latest_year": float('nan'),
            "years_available": 0,
            "years_min": None,
            "year_max": None,
            "missing_years": [],
            "coverage_pct": 0.0,
        }

    # Coverage / freshness stats
    years_series = regional_df['year'].dropna().astype(int)
    latest_year = int(years_series.max()) if not years_series.empty else None
    latest_year = int(regional_df['year'].max())
    r_latest = regional_df[regional_df['year'] == latest_year][full_name].iloc[0]
    n_latest_row = national_df[national_df['year'] == latest_year]
    n_latest = n_latest_row[full_name].iloc[0] if not n_latest_row.empty else float('nan')

    delta = r_latest - n_latest if pd.notna(r_latest) and pd.notna(n_latest) else float('nan')
    pct_delta = (delta / n_latest) if pd.notna(delta) and n_latest not in (0, float('nan')) else float('nan')
    years_min = int(years_series.min()) if not years_series.empty else None
    years_max = int(years_series.max()) if not years_series.empty else None
    full_range = list(range(years_min, years_max + 1)) if years_min is not None and years_max is not None else []
    available_years = sorted(set(years_series.tolist())) if not years_series.empty else []
    missing_years = [y for y in full_range if y not in available_years]
    coverage_pct = (len(available_years) / len(full_range)) if full_range else 0.0
    
    return regional_df, national_df, {
        "latest_region": r_latest,
        "latest_national": n_latest,
        "delta": delta,
        "pct_delta": pct_delta,
        "higher_is_better": INDICATOR_HIGHER_IS_BETTER.get(full_name, True),
        "full_name": full_name,
        "latest_year": latest_year,
        "years_available": len(available_years),
        "years_min": years_min,
        "years_max": years_max,
        "missing_years": missing_years,
        "coverage_pct": coverage_pct,
    }

def filter_projects(df_projects: pd.DataFrame, subcategory: str) -> pd.DataFrame:
    """
    Filters the projects DataFrame based on the selected subcategory.
    """
    df_filtered = df_projects[df_projects['Investment Sector'].str.contains(subcategory, case=False, na=False)]
    
    if subcategory == 'Environment':
        df_filtered = df_filtered[df_filtered['Project Description'].str.contains("air | air pollution | emissions | co2 | CO2", na=False)]
    
    if subcategory == 'Sustainable Transport':
        df_filtered = df_filtered[df_filtered['Status'] != 'Preparation']
        
    return df_filtered

def calculate_indicator_score(indicator: str, df_indicators: pd.DataFrame) -> float:
    """
    Calculates the score for a single indicator.
    """
    
    higher_is_better = INDICATOR_HIGHER_IS_BETTER.get(indicator, True)
    
    if higher_is_better:
        return np.round(df_indicators[indicator].rank(pct=True) * 100, 2)
    else:
        return np.round(100 - df_indicators[indicator].rank(pct=True) * 100, 2)


def prepare_3d_scatter_data(df_scatter: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    Prepare data for 3D scatterplot.
    
    Args:
        df_scatter: DataFrame with indicator data
        year: Year to filter
        
    Returns:
        Filtered and renamed DataFrame for 3D plotting
    """
    slice_3d = df_scatter[["NAME_1", 'ENGLISH_NAME', 'year', 'Livability Score', 'Infrastructure Score', 'Prosperity Score']]
    slice_3d = slice_3d[slice_3d['year'] == year]
    slice_3d = slice_3d.rename({'NAME_1': 'District', 'ENGLISH_NAME': 'Municipality'}, axis=1)
    return slice_3d


def prepare_scatter_data(df_scatter: pd.DataFrame, indicator_x: str, indicator_y: str, 
                         year: int, x_score_name: str, y_score_name: str,
                         x_is_score: bool = False, y_is_score: bool = False) -> pd.DataFrame:
    """
    Prepare data for 2D scatterplot with score calculations.
    
    Args:
        df_scatter: DataFrame with indicator data
        indicator_x: X-axis indicator name
        indicator_y: Y-axis indicator name
        year: Year to filter
        x_score_name: Name for X score column
        y_score_name: Name for Y score column
        x_is_score: If True, indicator_x is already a score (don't calculate)
        y_is_score: If True, indicator_y is already a score (don't calculate)
        
    Returns:
        DataFrame with calculated scores
    """
    slice_scatter = df_scatter[['ENGLISH_NAME', 'NAME_1', 'year', indicator_x, indicator_y]]
    slice_scatter = slice_scatter[slice_scatter['year'] == year]
    
    # Only calculate scores if the indicator is not already a score column
    if not x_is_score:
        slice_scatter[x_score_name] = calculate_indicator_score(indicator_x, df_scatter)
    if not y_is_score:
        slice_scatter[y_score_name] = calculate_indicator_score(indicator_y, df_scatter)
    
    return slice_scatter


def prepare_choropleth_data(df_choropleth: pd.DataFrame, indicator: str, year: int) -> Tuple[pd.DataFrame, dict]:
    """
    Prepare data for choropleth with score calculations.
    
    Args:
        df_choropleth: GeoDataFrame with indicator data
        indicator: Indicator name
        year: Year to filter
        
    Returns:
        Tuple of (slice_choropleth with scores, geojson_data)
    """
    slice_choropleth = df_choropleth[['NAME_1', 'ENGLISH_NAME', 'year', indicator, 'geometry']]
    slice_choropleth = slice_choropleth[slice_choropleth['year'] == year]
    slice_choropleth[f'{indicator}_score'] = calculate_indicator_score(indicator, slice_choropleth)
    geojson_data = slice_choropleth.__geo_interface__
    
    return slice_choropleth, geojson_data


def find_municipality_match(input_text: str, name_lookup: Dict[str, str]) -> List[str]:
    """
    Find municipality matches using fuzzy matching.
    
    Args:
        input_text: User input text
        name_lookup: Dictionary mapping normalized names to actual names
        
    Returns:
        List of matched municipality names
    """
    norm_input = normalize(input_text)
    
    # 1️⃣ Find substring matches
    matches = [v for k, v in name_lookup.items() if norm_input in k]
    
    # 2️⃣ If no substring matches, find close fuzzy matches
    if not matches:
        all_norms = list(name_lookup.keys())
        close_keys = difflib.get_close_matches(norm_input, all_norms, n=3, cutoff=0.6)
        matches = [name_lookup[k] for k in close_keys]
    
    return matches
    
