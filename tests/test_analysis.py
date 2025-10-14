import pandas as pd
import pytest
from src.analysis import (
    extract_regional_data,
    extract_national_data,
    get_indicator_analysis,
    prepare_regional_analysis_data,
    filter_projects,
)

@pytest.fixture
def sample_df_indicators():
    data = {
        'ENGLISH_NAME': ['Region A', 'Region A', 'Region B'],
        'year': [2020, 2021, 2020],
        'indicator_1': [10, 12, 20],
        'indicator_2': [100, 110, 200]
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_df_indicatorlist():
    data = {
        'indicator_name_full': ['Indicator One Full', 'Indicator Two Full'],
        'indicator_name': ['indicator_1', 'indicator_2'],
        'indicator_description': ['Desc 1', 'Desc 2']
    }
    return pd.DataFrame(data)

def test_extract_regional_data(sample_df_indicators):
    result = extract_regional_data(sample_df_indicators, 'Region A', ['indicator_1', 'year'])
    assert len(result) == 2
    assert 'indicator_1' in result.columns
    assert 'year' in result.columns
    assert result['indicator_1'].tolist() == [10, 12]

def test_extract_national_data(sample_df_indicators):
    # This function expects averages, so we'll mimic that structure
    avg_df = pd.DataFrame({'year': [2020, 2021], 'indicator_1': [15, 12]})
    result = extract_national_data(avg_df, ['indicator_1', 'year'])
    assert len(result) == 2
    assert 'indicator_1' in result.columns

def test_get_indicator_analysis(sample_df_indicatorlist, mocker):
    # Mock the config dictionary
    mocker.patch('src.analysis.CATEGORY_INDICATOR_DICT', {'Test Category': ['Indicator One Full']})
    
    text, code_list, code_name_dict = get_indicator_analysis(sample_df_indicatorlist, 'Test Category')
    
    assert "Here is the outline of the indicators relevant to Test Category" in text
    assert "1. **Indicator One Full**: Desc 1" in text
    assert code_list == ['indicator_1']
    assert code_name_dict == {'indicator_1': 'Indicator One Full'}

def test_prepare_regional_analysis_data(sample_df_indicators):
    avg_df = pd.DataFrame({'year': [2020, 2021], 'indicator_1': [15.0, 12.0], 'ENGLISH_NAME':['x','y']})
    
    result = prepare_regional_analysis_data(
        sample_df_indicators, 
        avg_df, 
        'Region A', 
        ['indicator_1'], 
        {'indicator_1': 'Indicator One Full'}
    )
    
    assert "**Indicator One Full**" in result
    assert "2020: 10.00 – Region A | 15.00 – National avg" in result
    assert "2021: 12.00 – Region A | 12.00 – National avg" in result

@pytest.fixture
def sample_df_projects():
    data = {
        'Investment Sector': ['Environment', 'Health', 'Environment'],
        'Project Description': ['About air quality', 'A hospital project', 'About water'],
        'Status': ['Completed', 'Preparation', 'Completed']
    }
    return pd.DataFrame(data)

def test_filter_projects(sample_df_projects):
    result = filter_projects(sample_df_projects, 'Environment')
    assert len(result) == 1
    assert result.iloc[0]['Project Description'] == 'About air quality'

def test_filter_projects_sustainable_transport(sample_df_projects):
    # Add a transport project for testing this specific case
    sample_df_projects.loc[3] = ['Sustainable Transport', 'A road project', 'Preparation']
    result = filter_projects(sample_df_projects, 'Sustainable Transport')
    assert len(result) == 0 # Should filter out 'Preparation' status
