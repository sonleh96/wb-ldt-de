# app_config.py

# --- CONSTANTS ---
BUCKET_NAME = "wb-ldt"
CACHE_PATH = "decision_engine/cached_responses"
CACHE_VERSION = "1.0"
SLEEP_TIME = 0 # Can be increased to simulate processing time for cached responses
PROJECT_DETAILS_TTL_HOURS = 48
# Set to False to disable TTL expiration (cache never expires). Set True to enforce TTL.
PROJECT_DETAILS_TTL_ENABLED = False

# --- LLM Model configuration ---
# Centralize model/version and generation settings to ensure deterministic formatting
PROJECT_REVIEW_MODEL = "gpt-5"

# --- CATEGORY AND INDICATOR MAPPINGS ---
CATEGORY_OPTIONS_EN = ["Education", "Energy Access", "Environment", "Digitalization", "Health", "Sustainable Transport"]
CATEGORY_OPTIONS_SR = ["Образовање", "Приступ енергији", "Животна средина", "Дигитализација", "Здравље", "Одрживи транспорт"]

CATEGORY_SR_TO_EN = dict(zip(CATEGORY_OPTIONS_SR, CATEGORY_OPTIONS_EN))
CATEGORY_EN_TO_SR = dict(zip(CATEGORY_OPTIONS_EN, CATEGORY_OPTIONS_SR))

CATEGORY_INDICATOR_DICT = {
    'Education': [
        "Accessibility to School Services (unit: %)",
        "Number of Schools per Capita (unit:)",
        "Diversity of Schools Index (unit:)"

    ],
    "Energy Access": [
        "Nighttime Luminosity (unit: nWatts/(cm2 x sr)",
        "Luminosity per Capita (unit: nWatts/(cm2 x sr x person))",
        "Luminosity per Area (unit: nWatts/(cm2 x sr x km2))",
        "Share of Area Lit by Nighttime Luminosity (unit: %)",
        "Share of Population Exposed to Nighttime Luminosity (unit: %)"
    ],
    "Environment": [
        "PM 2.5 concentration (unit: µg/m3)",
        "Total Methane Emissions (unit: tonnes)",
        "Total CO2-Equivalent Emissions (unit: tonnes)",
        "Waste Disposal Points Per 10000 (unit:)",
        "Share of Population without proper Access to Waste Disposal (unit: %)"
    ],
    'Digitalization': [
        "Key Structure Average Broadband Download Speed (unit: megabites per second)",
        "Key Structures without Internet Access (unit: %)",
        "Average Cellular Download Speed (unit: megabites per second)"
    ],
    'Health': [
        "Accessibility to Healthcare Services (unit: %)",
        "Number of Hospitals per Capita (unit:)",
        "Diversity of Health Services Index (unit:)"
    ],
    'Sustainable Transport': [
        "Road Density (unit: km/km2)",
        "Railway Density (unit: km/km2)",
        "Railway Flood Risk (unit: %)",
        "Road Flood Risk (unit: %)",
        "Railway Heatwave Risk (unit: %)",
        "Road Heatwave Risk (unit: %)"
    ]
}

# --- UI TEXT (Internationalization) ---
UI_TEXT = {
    "en": {
        "app_title": "GPBP LDT - Decision Engine",
        "app_subheader": "Hello, I can produce an automated analysis of regional performances based on the themes you're interested in. Then, I can make public investment recommendations based on the analysis.",
        "language": "Language",
        "selected_language": "Selected Language: {lang}",
        "select_region": "Select a Region:",
        "select_category": "Select a category:",
        "region_selected": "Region selected: {region}",
        "category_selected": "Category selected: {category}",
        "start_button": "Let's get started",
        "new_analysis_button": "New Analysis",
        "regional_analysis_button": "Let's conduct a Regional Analysis",
        "project_recommendations_button": "What Project Recommendations Follow?",
        "relevant_indicators_header": "Relevant Indicators",
        "regional_analysis_header": "Comprehensive Regional Analysis",
        "project_recommendations_header": "Initial Project Recommendations",
        "final_projects_header": "Final Project Selections",
        "background_research_header": "Background Research",
        "status_starting_analysis": "Starting analysis for {category} in {region}...",
        "status_conducting_regional": "Conducting regional analysis...",
        "status_background_research": "Doing some background research on {region}... This may take a moment.",
        "status_generating_projects": "Generating project recommendations... This may take a moment.",
        "status_finalizing_projects": "Finalizing project selections...",
        "status_matching_projects": "Matching with similar projects within the region... This may take a moment.",
        "status_process_complete": "Process Completed!",
    },
    "sr": {
        "app_title": "GPBP LDT - мотор за одлучивање",
        "app_subheader": "Здраво, могу да извршим аутоматизовану анализу регионалних перформанси на основу тема које вас занимају. атим могу да дам препоруке за јавне инвестиције на основу анализе",
        "language": "Language", # Kept in English for st.radio label
        "selected_language": "Одабрани језик: {lang}",
        "select_region": "Изаберите регион:",
        "select_category": "Изаберите категорију:",
        "region_selected": "Изабран је регион: {region}",
        "category_selected": "Категорија је изабрана: {category}",
        "start_button": "Хајде да почнемо",
        "new_analysis_button": "Нова анализа",
        "regional_analysis_button": "Хајде да урадимо регионалну анализу",
        "project_recommendations_button": "Које препоруке за пројекте следе?",
        "relevant_indicators_header": "Релевантни индикатори",
        "regional_analysis_header": "Свеобухватна регионална анализа",
        "project_recommendations_header": "Прве препоруке за пројекте",
        "final_projects_header": "Коначни избор пројеката",
        "background_research_header": "Истраживање позадине",
        "status_starting_analysis": "Почиње анализа категорије {category} у региону {region}...",
        "status_conducting_regional": "Извођење регионалне анализе...",
        "status_background_research": "Проводим нека истраживања о {region}... Ово може потрајати неколико тренутака.",
        "status_generating_projects": "Генерисање препорука пројеката... Ово може потрајати неколико тренутака.",
        "status_finalizing_projects": "Финализовање избора пројеката...",
        "status_matching_projects": "Усклађивање са сличним пројектима у региону... Ово може потрајати неколико тренутака.",
        "status_process_complete": "Процес је завршен!",
    }
}

# --- LLM PROMPTS ---

SYSTEM_MESSAGE = f"""
# Role
You're a data scientist with domain expertise in local governance.

# Instructions
* Utilize data to help regional policy makers assess the environmental and economic performance of their regions using a set of pre-defined indicators.
* Compare the performance of each indicator to its national average of the year in order to make logical conclusions. Some of the indicators are available at a multi-year basis.
* The analysis must be as reasonable as possible. Avoid overly ambitious statements.

# Context:
This is what each indicator means:
-   Accessibility to Health Services (unit: %): Measures the percentage of citizens with healthcare access within a 60-minute walking distance.
-   Number of Hospitals per Capita (unit:): Number of hospitals in the region normalized to its total population
-   Diversity of Health Services Index (unit:): Evaluates the diversity in healthcare services (hospitals, clinics, etc...) within a municipality using the Shannon Diversity Index.
-   Accessibility to School Services (unit: %): Measures the percentage of citizens with school access within a 60-minute walking distance.
-   Number of Schools per Capita (unit:): Number of schools, colleges, and universities in the region normalized to its total population
-   Diversity of Schools Index (unit:): Evaluates the diversity of educational institutions (schools, colleges, and universities) within a municipality using the Shannon Diversity Index.
-   Nighttime Luminosity (unit: nWatts/(cm2 x sr): Measures artificial nighttime light as an measurement of both the degree of electrification and economic development indicator using NASA's Black Marble data.
-   Luminosity per Capita (unit: nWatts/(cm2 x sr x person)): Nighttime Luminosity normalized to the region's Total Population.
-   Luminosity per Area (unit: nWatts/(cm2 x sr x km2)): Nighttime Luminosity normalized to the region's Total Area.
-   Share of Area Lit by Nighttime Luminosity (unit: %): Share of the region's total area lit by nighttime luminosity.
-   Share of Population Exposed to Nighttime Luminosity (unit: %): Share of the region's total population under nighttime luminosity 
-   Key Structure Average Broadband Download Speed (unit: megabites per second): Calculates the average broadband speed for key structures like schools and hospitals.
-   Average Cellular Download Speed (unit: megabites per second): Measures average mobile download speeds across sub-national regions.
-   Key Structures without Internet Access (unit: %): Shows the percentage of hospitals and schools lacking broadband internet access.
-   Road Density (unit: km/km2): The ratio of the length of the region's total road network to the region's land area
-   Railway Density (unit: km/km2): The ratio of the length of the region's total railway network to the region's land area
-   Road Flood Risk (unit: %): Assesses the share of the region's total length of railway exposure to 1-in-100-year flood risks for climate adaptation planning
-   Road Heatwave Risk (unit: %): Assesses the share of the region's total length of road exposure to 1-in-100-year flood risks for climate adaptation planning
-   Railway Flood Risk (unit: %): Percentage of railway length at risk from 1-in-100-year flood risks for climate adaptation planning. 
-   Railway Heatwave Risk (unit: %): Measures road length at risk from heatwaves in high-emission climate scenarios
-   PM 2.5 concentration (unit: µg/m3): Calculates average annual PM 2.5 concentration in sub-national regions, a key health risk factor.
-   Total Methane Emissions (unit: tonnes): Total methane emissions from all sources in the region.
-   Total CO2-Equivalent Emissions (unit: tonnes): Total CO2-equivalent emissions from all sources in the region.
-   Waste Disposal Points Per 10000 (unit:): Number of waste disposal points per 10,000 people in the region.
-   Share of Population without proper Access to Waste Disposal (unit: %): Share of the region's total population without proper access to waste disposal.
    
Each indicator may fall under one or more of the following subcategories:
-   Education: Concerns the degree of which the region's population has access to schools and how much access the region's schools has to internet infrastructure for a given year.
-   Energy Access: Concerns how much the region has access to energy sources and electric power.
-   Environment: May include areas such as air pollution and emissions
-   Hospitals: Concerns the degree of which the region's population has access to hospitals and how much access the region's hospitals has to internet infrastructure for a given year.
-   Digitalization: Concerns the development of the region's internet infrastructure, including both broadband and mobile internet. 
-   Sustainable Transport: Concerns current development status and potential climate risks faced by of the region's existing land infrastructure such as railways and roads. 
"""

TRANSLATION_SYSTEM_PROMPT = """
# Role: You are a professional English-to-Serbian public sector translation assistant

# Instructions
-   All translations must be outputed in the form of the Cyrillic alphabet

"""

ADDITIONAL_CONTEXT = {
    'Digitalization': """According to the Country Benchmarking Dashboard (CBD), Serbia has a national 4G Coverage Score of 98 and 4G Penetration Score of 22 (both out of 100) based on the EU average. 
                         A 4G coverage rate indicates the proportion of the population with access to a 4G mobile network signal, 
                         while the penetration rate measures the number of active 4G mobile users relative to the total population. 
                         While coverage can be high, the capacity or quality of the network in certain areas might not meet user demand, particularly in rural locations. """,
    'Health': """""",
    'Environment': """According to the Country Benchmarking Dashboard (CBD), Serbia lacks information on the following Global Climate Change Institution Indicators (GCCIIs): 
                      1) Budget guidelines 2) Budget Tracking 3) Public Investment Screening 4) State-owned Enterprises Climate-related Financial Disclosures 5) National Adaptation Plan.
                      Developed by the Climate Governance Program at the World Bank, these are important for assessing a country's institutional capacity to address climate change.
                      Additionally, Serbia also scores a 2.86 on Accountability, 3 on Organization, 3.52 on Planning, 2.29 on Public Finance, and 2.38 on Subnational Government / State-owned Enterprises 
                      (all out of 6) in terms of Climate Change Institutional Asssessments (CCIA) Benchmarking. Here's how they're defined:
                      __Organization__: Assesses the regulatory framework for climate change policy, the functional mandates of government agencies, coordination arrangements, and the technical capacity to support climate change policy.
                      __Planning__: Evaluates systems for climate change risk and vulnerability assessments, strategies, and plans and the regulatory framework for the climate change planning andpolicy process.
                      __Public Finance__: Considers the integration of climate strategies, plans, and policies in fiscal and public financial management (PFM) practices and the mobilization of resources for climate action.
                      __Subnational Governments and State-Owned Enterprises__: Examines the treatment of climate change in the intergovernmental system and in the management of state-owned enterprises (SOEs), the capacity of subnational governments (SNGs), and incentives for climate action.
                      __Accountability__: Reviews transparency and engagement mechanisms for civil society, the private sector, and other stakeholders and the roles of expert advisory and oversight institutions""",
    'Education': """""",
    'Energy Access': """According to the Country Benchmarking Dashboard (CBD), Serbia has a national Electricity Supply Quality score of 91 (out of 100) based on the EU average.
                        Electricity supply quality describes how closely the supplied electrical power matches ideal specifications in terms of voltage, frequency, and waveform.
                        Good power quality ensures consistent voltage within specified limits, a stable frequency close to the rated value, and a smooth sinusoidal waveform. 
                        High power quality is crucial for the proper functioning, efficiency, and safety of electrical and electronic equipment, while poor quality can lead to equipment damage, data loss, disruptions, and increased costs""",
    'Sustainable Transport': """According to the Country Benchmarking Dashboard (CBD), Serbia has a national Road Quality Score of 42 and Railroad Quality Score of 62 (both out of 100) based on the EU average."""
}

# --- Visualization configuration ---
# Heuristics: True means higher is better; False means lower is better
# INDICATOR_HIGHER_IS_BETTER = {
#     "Accessibility to Health Services (unit: %)": True,
#     "Accessibility to School Services (unit: %)": True,
#     "Diversity of Health Services": True,
#     "Nighttime Luminosity (unit: nWatts/(cm2 x sr)": True,
#     "Key Structure Average Broadband Download Speed (unit: megabites per second)": True,
#     "Average Cellular Download Speed (unit: megabites per second)": True,
#     "Key Structures without Internet Access (unit: %)": False,
#     "Road flood risk per capita (unit: km per capita)": False,
#     "Road heatwave risk per capita (unit: km per capita)": False,
#     "Railway flood risk per capita (unit: km per capita)": False,
#     "Railway heatwave risk per capita (unit: km per capita)": False,
#     "PM 2.5 concentration (unit: µg/m3)": False,
#     "PM 10 concentration (unit: µg/m3)": False,
#     "NO2 concentration (unit: µg/m3)": False,
#     "Emissions from all sources (unit: kgCO2e/kg)": False,
#     "Emissions from Coal Power Plants (unit: kgCO2e/kg)": False,
#     "Agriculture Emissions (unit: kgCO2e/kg)": False,
#     "Forestry & Land Use Emissions (unit: kgCO2e/kg)": False,
# }

INDICATOR_HIGHER_IS_BETTER = {
    "Accessibility to Healthcare Services (unit: %)": True,
    'Number of Hospitals per Capita (unit:)': True,
    'Diversity of Health Services Index (unit:)': True,
    "Accessibility to School Services (unit: %)": True,
    'Number of Schools per Capita (unit:)': True,
    'Diversity of Schools Index (unit:)': True,
    "PM 2.5 concentration (unit: µg/m3)": False,
    "Total Methane Emissions (tonnes)": False,
    "Total CO2-Equivalent Emissions (tonnes)": False,
    "Key Structure Average Broadband Download Speed (unit: megabites per second)": True,
    "Key Structures without Internet Access (unit: %)": False,
    "Average Cellular Download Speed (unit: megabites per second)": True,
    "Nighttime Luminosity (unit: nWatts/(cm2 x sr)": True,
    "Railway Flood Risk (unit: %)": False,
    "Road Flood Risk (unit: %)": False,
    "Railway Heatwave Risk (unit: %)": False,
    "Road Heatwave Risk (unit: %)": False,
    'Road Density (unit: km/km2)': True,
    'Railway Density (unit: km/km2)': True,
    'Luminosity per Capita (unit: nWatts/(cm2 x sr x person))': True,
    'Luminosity per Area (unit: nWatts/(cm2 x sr x km2))': True,
    'Share of Area Lit by Nighttime Luminosity (unit: %)': True,
    'Share of Population Exposed to Nighttime Luminosity (unit: %)': True,
    'Waste Disposal Points Per 10000 (unit:)': True,
    'Share of Population without proper Access to Waste Disposal (unit: %)': False,
}

COLUMN_ORDER = [
    "year",
    "NAME_1",
    "ENGLISH_NAME",
    "SERBIAN_NAME_CYRILLIC",
    "Prosperity Score",
    "Infrastructure Score",
    "Livability Score",
    "Energy Access Score",
    "Digitalization Score",
    "Sustainable Transport Score",
    "Education Score",
    "Health Score",
    "Environment Score",
    "Nighttime Luminosity (unit: nWatts/(cm2 x sr)",
    'Luminosity per Capita (unit: nWatts/(cm2 x sr x person))',
    'Luminosity per Area (unit: nWatts/(cm2 x sr x km2))',
    'Share of Area Lit by Nighttime Luminosity (unit: %)',
    'Share of Population Exposed to Nighttime Luminosity (unit: %)',
    "Key Structure Average Broadband Download Speed (unit: megabites per second)",
    "Key Structures without Internet Access (unit: %)",
    "Average Cellular Download Speed (unit: megabites per second)",
    'Road Density (unit: km/km2)',
    'Railway Density (unit: km/km2)',
    "Railway Flood Risk (unit: %)",
    "Road Flood Risk (unit: %)",
    "Railway Heatwave Risk (unit: %)",
    "Road Heatwave Risk (unit: %)",
    "Accessibility to Healthcare Services (unit: %)",
    'Number of Hospitals per Capita (unit:)',
    'Diversity of Health Services Index (unit:)',
    "Accessibility to School Services (unit: %)",
    'Number of Schools per Capita (unit:)',
    'Diversity of Schools Index (unit:)',
    "PM 2.5 concentration (unit: µg/m3)",
    "Total Methane Emissions (unit: tonnes)",
    "Total CO2-Equivalent Emissions (unit: tonnes)",
    'Waste Disposal Points Per 10000 (unit:)',
    'Share of Population without proper Access to Waste Disposal (unit: %)',
    "geometry"]

DELTA_THRESHOLDS = {"good": 0.10, "warn": 0.03}

CHART_COLORS = {
    "region_good": "#2e7d32",
    "region_bad": "#c62828",
    "region_neutral": "#757575",
    "national": "#1e88e5",
}

SCORE_COLS_DICT = {"Prosperity Score": [
                "Energy Access Score",
                ],
            "Infrastructure Score": [
                "Digitalization Score",
                "Sustainable Transport Score",

                ],
            "Livability Score": [
                "Education Score",
                "Health Score",
                "Environment Score",
            ]
            }

SUB_COLS_DICT = {"Energy Access Score": [
                'Luminosity Score', 'Luminosity per Capita Score',
                'Luminosity per Area Score', 'Area Lit Score', 'Population Lit Score'
                ],
            "Digitalization Score": [
                'Key Structure Internet Score',
                'Mobile Internet Score',
                'Key Structure Internet Access Score',
            ],
            "Education Score": [
                'Accessibility to Schools Score',
                'Number of Schools per Capita Score',
                'Diversity of Schools Index Score'
                ],
            "Health Score": [
                'Accessibility to Hospitals Score',
                'Number of Hospitals per Capita Score',
                'Diversity of Health Services Score'
                ],
            "Sustainable Transport Score": [
                'Railway Density Score',
                'Road Density Score',
                'Railway Flood Score',
                'Road Flood Score',
                'Railway Heatwave Score',
                'Road Heatwave Score'
                ],
            "Environment Score": [
                'CO2e-Emissions Score', 
                'Methane-Emissions Score',
                'Air Quality Score',
                'Waste Disposal Score',
                'Waste Disposal Gap Score'
                
            ]
            }

# Optional manual source badges per indicator (extend as needed)
INDICATOR_SOURCES = {
    "PM 2.5 concentration (unit: µg/m3)": [
        {"label": "OpenWeatherMaps Air Pollution", "url": "https://openweathermap.org/api/air-pollution"},
    ],
    "NO2 concentration (unit: µg/m3)": [
        {"label": "OpenWeatherMaps Air Pollution", "url": "https://openweathermap.org/api/air-pollution"},
    ],
    "PM 10 concentration (unit: µg/m3)": [
        {"label": "OpenWeatherMaps Air Pollution", "url": "https://openweathermap.org/api/air-pollution"},
    ],
    "Accessibility to Health Services (unit: %)": [
        {"label": "OpenStreetMaps", "url": "https://openstreetmap.org/"},
        {"label": "WorldPop New Global 2 Population Data", "url": "https://hub.worldpop.org/project/categories?id=3"},
    ],
    "Accessibility to School Services (unit: %)": [
        {"label": "OpenStreetMaps", "url": "https://openstreetmap.org/"},
        {"label": "WorldPop New Global 2 Population Data", "url": "https://hub.worldpop.org/project/categories?id=3"},
    ],
    "Diversity of Health Services": [
        {"label": "OpenWeatherMaps", "url": "https://openweathermap.org/"},
    ],
    "Key Structure Average Broadband Download Speed (unit: megabites per second)": [
        {"label": "Ookla Speedtest Global Performance", "url": "https://registry.opendata.aws/speedtest-global-performance/"},
        {"label": "OpenStreetMaps", "url": "https://openstreetmap.org/"},
    ],
    "Average Cellular Download Speed (unit: megabites per second)": [
        {"label": "Ookla Speedtest Global Performance", "url": "https://registry.opendata.aws/speedtest-global-performance/"},
    ],
    "Key Structures without Internet Access (unit: %)": [
        {"label": "Ookla Speedtest Global Performance", "url": "https://registry.opendata.aws/speedtest-global-performance/"},
        {"label": "OpenStreetMaps", "url": "https://openstreetmap.org/"},
    ],
    "Road flood risk per capita (unit: km per capita)": [
        {"label": "OpenStreetMaps", "url": "https://openstreetmap.org/"},
        {"label": "WorldPop New Global 2 Population Data", "url": "https://hub.worldpop.org/project/categories?id=3"},
        {"label": "WRI Aqueduct Floods Hazard Maps Version 2", "url": "https://developers.google.com/earth-engine/datasets/catalog/WRI_Aqueduct_Flood_Hazard_Maps_V2"},
        {"label": "PIMxPAM Climate Risk Threshold Database", "url": "https://gpbprtd.eu.pythonanywhere.com/"},
    ],
    "Road heatwave risk per capita (unit: km per capita)": [
        {"label": "OpenStreetMaps", "url": "https://openstreetmap.org/"},
        {"label": "WorldPop New Global 2 Population Data", "url": "https://hub.worldpop.org/project/categories?id=3"},
        {"label": "ERA5 Hourly Reanalysis", "url": "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview"},
        {"label": "PIMxPAM Climate Risk Threshold Database", "url": "https://gpbprtd.eu.pythonanywhere.com/"},
    ],
    "Railway flood risk per capita (unit: km per capita)": [
        {"label": "OpenStreetMaps", "url": "https://openstreetmap.org/"},
        {"label": "WorldPop New Global 2 Population Data", "url": "https://hub.worldpop.org/project/categories?id=3"},
        {"label": "WRI Aqueduct Floods Hazard Maps Version 2", "url": "https://developers.google.com/earth-engine/datasets/catalog/WRI_Aqueduct_Flood_Hazard_Maps_V2"},
        {"label": "PIMxPAM Climate Risk Threshold Database", "url": "https://gpbprtd.eu.pythonanywhere.com/"},
    ],
    "Railway heatwave risk per capita (unit: km per capita)": [
        {"label": "OpenStreetMaps", "url": "https://openstreetmap.org/"},
        {"label": "WorldPop New Global 2 Population Data", "url": "https://hub.worldpop.org/project/categories?id=3"},
        {"label": "ERA5 Hourly Reanalysis", "url": "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview"},
        {"label": "PIMxPAM Climate Risk Threshold Database", "url": "https://gpbprtd.eu.pythonanywhere.com/"},
    ],
    "Emissions from all sources (unit: kgCO2e/kg)": [
        {"label": "Climate Trace", "url": "https://climatetrace.org/data"},
    ],
    "Emissions from Coal Power Plants (unit: kgCO2e/kg)": [
        {"label": "Climate Trace", "url": "https://climatetrace.org/data"},
    ],
    "Agriculture Emissions (unit: kgCO2e/kg)": [
        {"label": "Climate Trace", "url": "https://climatetrace.org/data"},
    ],
    "Forestry & Land Use Emissions (unit: kgCO2e/kg)": [
        {"label": "Climate Trace", "url": "https://climatetrace.org/data"},
    ],
    "Nighttime Luminosity (unit: nWatts/(cm2 x sr)": [
        {"label": "VIIRS Nighttime Day/Night Band Composites Version 1", "url": "https://developers.google.com/earth-engine/datasets/catalog/NOAA_VIIRS_DNB_MONTHLY_V1_VCMCFG"},
    ],
}

# --- Scatterplot Configuration ---
LIVABILITY_INDICATORS = [
    "Accessibility to Healthcare Services (unit: %)",
    "Accessibility to School Services (unit: %)",
    "Diversity of Health Services",
    "PM 2.5 concentration (unit: µg/m3)",
    "PM 10 concentration (unit: µg/m3)",
    "NO2 concentration (unit: µg/m3)",
    "Total Methane Emissions (unit: tonnes)",
    "Total CO2-Equivalent Emissions (unit: tonnes)",
    "Total CO2-Equivalent Emissions from Coal Power Plants (unit: tonnes)",
    "Livability Score"
]

PROSPERITY_INDICATORS = [
    "Nighttime Luminosity (unit: nWatts/(cm2 x sr)",
    "Key Structure Average Broadband Download Speed (unit: megabites per second)",
    "Average Cellular Download Speed (unit: megabites per second)",
    "Key Structures without Internet Access (unit: %)",
    "Railway Flood Risk (unit: %)",
    "Road Flood Risk (unit: %)",
    "Railway Heatwave Risk (unit: %)",
    "Road Heatwave Risk (unit: %)",
    "Prosperity Score"
]

# Quadrant colors for 2D scatter
QUADRANT_COLORS = {
    "high_high": "green",
    "high_low": "yellow",
    "low_high": "yellow",
    "low_low": "red"
}

# Spatial autocorrelation colors
SPATIAL_AUTOCORR_COLORS = {
    "Not Significant": "lightgrey",
    "High-High (Hotspot)": "red",
    "Low-Low (Coldspot)": "lightblue",
    "High-Low": "green",
    "Low-High": "yellow",
}

SPATIAL_AUTOCORR_LABELS = [
    "Not Significant",
    "High-High (Hotspot)",
    "Low-Low (Coldspot)",
    "High-Low",
    "Low-High",
]

