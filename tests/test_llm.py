import pytest
from unittest.mock import MagicMock
from src.llm import (
    translate_en_to_sr,
    get_regional_narrative,
    get_background_research,
    get_initial_recommendations,
    get_final_projects
)

@pytest.fixture
def mock_openai_client():
    """Fixture to create a mock OpenAI client."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_response = MagicMock()

    mock_message.content = "Mocked LLM Response"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    
    return mock_client

def test_translate_en_to_sr(mock_openai_client):
    translate_en_to_sr(mock_openai_client, "Hello world")
    
    mock_openai_client.chat.completions.create.assert_called_once()
    args, kwargs = mock_openai_client.chat.completions.create.call_args
    assert kwargs['model'] == "gpt-4.1-nano"
    assert "Hello world" in kwargs['messages'][1]['content']

def test_get_regional_narrative(mock_openai_client):
    get_regional_narrative(mock_openai_client, "Test Region", "Test Category", "Test Data")
    
    mock_openai_client.chat.completions.create.assert_called_once()
    args, kwargs = mock_openai_client.chat.completions.create.call_args
    assert kwargs['model'] == "gpt-4.1"
    user_prompt = kwargs['messages'][1]['content']
    assert "# Data for Test Region" in user_prompt
    assert "Test Data" in user_prompt
    assert "non-technical policymaker" in user_prompt

def test_get_background_research(mock_openai_client, mocker):
    mocker.patch('src.llm.ADDITIONAL_CONTEXT', {'Test Category': 'Test Context'})
    get_background_research(mock_openai_client, "Test Region", "Test Category")
    
    mock_openai_client.chat.completions.create.assert_called_once()
    args, kwargs = mock_openai_client.chat.completions.create.call_args
    user_prompt = kwargs['messages'][1]['content']
    assert "summary regarding the Test Region municipality" in user_prompt
    assert "Test Context" in user_prompt

def test_get_initial_recommendations(mock_openai_client, mocker):
    mocker.patch('src.llm.ADDITIONAL_CONTEXT', {'Test Category': 'Test Context'})
    get_initial_recommendations(mock_openai_client, "Test Region", "Test Category", "Analysis", "Summary")

    mock_openai_client.chat.completions.create.assert_called_once()
    args, kwargs = mock_openai_client.chat.completions.create.call_args
    system_prompt = kwargs['messages'][0]['content']
    user_prompt = kwargs['messages'][1]['content']

    assert "Summary" in system_prompt
    assert "Analysis" in user_prompt
    assert "Test Context" in user_prompt

def test_get_final_projects(mock_openai_client):
    get_final_projects(mock_openai_client, "Test Region", "Test Category", "Recs", "Projects JSON")
    
    mock_openai_client.chat.completions.create.assert_called_once()
    args, kwargs = mock_openai_client.chat.completions.create.call_args
    user_prompt = kwargs['messages'][1]['content']
    
    assert "Recs" in user_prompt
    assert "Projects JSON" in user_prompt
