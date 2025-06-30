import json
import os
import re
from typing import List, Dict, Tuple, Optional, Any

from openai import OpenAI
import pandas as pd
import streamlit as st

os.environ["OPENAI_API_KEY"] = os.getenv('openai_apikey')

def run_analysis(
    df_indicatorlist: pd.DataFrame,
    df_indicators: pd.DataFrame,
    averages_df: pd.DataFrame,
    df_projects: pd.DataFrame,
    regions: List[str],
    language: str = 'en'
) -> None:
    """
    Main function to run the analysis pipeline for the LDT Decision Engine.
    
    This function orchestrates the entire analysis process including:
    - Indicator analysis
    - Regional analysis
    - Project recommendations
    
    Args:
        df_indicatorlist (pd.DataFrame): DataFrame containing the list of indicators and their metadata
        df_indicators (pd.DataFrame): DataFrame containing the actual indicator values for each region
        averages_df (pd.DataFrame): DataFrame containing national averages for each indicator
        df_projects (pd.DataFrame): DataFrame containing project examples and their details
        regions (List[str]): List of available regions for analysis
        language (str, optional): Language code for the interface. Defaults to 'en'.
                                Supported values: 'en' (English), 'sr' (Serbian)
    
    Returns:
        None: This function updates the Streamlit interface directly
    """
    
    ##Functions Required For Analysis##

    @st.cache_data
    def extract_regional_data(
        df: pd.DataFrame,
        region: str,
        relevant_columns: List[str],
        language: str = 'en'
    ) -> pd.DataFrame:
        """
        Filters the DataFrame based on the specified region and relevant columns.

        Args:
            df (pd.DataFrame): The dataset containing all regions and indicators
            region (str): The region to filter by
            relevant_columns (List[str]): List of column names to keep
            language (str, optional): Language code. Defaults to 'en'

        Returns:
            pd.DataFrame: Filtered DataFrame containing only the specified region and columns
        """
        if language == 'en':
            lang_col = "ENGLISH_NAME"
        if language == 'sr':
            lang_col = 'SERBIAN_NAME_CYRILLIC'

        valid_columns = [col for col in relevant_columns if col in df.columns]
        return df.loc[df[lang_col] == region, valid_columns]

    @st.cache_data
    def extract_national_data(
        df: pd.DataFrame,
        relevant_columns: List[str]
    ) -> pd.DataFrame:
        """
        Extracts national average data for specified columns.

        Args:
            df (pd.DataFrame): DataFrame containing national averages
            relevant_columns (List[str]): List of columns to extract

        Returns:
            pd.DataFrame: DataFrame containing only the specified columns
        """
        valid_columns = [col for col in relevant_columns if col in df.columns]
        return df[valid_columns]
    
    @st.cache_data
    def translate_en_to_sr(text: str) -> str:
        """
        Translates English text to Serbian with caching for better performance.
        
        This function uses GPT-4o-mini to perform high-quality translations while
        preserving Markdown formatting and following specific translation rules
        for public sector terminology.
        
        Args:
            text (str): The English text to translate
            
        Returns:
            str: The translated Serbian text in Cyrillic script
            
        Note:
            The function uses caching (@st.cache_data) to improve performance
            for repeated translations.
        """
        translation_system_prompt = """
        # Role: You are a professional English-to-Serbian public sector translation assistant

        # Instructions
        -   All translations must be outputed in the form of the Cyrillic alphabet

        """

        translation_task = f"""
        # Task: Accurately translate the input text content into Serbian, ensuring accuracy of terminology and clarity of expression

        # Input
        {text}

        # Requirements:
        - In-depth understanding of the terminology and descriptions in English public sector to ensure correct governance and public policy vocabulary is used in the Serbian translation.
        - Maintain the semantic integrity and accuracy of the original text to avoid omitting important information or introducing errors.
        - Pay attention to the differences in expression habits between English and Serbian, and make appropriate adjustments to make the Serbian translation more natural and fluent.
        - Only the translated content should be given, do not output other irrelevant content!
        - Follow "# Additional Translation Rules" and prioritize it over the above requirements **if and only if** there's a conflict. 
        - Preserve all Markdown formatting exactly as in the original text, including:
          * Bold text markers (**) must remain directly adjacent to the text they surround
          * No spaces should be added between formatting symbols and text
          * All links, lists, and other Markdown elements should maintain their exact format

        # Additional Translation Rules
        - Preserve all instances of "LDT" in English, 
        - No need to produce capital letters for each word in headings or titles, e.g "Мотор за Одлучивање" should be "Мотор за одлучивање."
        - All instances of "Decision Engine" or "decision engine" should be translated as **"алат за подршку одлучивању"**
        - All mentions of "region" or municipality" in the original English input text should be translated to **"општина"**
        - All monetary units (e.g USD, EUR, ...) should be kept in English.

        # Example 1：
        Original sentence: Veliko Gradište is a municipality in Serbia, positioned in the Braničevo District on the right bank of the Danube River, near the Romanian border.
        Translated: Велико Градиште је општина у Србији, која се налази у Браничевском округу на десној обали реке Дунав, близу границе са Румунијом.

        # Example 2:
        Original: **Access to school services (unit: %)**: Measures the percentage...
        Translated: **Приступ услугама у школи (јединица: %)**: Мери проценат...
        """

        messages = [
            {"role": "system", "content": translation_system_prompt},
            {"role": "user", "content": translation_task}
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,  # Even lower temperature for maximum consistency
            seed=42  # Fixed seed for deterministic translations
        )
        return response.choices[0].message.content

    
    #Global Variables for the OpenAI Calls
    client: OpenAI = OpenAI()

    SYSTEM_MESSAGE = """
    # Role
    You're a data scientist with domain expertise in local governance.

    # Instructions
    * Utilize data to help regional policy makers assess the environmental and economic performance of their regions using a set of pre-defined indicators.
    * Compare the performance of each indicator to its national average of the year in order to make logical conclusions. Some of the indicators are available at a multi-year basis.
    * The analysis must be as reasonable as possible. Avoid overly ambitious statements.

    # Context:
    This is what each indicator means:
    -   Accessibility to Health Services (unit: %): Measures the percentage of citizens with healthcare access within a 60-minute walking distance.
    -   Accessibility to School Services (unit: %): Measures the percentage of citizens with school access within a 60-minute walking distance.
    -   Diversity of Health Services: Evaluates healthcare service diversity within a municipality using the Shannon Diversity Index.
    -   CO2 Equivalent Emissions from all sources (unit: kgCO2e/kg): Quantifies total emissions, in terms of CO2, at the municipal level from all sources.
    -   Methane Emissions from all sources (kg): Quantifies total methane emissions at the municipal level from all sources.
    -   Emissions from Coal Power Plants (unit: kgCO2e/kg): Quantifies emissions from coal power plants specifically, aggregating data by emission type.
    -   Nighttime Luminosity (unit: nWatts/(cm2 x sr): Measures artificial nighttime light as an measurement of both the degree of electrification and economic development indicator using NASA's Black Marble data.
    -   Key Structure Average Broadband Download Speed (unit: megabites per second): Calculates the average broadband speed for key structures like schools and hospitals.
    -   Average Cellular Download Speed (unit: megabites per second): Measures average mobile download speeds across sub-national regions.
    -   Key Structures without Internet Access (unit: %): Shows the percentage of hospitals and schools lacking broadband internet access.
    -   Road flood risk per capita (unit: km per capita): Assesses road exposure to 1-in-100-year flood risks per capita for climate adaptation planning. 
    -   Road heatwave risk per capita (unit: km per capita): Measures road length at risk from heatwaves per capita in high-emission climate scenarios.
    -   Railway flood risk per capita (unit: km per capita): Assesses railway exposure to 1-in-100-year flood risks per capita.
    -   Railway heatwave risk per capita (unit: km per capita): Measures railway length at risk from heatwaves per capita in high-emission scenarios.
    -   Road flood risk (unit: km): Assesses road exposure to 1-in-100-year flood risks for climate adaptation planning. 
    -   Road heatwave risk (unit: km): Measures road length at risk from heatwaves in high-emission climate scenarios.
    -   Railway flood risk (unit: km): Assesses railway exposure to 1-in-100-year flood risks.
    -   Railway heatwave risk (unit: km): Measures railway length at risk from heatwaves in high-emission scenarios.
    -   PM 2.5 concentration (unit: µg/m3): Calculates average annual PM 2.5 concentration in sub-national regions, a key health risk factor.
    -   PM 10 concentration (unit: µg/m3): Calculates average annual PM 10 concentration in sub-national regions, a key health risk factor.
    -   NO2 concentration (unit: µg/m3): Calculates average annual NO2 concentration in sub-national regions, a key health risk factor.
    -   Agriculture Emissions (unit: kgCO2e/kg): Quantifies total emissions and emission factors at the municipal level from agriculture sources.
    -   Forestry & Land Use Emissions (unit: kgCO2e/kg): Quantifies total emissions and emission factors at the municipal level from forestry and land-use sources.
        
    Each indicator may fall under one or more of the following subcategories:
    -   Education: Concerns the degree of which the region's population has access to schools and how much access the region's schools has to internet infrastructure for a given year.
    -   Energy Access: Concerns how much the region has access to energy sources and electric power.
    -   Environment: May include areas such as air pollution and emissions
    -   Hospitals: Concerns the degree of which the region's population has access to hospitals and how much access the region's hospitals has to internet infrastructure for a given year.
    -   Digitalization: Concerns the development of the region's internet infrastructure, including both broadband and mobile internet. 
    -   Sustainable Transport: Concerns current development status and potential climate risks faced by of the region's existing land infrastructure such as railways and roads. 
        """

    category_options_en = ["Education", "Energy Access", "Environment", "Digitalization", "Health", "Sustainable Transport"]
    category_options_sr = ["Образовање", "Приступ енергији", "Животна средина", "Дигитализација", "Здравље", "Одрживи транспорт"]

    TOOLS = [{
        "type": "function",
        "function": {
            "name": "extract_relevant_data",
            "description": "Extract relevant columns from a particular dataset based on the region we are interested in and the columns relevant to the subcategory being analyzed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Region being analyzed and of which the data needs to be extracted"
                    },
                    "relevant_columns": {
                        "type": "array",
                        "description": "List of column titles that should be extracted from the dataset because they are relevant to the subcategory we are analyzing",
                        "items": { "type": "string" }  
                    }
                },
                "required": ["region"],  
                "additionalProperties": False
            }
        }
    }]



    if language == 'en':
        if "option_category" not in st.session_state:
            st.session_state.option_category = "Education"

        # Determine the index for "VelikoGradište" in the regions list
        region_index = regions.index("Veliko Gradište") if "Veliko Gradište" in regions else 0

        # Use selectbox to manage session state (Streamlit will handle option_region automatically)
        option_region = st.selectbox(
            "Select a Region:", 
            regions, 
            index=region_index,  # Uses computed index
            key="option_region"   # This prevents manual setting conflicts
        )
            # Category selectbox
        option_category = st.selectbox(
            "Select a category:",
            category_options_en,
            key="option_category",
            # index=category_options_en.index(st.session_state.option_category),
        )

        st.write("Region selected:", st.session_state.option_region)
        st.write("Category selected:", st.session_state.option_category)


    if language == 'sr':

        # Ensure session state keys exist for category, but NOT for region (to avoid conflict)
        if "option_category" not in st.session_state:
            st.session_state.option_category = "Образовање"

        # Determine the index for "VelikoGradište" in the regions list
        region_index = regions.index("Велико Градиште") if "Велико Градиште" in regions else 0

        # Use selectbox to manage session state (Streamlit will handle option_region automatically)
        option_region = st.selectbox(
            "Изаберите регион:", 
            regions, 
            index=region_index,  # Uses computed index
            key="option_region"   # This prevents manual setting conflicts
        )

        option_category = st.selectbox(
            "Изаберите категорију:",
            category_options_sr,
            key="option_category",
            # index=category_options_sr.index(st.session_state.option_category),
        )

        st.write("Изабран је регион:", st.session_state.option_region)
        st.write("Категорија је изабрана:", st.session_state.option_category)



    def df_indicatorlist_analysis(
        category_temp: str,
        df_temp: pd.DataFrame,
        region_temp: str,
        language: str = 'en'
    ) -> str:
        """
        Analyzes indicators for a specific category and region.

        Args:
            category_temp (str): Category to analyze
            df_temp (pd.DataFrame): DataFrame containing indicator metadata
            region_temp (str): Region being analyzed
            language (str, optional): Language code. Defaults to 'en'

        Returns:
            str: Formatted analysis text with relevant indicators
        """

        
        if language == 'en':
            flag = f"Starting analysis on {category_temp} in {region_temp}..."
            df_temp = df_temp[df_temp['SubCategory'].str.contains(category_temp, case=False, na=False)]

        if language == 'sr':
            flag = f"Почиње анализа категорије {category_temp} у региону {region_temp}..."
            df_temp = df_temp[df_temp['SubCategory'].str.contains(category_options_en[category_options_sr.index(category_temp)], 
                                                                  case=False, na=False)]

        with st.status(flag, expanded=True) as status:
            json_columns = df_temp.to_json(orient='records')
            question_output = f"""
                # Task
                From the attached dataframe, outline the listed indicators.

                # Requirements:
                -   Mention the full name of the indicator from 'indicator_name_full' in **bold**, followed by ':' and its full description in regular text from 'indicator_descrption'.
                -   Ensure the indicators are logically relevant to the category based on the provided information.
                -   Outline the indicators in order of most relevant to {category_temp}
                
                # Additional Context:
                This is the dataframe: {json_columns}"""
            
            messages = [
            {"role": "system", "content": SYSTEM_MESSAGE},  # System message
            {"role": "user", "content": question_output}]  # User message

            response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.3,
                    seed=42
                )
            
            if language == 'en':
                # st.subheader("Relevant Indicators")
                return response.choices[0].message.content
            if language == 'sr':
                # st.subheader("Релевантни индикатори")
                return translate_en_to_sr(response.choices[0].message.content)

    def build_comparison_lines(
        regional_df: pd.DataFrame,
        national_df: pd.DataFrame,
        language: str = 'en'
    ) -> str:
        """
        Converts regional and national DataFrames into a formatted comparison string.

        Args:
            regional_df (pd.DataFrame): DataFrame containing regional data
            national_df (pd.DataFrame): DataFrame containing national averages
            language (str, optional): Language code. Defaults to 'en'

        Returns:
            str: Formatted string comparing regional and national values
        
        Example:
            **Indicator (unit)**
            2020: 12.3 Mbps – Veliko Gradište | 18.1 Mbps – National avg
            2021: ...
        """
        if language == 'en':
            col = "ENGLISH_NAME"
        if language == 'sr':
            col = "SERBIAN_NAME_CYRILLIC"

        lines = []

        for col in regional_df.columns.drop([col, "year"]):
            unit = ""  # ► fill if you store units in a lookup dict
            lines.append(f"**{col}{unit}**")
            for _, r_row in regional_df.iterrows():
                year = int(r_row["year"])
                region_val = r_row[col]
                nat_val   = national_df.loc[national_df["year"] == year, col].iloc[0]
                region_name = r_row[col]
                lines.append(
                    f"{year}: {region_val:.2f} – {region_name} | {nat_val:.2f} – National avg"
                )
            lines.append("")   # blank line between indicators
        return "\n".join(lines) 

    def regional_analysis(
        region_name: str,
        relevant_indicators: str,
        category_temp: str,
        language: str = 'en'
    ) -> str:
        """
        Performs detailed regional analysis using a two-step RAG pipeline.

        Args:
            region_name (str): Name of the region to analyze
            relevant_indicators (str): Text containing relevant indicators
            category_temp (str): Category being analyzed
            language (str, optional): Language code. Defaults to 'en'

        Returns:
            str: Comprehensive regional analysis text
        """
        if language == 'en':
            flag = "Conducting regional analysis..."
        if language == 'sr':
            flag = "Извођење регионалне анализе..."

        with st.status(flag, expanded=True) as status:

            # ---------- 1. GPT *extraction* call ----------
            json_columns = df_indicators.columns[4:].tolist()

            extract_prompt = f"""
            # Task
            From the text below, return JSON with keys:
            • region          (string, should equal "{region_name}")
            • relevant_columns (array of dataset column titles)

            # Additional Context
            The following is text that lists indicators
            {relevant_indicators}

            And the following are the dataset column titles
            {json_columns}

            Return *only* the JSON, no prose."""
            
            messages = [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user",   "content": extract_prompt}
            ]
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=1
            )

            # print(response.choices[0].message)
            raw_content = response.choices[0].message.content
            json_str = re.sub(r"```json\s*|```", "", raw_content).strip()
            cols_parsed = json.loads(json_str)
            cols = cols_parsed.get("relevant_columns", [])
            if language == 'en':
                cols.extend(['ENGLISH_NAME', 'year'])
            if language == 'sr':
                cols.extend(["SERBIAN_NAME_CYRILLIC", 'year'])


            # ---------- 2.  deterministic numeric step ----------
            regional_df = extract_regional_data(df_indicators, region_name, cols, language)
            national_df = extract_national_data(averages_df.reset_index(), cols)
            comp_lines  = build_comparison_lines(regional_df, national_df, language)

            # ---------- 3. GPT *narrative* call ----------
            narrative_prompt = f"""
            # Data for {region_name}
            {comp_lines}

            # Task
            1. Number and print each indicator's name as a **mini-header (bold)** (e.g., "1. Indicator Name").
            2. Print the indicator metrics using this format `YYYY: Regional Indicator Performance + Unit - Region Name | National Performance + Unit - National Average`
            3. After each indicator's bullet list, add a short **Interpretation** section in regular text format (not as a header).
            4. Finish with an **Overall Summary** as a small header using # markdown syntax (≤ 150 words) for a non-technical policymaker.

            # Requirements
            -   Write for someone in government, who is in charge of **policy or decision-making**, who may not be familiar with these indicators.
            -   For each **interpretation** Explain why this is important regarding the {region_name} region and {category_temp} subcategory
            -   Keep the explanations clear, informative, and concise.
            -   The outputs must strictly follow what is set in the following **# Example** with no deviations.

            # Example
            1. Key Structure Average Broadband Download Speed (as a **mini-header (bold)**)\n
            2021: 33.67 megabits per second - Bor | 37.79 megabits per second - National Average\n2022: 26.43 megabits per second - Bor | 42.19 megabits per second - National Average\n2023: 43.90 megabits per second - Bor | 54.94 megabits per second - National Average\n2024: 44.63 megabits per second - Bor | 65.87 megabits per second - National Average\n\n
            **Interpretation**\n
            Bor's broadband speeds for key structures ...

            2. Average Cellular Download Speed (as a **mini-header (bold)**)\n
            2021: 33.67 megabits per second - Bor | 37.79 megabits per second - National Average\n2022: 26.43 megabits per second - Bor | 42.19 megabits per second - National Average\n2023: 43.90 megabits per second - Bor | 54.94 megabits per second - National Average\n2024: 44.63 megabits per second - Bor | 65.87 megabits per second - National Average\n\n
            **Interpretation**\n
            Bor shows an improving trend in cellular download speeds ...
            
            ### Overall Summary
            Bor demonstrates notable advancements in terms of digitalization over recent years ...
            """
            
            messages = [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user",   "content": narrative_prompt}
            ]
            narrative_response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0
            )

            if language == 'en':
                # st.subheader("Comprehensive Regional Analysis")
                return narrative_response.choices[0].message.content
            if language == 'sr':
                # st.subheader("Свеобухватна регионална анализа")
                return translate_en_to_sr(narrative_response.choices[0].message.content)

    def project_recommendation_agent(
        region_temp: str,
        subcategory: str,
        regional_analysis: str
    ) -> Tuple[str, str]:
        """
        Generates project recommendations based on regional analysis.

        Args:
            region_temp (str): Region to generate recommendations for
            subcategory (str): Category/subcategory focus area
            regional_analysis (str): Text of the regional analysis

        Returns:
            Tuple[str, str]: Tuple containing:
                - Initial recommendations text
                - Final project selections text
        """

        # CONSISTENT API PARAMETERS FOR ALL CALLS
        RESEARCH_TEMPERATURE = 0.1
        RECOMMENDATION_TEMPERATURE = 0.1
        FINAL_SELECTION_TEMPERATURE = 0.1
        RANDOM_SEED = 42

        # SYSTEM MESSAGE
        research_system_message = """
            # Role
            You are a policy researcher and data scientist specializing in countries located in the Western Balkans. 
            
            # Instructions
            -   You will output only relevant responses 
            -   You will only search for and retain facts
            -   Provide accurate sources (if available) for your information"""

        # FIRST AGENT - General Regional Summary
        task_research = f"""
            # Task
            -   Provide a summary regarding the {region_temp} municipality of Serbia when it comes to {subcategory}, focusing on its assets, weaknesses, and most relevant challenges.
            -   Also look for basic information regarding the municipality such as its location, population, etc..,
            
            
            # Requirements
            - Summarize the results in ≤ 150 words.
            - Focus on factual, data-driven insights
            - Maintain consistent structure and terminology
            """

        # CREATE CACHE KEY FOR REGIONAL SUMMARY
        research_cache_key = f"regional_summary_{region_temp}_{subcategory}"
        
        # CHECK IF REGIONAL SUMMARY EXISTS IN CACHE
        if research_cache_key not in st.session_state:
            if language == 'en':
                st.subheader("Background Research")
                status_temp = f"Doing some background research on {region_temp}... This may take a moment."
            else:
                st.subheader("Истраживање позадине")
                status_temp = f"Проводим нека истраживања о {region_temp}... Ово може потрајати неколико тренутака."
            
            with st.status(status_temp, expanded=True) as status:
                research_messages = [{"role": "system", "content": research_system_message}, 
                                    {"role": "user", "content": task_research}]

                research_response = client.chat.completions.create(
                    model="gpt-4o", 
                    messages=research_messages, 
                    temperature=RESEARCH_TEMPERATURE, 
                    seed=RANDOM_SEED,
                    max_tokens=200
                )
                # CACHE THE REGIONAL SUMMARY
                st.session_state[research_cache_key] = research_response.choices[0].message.content
        
        # GET REGIONAL SUMMARY FROM CACHE
        regional_summary = st.session_state[research_cache_key]
        
        # DISPLAY REGIONAL SUMMARY
        if language == 'en':
            if research_cache_key not in st.session_state or st.session_state.get('show_research', False):
                st.subheader("Background Research")
                st.write(regional_summary)
        else:
            if research_cache_key not in st.session_state or st.session_state.get('show_research', False):
                st.subheader("Истраживање позадине")
                st.write(translate_en_to_sr(regional_summary))

        # SECOND AGENT - Project Recommendations
        project_system_message = f"""
            # Role 
            You are a governance specialist with deep expertise in both national and sub-national public policy for countries located in the Western Balkans.

            # Instructions 
            -   Your task is to generate project recommendations for the {region_temp} municipality in terms of {subcategory}. 
            -   However, these recommendations must be **strictly based on** 
                    - the regional analysis 
                    - regional summary 
                    - when applicable: Potentially Viable Projects
            
            # Context 
            **# Regional Summary (Only for Refinement, Not Idea Generation):**\n
            The following background information about the region should only be used to refine or adjust the recommendations 
            from the dataset. It should **not** be used to create recommendations that are not supported by the dataset.\n
            {regional_summary}\n\n
            """

        project_task = f"""
            # Task
            -   Generate exactly 5 project recommendations that directly address the specific challenges and opportunities identified in the **Regional Analysis**
            -   Rank projects by implementation feasibility (most feasible first)
            -   Each recommendation must cite specific data points or findings from the Regional Analysis where applicable
            -   Provide exactly 3 concrete policy actions for each project

            # Ranking Criteria (in order of priority)
            1. Addresses critical gaps identified in the regional data
            2. Builds on existing regional strengths/assets  
            3. Feasible given typical municipal budgets and capabilities
            4. Aligns with {subcategory} sector priorities
            5. Has measurable impact potential

            # Requirements
            -   Policy recommendations must be actionable at the municipal level
            -   Focus on projects that can realistically be implemented within 3-5 years
            -   Prioritize projects that leverage existing infrastructure or capabilities
            -   Follow the exact format specified below without deviation
            -   Maintain consistent terminology and structure

            # Format (Follow Exactly)
            Based on the regional analysis data for {region_temp}, here are the 5 most viable public investment projects ranked by implementation feasibility:

            **1. [Specific Project Name]**
            Project Description: [50-75 words describing the project scope and components]
            Data-Based Justification: [Reference specific indicators/findings from Regional Analysis that support this project - 75-100 words]
            Implementation Actions:
                1. [Specific municipal-level action]
                2. [Specific policy or regulatory action]
                3. [Specific partnership or funding action]

            **2. [Specific Project Name]**
            [Same format as above]

            **3. [Specific Project Name]**
            [Same format as above]

            **4. [Specific Project Name]**
            [Same format as above]

            **5. [Specific Project Name]**
            [Same format as above]

            # Additional Context
            **Regional Analysis Data:**
            {regional_analysis}
            """

        project_messages = [{"role": "system", "content": project_system_message},
                                {"role": "user", "content": project_task}]

        
            

        if language == 'en':
            
            st.subheader("Initial Project Recommendations")

            # SHOW INTERMEDIATE RESPONSE (Processing Message)
            with st.status("Generating project recommendations... This may take a moment.", expanded=True) as status:
                initial_response = client.chat.completions.create(model="gpt-4o", messages=project_messages, temperature=RECOMMENDATION_TEMPERATURE, seed=42)
                initial_recommendations = initial_response.choices[0].message.content

                # FILTER RELEVANT PROJECTS
                df_projects_temp = df_projects[df_projects['Investment Sector'].str.contains(subcategory, case=False, na=False)]
                if option_category == 'Environment':
                    df_projects_temp = df_projects_temp[df_projects_temp['Project Description'].str.contains("air | air pollution | emissions | co2 | CO2")]
                
                if option_category == 'Sustainable Transport':
                    df_projects_temp = df_projects_temp[df_projects_temp['Status'] != 'Preparation']

                json_projects = df_projects_temp.to_json(orient="records")
                
            # DISPLAY INITIAL RESPONSE
            # st.subheader("Initial Project Recommendations")
            st.write(initial_recommendations)
        
        if language == 'sr':

            st.subheader("Прве препоруке за пројекте")

            # SHOW INTERMEDIATE RESPONSE (Processing Message)
            with st.status("Генерисање препорука пројеката... Ово може потрајати неколико тренутака.", expanded=True) as status:
                initial_response = client.chat.completions.create(model="gpt-4o", messages=project_messages, temperature=RECOMMENDATION_TEMPERATURE, seed=42)
                initial_recommendations = initial_response.choices[0].message.content

                # FILTER RELEVANT PROJECTS
                df_projects_temp = df_projects[df_projects['Земља корисница'].str.contains(subcategory, case=False, na=False)]
                if option_category == 'Животна средина':
                    df_projects_temp = df_projects_temp[df_projects_temp['Опис пројекта'].str.contains("ваздух | загађење ваздуха | емисије | cO2 | CO2")]
                if option_category == 'Одрживи транспорт':
                     df_projects_temp = df_projects_temp[df_projects_temp['Статус'] != 'Припрема']

                json_projects = df_projects_temp.to_json(orient="records")

            # DISPLAY INITIAL RESPONSE
            # st.subheader("Прве препоруке за пројекте")
            st.write(translate_en_to_sr(initial_recommendations))

        relevant_projects_q = f"""
        # Task
        -   Select the most relevant projects from the provided dataset based on project description, fit, and title alignment with the recommendations
        -   Present exactly 5 projects with complete information including project description, location, expected beneficiaries, lead IFI, cost, and URL

        # Requirements
        -   Projects should be selected based on relevance to {subcategory} and alignment with the **# Additional Context** recommendations
        -   The chosen projects serve as examples for policy makers to learn from
        -   If projects are not thematically relevant to the recommendations, select projects from the same industry/theme
        -   Always output exactly 5 projects unless fewer than 5 relevant projects exist
        -   For Lead IFI, always use full institution name and abbreviation in parentheses. Refer to "# Disambiguation"
        -   Follow the exact format structure without deviation
        -   Maintain consistent terminology and project numbering

        # Format (Follow Exactly)
        Here are the projects that align closely with the recommendations for {region_temp}, focusing particularly on {subcategory}:

        1. **[Project Title]**
            - Project Description: [approximately 50 words]
            - Location: [specific location]
            - Beneficiaries: [target beneficiaries]
            - Lead IFI: [Full Institution Name (ABBREVIATION)]
            - Sector: {subcategory}
            - Type: [project type]
            - Total Financing: [amount]
            - Project Benefits: [key benefits]
            - URL: [project URL]

        2. **[Project Title]**
            [Same format as above]

        3. **[Project Title]**
            [Same format as above]

        4. **[Project Title]**
            [Same format as above]

        5. **[Project Title]**
            [Same format as above]

        # Additional Context
        The project recommendations for reference are: {initial_recommendations}
        
        # Available Projects Dataset
        {str(json_projects)}
        
        # Disambiguation
        - AFD: French Development Agency (AFD)
        - KfW: KfW Bankengruppe (KfW)
        - EIF: European Investment Fund (EIF)
        - CEB: Council of Europe Development Bank (CEB)
        - EIB: European Investment Bank (EIB)
        - EBRD: European Bank of Reconstruction and Development (EBRD)
        - IFC: International Finance Corporation (IFC)
        """
        
        final_project_messages = [{"role": "system", "content": project_system_message},
                                  {"role": "user", "content": relevant_projects_q}]
        
        final_response = client.chat.completions.create(
            model="gpt-4o", 
            messages=final_project_messages, 
            temperature=FINAL_SELECTION_TEMPERATURE, 
            seed=RANDOM_SEED
        )
        final_project_selection = final_response.choices[0].message.content

        if language == 'en':
            # DISPLAY FINAL OUTPUT
            st.subheader("Final Project Selections")
            st.write(final_project_selection)

            # UPDATE STATUS
            status.update(label="Process Completed!", state="complete")

        if language == 'sr':
            # DISPLAY FINAL OUTPUT
            st.subheader("Коначни избор пројеката")
            st.write(translate_en_to_sr(final_project_selection))

            # UPDATE STATUS
            status.update(label="Process Completed!", state="complete")

        return initial_recommendations, final_project_selection

    ## Running Analysis ##

    # Initialize session state flags if they don't exist
    if 'analysis_completed' not in st.session_state:
        st.session_state.analysis_completed = False
    if 'regional_analysis_completed' not in st.session_state:
        st.session_state.regional_analysis_completed = False
    if 'project_recommendations_completed' not in st.session_state:
        st.session_state.project_recommendations_completed = False
    if 'start_analysis' not in st.session_state:
        st.session_state.start_analysis = False  # Ensure session state variable exists

    # Initialize 'messages' key in session state if not already initialized
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []
    
    if language == 'en':
        if st.button("Let's get started"):
            st.session_state.start_analysis = True  # Set flag when button is clicked
    else:
        if st.button("Хајде да почнемо"):
            st.session_state.start_analysis = True  # Set flag when button is clicked

    if st.session_state.start_analysis and not st.session_state.analysis_completed:
        relevant_indicators = df_indicatorlist_analysis(st.session_state.option_category, df_indicatorlist, st.session_state.option_region, language=language) 
        st.session_state.relevant_indicators = relevant_indicators
        st.session_state.analysis_completed = True  # Mark analysis as complete

    # Display the initial analysis result if it exists in session state
    if st.session_state.get("relevant_indicators"):
        # Always show the subheader when displaying results
        if language == 'en':
            st.subheader("Relevant Indicators")
        else:
            st.subheader("Релевантни индикатори")
        st.write(st.session_state.relevant_indicators)


    # Second button only appears after the first analysis is complete
    if st.session_state.analysis_completed:

        if language == 'en':
            if st.button("Let's conduct a Regional Analysis") and not st.session_state.regional_analysis_completed:
                regional_analysis_results = regional_analysis(st.session_state.option_region, st.session_state.relevant_indicators, st.session_state.option_category, language=language)
                st.session_state.regional_analysis_results = regional_analysis_results
                st.session_state.regional_analysis_completed = True
        else:
            if st.button("Хајде да урадимо регионалну анализу") and not st.session_state.regional_analysis_completed:
                regional_analysis_results = regional_analysis(st.session_state.option_region, st.session_state.relevant_indicators, st.session_state.option_category, language=language)
                st.session_state.regional_analysis_results = regional_analysis_results
                st.session_state.regional_analysis_completed = True
        
        

    # Display regional analysis if it exists
    if st.session_state.get("regional_analysis_results"):
        # Always show the subheader when displaying results
        if language == 'en':
            st.subheader("Comprehensive Regional Analysis")
        else:
            st.subheader("Свеобухватна регионална анализа")
        st.write(st.session_state.regional_analysis_results)


    if st.session_state.regional_analysis_completed == True:
        # Ensure function only runs once
        if language == 'en':
            flag = "What Project Recommendations Follow?"
        if language == 'sr':
            flag = "Које препоруке за пројекте следе?"

        if st.button(flag) and not st.session_state.project_recommendations_completed:
            project_recommendations = project_recommendation_agent(st.session_state.option_region, st.session_state.option_category, st.session_state.regional_analysis_results)
            st.session_state.project_recommendations_completed = True
            st.session_state.project_recommendations = project_recommendations

    if st.session_state.get("project_recommendations"):
        if language == 'en':
            if st.button("New Analysis"):
                # Clear only analysis-specific session state
                analysis_keys = [
                    'analysis_completed', 'regional_analysis_completed', 
                    'project_recommendations_completed', 'start_analysis',
                    'relevant_indicators', 'regional_analysis_results', 
                    'project_recommendations', 'messages'
                ]
                for key in analysis_keys:
                    if key in st.session_state:
                        del st.session_state[key]

                # Rerun the app without modifying language state
                st.rerun()

        else:
            if st.button("Нова анализа"):
                # Clear only analysis-specific session state
                analysis_keys = [
                    'analysis_completed', 'regional_analysis_completed', 
                    'project_recommendations_completed', 'start_analysis',
                    'relevant_indicators', 'regional_analysis_results', 
                    'project_recommendations', 'messages'
                ]
                for key in analysis_keys:
                    if key in st.session_state:
                        del st.session_state[key]

                # Rerun the app without modifying language state
                st.rerun()