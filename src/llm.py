import streamlit as st
from openai import OpenAI

from src.config import (
    SYSTEM_MESSAGE,
    TRANSLATION_SYSTEM_PROMPT,
    ADDITIONAL_CONTEXT
)

def translate_en_to_sr(client: OpenAI, text: str) -> str:
    """
    Translates English text to Serbian using GPT-4.1-mini with caching.
    """
    translation_task = f"""
    # Task: Accurately translate the input text content into Serbian...
    # Input
    {text}
    # Requirements:
    - Preserve all Markdown formatting exactly...
    # Additional Translation Rules
    - Preserve all instances of "LDT" in English...
    - All mentions of "Decision Engine" or "decision engine" should be translated as **"алат за подршку одлучивању"**
    - All mentions of "region" or municipality" should be translated to **"општина"**
    """
    messages = [
        {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
        {"role": "user", "content": translation_task}
    ]
    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=messages,
        temperature=0.1,
        seed=42
    )
    return response.choices[0].message.content

def get_regional_narrative(client: OpenAI, region: str, category: str, comparison_text: str) -> str:
    """
    Generates the narrative for the regional analysis.
    """
    narrative_prompt = f"""
    # Data for {region}
    {comparison_text}
    # Task
    1. Number and print each indicator's name as a **mini-header (bold)**.
    2. Print the indicator metrics...
    3. Add a short **Interpretation** section.
    4. Finish with an **Overall Summary** (≤ 150 words).
    # Requirements
    - Write for a non-technical policymaker.
    - Explain the importance regarding the {region} region and {category} subcategory.
    - Follow the example format strictly.
    """
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": narrative_prompt}
    ]
    response = client.chat.completions.create(
        model="gpt-4.1", messages=messages, temperature=0
    )
    return response.choices[0].message.content

def get_background_research(client: OpenAI, region: str, subcategory: str) -> str:
    """
    Generates a background research summary for a given region and subcategory.
    """
    research_system_message = """
        # Role
        You are a policy researcher and data scientist specializing in countries located in the Western Balkans. 
        # Instructions
        - You will output only relevant responses and facts.
        - Provide accurate sources (if available).
    """
    task_research = f"""
        # Task
        - Provide a summary regarding the {region} municipality of Serbia when it comes to {subcategory}, focusing on its assets, weaknesses, and most relevant challenges.
        - Also look for basic information regarding the municipality such as its location, population, etc.
        # Requirements
        - Summarize the results in ≤ 150 words.
        - Incorporate the following additional context, if applicable:
            {ADDITIONAL_CONTEXT[subcategory]}
    """
    research_messages = [{"role": "system", "content": research_system_message}, 
                         {"role": "user", "content": task_research}]
    research_response = client.chat.completions.create(
        model="gpt-4.1", messages=research_messages, temperature=0.1, seed=42, max_tokens=200
    )
    return research_response.choices[0].message.content

def get_initial_recommendations(client: OpenAI, region: str, subcategory: str, regional_analysis: str, regional_summary: str) -> str:
    """
    Generates the initial project recommendations.
    """
    project_system_message = f"""
        # Role 
        You are a governance specialist with deep expertise in public policy for the Western Balkans.
        # Instructions 
        - Your task is to generate project recommendations for the {region} municipality in terms of {subcategory}.
        - Recommendations must be **strictly based on** the provided regional analysis and summary.
        # Context 
        **# Regional Summary (For Refinement Only):**
        {regional_summary}
    """
    project_task = f"""
        # Task
        - Generate exactly 5 project recommendations based on the **Regional Analysis**.
        - Rank projects by implementation feasibility.
        - Provide exactly 3 concrete policy actions for each project.
        # Requirements
        - Policy recommendations must be actionable at the municipal level.
        - Focus on projects implementable within 3-5 years.
        - Follow the specified format exactly.
        - Incorporate additional context if it aligns with the analysis:
            {ADDITIONAL_CONTEXT[subcategory]}
        # Format (Follow Exactly)
        Based on the regional analysis data for {region}, here are the 5 most viable public investment projects ranked by implementation feasibility:

        **1. [Specific Project Name]**
        *Project Description:* [50-75 words]
        *Data-Based Justification:* [Reference regional analysis - 75-100 words]
        *Implementation Actions:*
            1. [Municipal-level action]
            2. [Policy or regulatory action]
            3. [Partnership or funding action]
        
        ... (repeat for 5 projects)

        # Additional Context
        **Regional Analysis Data:**
        {regional_analysis}
    """
    project_messages = [{"role": "system", "content": project_system_message},
                        {"role": "user", "content": project_task}]
    initial_response = client.chat.completions.create(
        model="gpt-4.1", messages=project_messages, temperature=0.1, seed=42
    )
    return initial_response.choices[0].message.content

def get_final_projects(client: OpenAI, region: str, subcategory: str, initial_recommendations: str, json_projects: str) -> str:
    """
    Selects the most relevant existing projects based on the initial recommendations.
    """
    project_system_message = f"""
        # Role 
        You are a governance specialist with deep expertise in public policy for the Western Balkans.
    """
    relevant_projects_q = f"""
        # Task
        - Select the 5 most relevant projects from the provided dataset that align with the recommendations.
        - Present them with complete information (description, location, cost, URL, etc.).
        # Requirements
        - Projects should be relevant to {subcategory}.
        - If not thematically perfect, select from the same industry/theme.
        - Follow the format structure exactly.
        - Use full institution names for Lead IFI (e.g., "French Development Agency (AFD)").
        # Format (Follow Exactly)
        Here are the projects that align closely with the recommendations for {region}:

        1. **[Project Title]**
            - *Project Description:* [~50 words]
            - *Location:* [specific location]
            ...
            - *URL:* [project URL]

        ... (repeat for 5 projects)

        # Additional Context
        The project recommendations for reference are: {initial_recommendations}
        
        # Available Projects Dataset
        {str(json_projects)}
    """
    final_project_messages = [{"role": "system", "content": project_system_message},
                              {"role": "user", "content": relevant_projects_q}]
    final_response = client.chat.completions.create(
        model="gpt-4.1", messages=final_project_messages, temperature=0.1, seed=42
    )
    return final_response.choices[0].message.content
