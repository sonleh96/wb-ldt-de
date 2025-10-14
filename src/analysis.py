from typing import List, Tuple, Dict
import pandas as pd
import streamlit as st

from src.config import CATEGORY_INDICATOR_DICT

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
    
    code_list = df_filtered['indicator_name'].tolist()
    name_list = df_filtered['indicator_name_full'].tolist()
    desc_list = df_filtered['indicator_description'].tolist()
    
    for i, name in enumerate(name_list):
        response_content += f"""{i+1}. **{name}**: {desc_list[i]}\n\n"""
        
    code_name_dict = dict(zip(code_list, name_list))
    
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
