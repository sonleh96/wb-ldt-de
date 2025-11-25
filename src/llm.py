import streamlit as st
from openai import OpenAI
import pandas as pd

from src.config import (
    SYSTEM_MESSAGE,
    TRANSLATION_SYSTEM_PROMPT,
    CBD_CONTEXT,
    PROJECT_REVIEW_MODEL
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

def get_background_research(client: OpenAI, region: str, subcategory: str, df_dev_plan: pd.DataFrame) -> str:
    """
    Generates a background research summary for a given region and subcategory.
    """
    
    dev_plan = df_dev_plan[(df_dev_plan['region'] == region) & (df_dev_plan['category'] == subcategory)].reset_index(drop=True)
    if len(dev_plan) == 0:
        current_situation = ""
        key_challenges = ""
        planned_measures_and_priorities = ""
    else:
        current_situation = dev_plan.loc[0, 'current situation']
        key_challenges = dev_plan.loc[0, 'key challenges']
        planned_measures_and_priorities = dev_plan.loc[0, 'planned measures and priorities']
    
    
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
        - The new information should be based on the latest data available.
        - The new information should come from reliable sources such as government websites,the World Bank, the European Commission, the OECD, etc.
        - Clearly state the region's most relevant strengths, weaknesses, and challenges, and opportunities.
        - Organize the information in a structured way, with clear headings and subheadings. 
        - When searching the web, only use official government sources or reliable news sites. Do not use websites like Wikipedia. 

        # Requirements
        - Summarize the results in ≤ 400 words (but don't mention this requirement in the output). Do not print out the word count either.
        - Cite the sources in the format with hyperlinks [Source: <source name>](<source URL>). Make sure the hyperlinks are working and clickable -> open in a new tab.
        - Incorporate and Prioritize the following additional context, if available. And also please cite them using the bolded text.
            - **Official Regional Development Plan for {region} municipality of Serbia**:
                - Current situation: {current_situation}
                - Key challenges: {key_challenges}
                - Planned measures and priorities: **{planned_measures_and_priorities}
            - **GPBP Country Benchmarking Dashboard (CBD)** with its source URL "https://cbd.pim-pam.net/":
                {CBD_CONTEXT[subcategory]}
        - New information must not contradict the existing context (if available).
        - Do not suggest "Let me know if you’d like a deeper dive into any of these areas." or anything similar in the output.
    
        # Output Format (Follow Exactly)
        Here's a quick summary of the {region} municipality when it comes to {subcategory}:

        **Strengths:**
        - [Strength 1]
        - [Strength 2]
        - ...

        **Weaknesses:**
        - [Weakness 1]
        - [Weakness 2]
        - ...

        **Challenges:**
        - [Challenge 1]
        - [Challenge 2]
        - ...

        **Opportunities:**
        - [Opportunity 1]
        - [Opportunity 2]
        - ...
        
    """
    research_messages = [{"role": "system", "content": research_system_message}, 
                         {"role": "user", "content": task_research}]
    research_response = client.responses.create(
        model="gpt-4.1", 
        input=research_messages, 
        temperature=0.1, 
        tools=[{"type": "web_search"}]
    )
    return research_response.output_text

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
        **# Regional Summary:**
        {regional_summary}
    """
    project_task = f"""
        # Task
        - Generate exactly 3 project recommendations based on the **Regional Analysis**.
        - Rank projects by implementation feasibility.
        - Provide exactly 3 concrete policy actions for each project.
        # Requirements
        - Policy recommendations must be actionable at the municipal level.
        - Focus on projects implementable within 3-5 years.
        - Follow the specified format exactly.

        # Format (Follow Exactly)
        Based on the regional analysis data for {region}, here are the 5 most viable public investment projects ranked by implementation feasibility:

        **1. [Specific Project Name]**
        *Project Description:* [50-75 words]
        *Data-Based Justification:* [Reference regional analysis - 75-100 words]
        *Research-Based Justification:* [Reference regional summary - 75-100 words]
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
        - Select the 3 most relevant projects from the provided dataset that align with the recommendations.
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
            - *Project Recommendation Addressed:* [project recommendation name]
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


# --- Project Review Document (Research via Web Search) ---

def get_project_review_document(client: OpenAI, wbif_url: str, model: str = None, temperature: float = None, json_only: bool = False) -> str:
    """
    Uses OpenAI Web Search to produce a ministry-grade Project Review Document for a given WBIF project URL.
    Returns a Markdown document following the strict format provided in research prompts.
    """
    system_prompt = r"""
Role: You are a meticulous public-sector analyst.
Mission: Produce a ministry-grade "Project Review Document" for a single WBIF project URL.
Tools: You must use the OpenAI Web Search tool to find authoritative sources (WBIF, IFIs, official gov sites, reputable media).
Style & Format: Exactly follow this structure (section headings and order are mandatory): 

    Project Review Document” (header block with: Project ID, Title, Sector/Window, Beneficiary, Lead IFI, Status)

    1) Objectives & Scope: Focus on socio-economic and development objectives of the project.
        * Be specific in terms of scope: How does this project fill existing quantifiable gaps?
        * Be clear on how this project advances the EU's Green Agenda and positions in the Single Project Pipeline (SPP)
        * Outline the objectives and scope of the project in bullet points.

    2) Financing Structure (headline) with a 2-column table (Instrument | Amount)

    3) Implementation & Governance with “Government / Implementing Bodies” (clearly state who the borrower, implementor, local beneficiaries, and regulatory bodies are) and “International Partners” (and their roles) sub-bullets. 
        * Include contact information for agencies/individuals in charge as a subsection.

    4) Outputs / Expected Results: show tangible, quantifiable, and time-bound expected results of the project.
        * Use bullet points to outline the expected results of the project.

    5) Updated Timeline (evidence-based reconstruction) as a 3-column table (Date | Milestone | Source)
        * Source cannot be empty.

    6) Risk Notes and Mitigation Strategies implemented (if any): Consider financial, regulatory/compliance, environmental/social, technical/operational, stakeholder/governance, and general planning risks. 
        * Outline facts and/or suggestions for each risk category, using bullet points.

    7) Primary Sources (quick access):  bullet list of the URLs used

Citations (mandatory):

    * Every factual claim derived from the web must have an inline citation immediately after the sentence/paragraph, with a clickable URL (e.g., “... Implementation, announced in 2022. WBIF page
    ”).

    * The Timeline table’s third column must show a concise source label linked to the exact URL for each row.

    * The Primary Sources section must list all URLs actually used.

    * Evidence & quality rules:

    * Prefer WBIF project pages, IFI project summary documents (e.g EBRD/EIB/CEB/World Bank), official ministry/government portals, and reputable press for milestones.

    * If amounts or dates differ across sources, show the conservative figure in the main text and clarify differences in a short note with citations to both sources.

    * If a field is unclear or missing, state that it’s not publicly specified and cite the best source you checked.

Outputs:

    * Produce a single self-contained Markdown document in the exact section order above.

    * No preamble, no meta-commentary—just the document.

Non-negotiables:

    * Do not invent data.

    * Do not include non-authoritative blogs, aggregator copies, or broken links.

    * Keep tone concise, neutral, decision-support oriented.
"""

    # Shared schema snippet to avoid f-string brace escaping issues
    _SCHEMA_SNIPPET = (
        """
{
  "financing_structure": [
    {"instrument": "string", "amount_text": "string", "source_label": "string", "source_url": "https://..."}
  ],
  "updated_timeline": [
    {"date_iso": "YYYY-MM-DD", "milestone": "string", "source_label": "string", "source_url": "https://..."}
  ],
  "narrative_markdown": "string"
}
        """.strip()
    )

    if json_only:
        user_prompt = f"""
Task: Research and produce the Project Review Document for this WBIF project and RETURN ONLY JSON (no prose, no code fences):
URL: {wbif_url}

Return a JSON object with exactly these fields:
{_SCHEMA_SNIPPET}
Constraints:
- financing_structure and updated_timeline must each have ≥1 valid entry; dates must be ISO.
- All URLs must be HTTPS; source_label should be concise.
- Output MUST be a single JSON object with no surrounding markdown and no extra commentary.
""".strip()
    else:
        user_prompt = f"""
Task: Research and produce the Project Review Document for this WBIF project:
URL: {wbif_url}

You MUST also return a JSON block that strictly follows this schema (for deterministic rendering of tables):
{_SCHEMA_SNIPPET}

Rules:
- financing_structure and updated_timeline must each have at least 1 entry. Use ISO dates.
- All source_url fields must be HTTPS and clickable.
- The narrative_markdown must contain the full document, but DO NOT duplicate the two tables inside it.
- Return the JSON block enclosed between lines that contain only "```json" and "```" so we can parse it.
- After the JSON, do not output anything else.
""".strip()

    response = client.responses.create(
        model=(model if model is not None else PROJECT_REVIEW_MODEL),
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        tools=[{"type": "web_search"}]
    )
    return response.output_text
