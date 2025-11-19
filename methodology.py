import streamlit as st

# Custom CSS for methodology page with centered content
st.markdown("""
    <style>
        /* Set max width for content container and center it */
        .block-container {
            max-width: 1200px !important;
            padding-left: 5rem !important;
            padding-right: 5rem !important;
        }
        
        @media (max-width: 1024px) {
            .block-container {
                padding-left: 3rem !important;
                padding-right: 3rem !important;
            }
        }
        
        @media (max-width: 768px) {
            .block-container {
                padding-left: 2rem !important;
                padding-right: 2rem !important;
            }
        }
        
        /* Force all markdown text to align left */
        .stMarkdown, .stMarkdown div {
            text-align: left !important;
            font-family: Arial, sans-serif;
            color: #333;
            line-height: 1.6;
        }
        
        /* Heading styles */
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            color: #1a1a1a;
        }
        
        h2 {
            font-size: 1.8rem;
            font-weight: 600;
            margin-top: 2rem;
            margin-bottom: 1rem;
            color: #2c3e50;
        }
        
        h3 {
            font-size: 1.4rem;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            color: #34495e;
        }
        
        /* Paragraph spacing */
        p {
            margin-bottom: 1rem;
            font-size: 1rem;
        }
        
        /* List styling */
        ul {
            margin-bottom: 1rem;
            padding-left: 2rem;
        }
        
        li {
            margin-bottom: 0.5rem;
        }
        
        /* Strong text */
        strong {
            font-weight: 600;
            color: #2c3e50;
        }
        
        /* Links */
        a {
            color: #0066cc;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        /* Info boxes */
        .methodology-note {
            background-color: #e8f4f8;
            border-left: 4px solid #0066cc;
            padding: 1rem;
            margin: 1.5rem 0;
            border-radius: 4px;
        }
        
        /* Figure caption */
        .figure-caption {
            font-style: italic;
            color: #666;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# Main title
st.markdown("# Methodology")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)

# Introduction
st.markdown("""
## Overview

The **GPBP Local Development Tracker Decision Engine (LDT-DE)** provides a comprehensive framework for 
evaluating municipal development priorities in Serbia. The methodology combines quantitative indicators 
across multiple domains with AI-powered analysis to support evidence-based decision-making for regional 
development investments.

This page describes the data sources, processing methods, and analytical framework that underpin the 
LDT-DE platform.
""")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)

# Indicator Selection
st.markdown("## Indicator Selection and Framework")

st.markdown("""
The LDT-DE utilizes a multi-dimensional approach to assess municipal development needs and priorities. 
Indicators were selected based on:

- Expertise from **World Bank sector specialists** in climate change, infrastructure, and Public Investments Management (PIM).
- Engagement with **Serbian government partners** including the Ministry of Finance (MoF) and the Republic Geodetic Authority (RGA).
- Feedback provided by **Local Governments** from municipalities across Serbia (e.g Veliko Gradiste, etc...).
- Selection framework based on the **Western Balkans Investment Framework (WBIF)**.

Indicators span three key pillars: **Prosperity**, **Livability**, and **Infrastructure**. Each pillar is composed of key development domains defined by the WBIF.
""")

st.image("data/Indicators Map.png", use_container_width=True)

st.markdown("### Development Domains")

st.markdown("""
**Prosperity** indicators focus on the region's ability to provide energy, as a proxy to economic development, to its population. It is currently composed of the *Energy Access* domain.
- Access to energy, with the use of nighttime luminosity to measure how easily a region's population and built up areas have access to energy.
- Intensity of energy consumption, using luminosity to measure how much energy is consumed per capita and per area.

**Livability** indicators measure the region's ability to provide various aspects of human development. It is currently composed of the *Education*, *Health*, and *Environment* domains.
- Solid waste management systems accessibility and stress.
- Emissions of Greenhouse Gases and Air Quality.
- Access to services for human development, such as healthcare and education.

**Infrastructure** indicators focus on the region's ability to provide and maintain basic infrastructure to its population. It is currently composed of the *Digitalization*, *Sustainable Transport* domains.
- Transportation networks (road, rail connectivity) and their vulnerability to climate risks.
- Digital connectivity and performance.
""")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)
# Data Sources
st.markdown("## Data Sources")

st.markdown("""
The LDT-DE integrates geospatial data from multiple publicly and globally available sources to ensure comprehensive and reliable, yet scalable 
municipal-level analysis. Data sources include:

### Satellite Data
- **VIIRS Nighttime Day/Night Band Composites Version 1** - nighttime luminosity data at raster level (100m resolution)

### Geospatial Data
- **GADM (Global Administrative Areas)** - administrative boundaries at municipal and district levels
- **WorldPop** - population data at raster level (100m resolution)
- **OpenStreetMap** - road networks, points of interest, and infrastructure locations
- **Copernicus Earth Observation** - meteorological monitoring
- **World Bank Geospatial Data** - poverty mapping, accessibility analysis, and climate data
- **WRI Flood Hazard Maps** - flood risk data at raster level (30m resolution)
- **Climate Trace** - greenhouse gas emissions data at point level, spanning all sectors and countries.
- **OpenWeatherMaps** - ground surface air pollution data at raster level (~5km resolution)

### International Organizations
- **Western Balkans Investment Framework (WBIF)** - project database and investment tracking
- **World Bank Group** - GPBP digital PIM-PAM tools for asset based indicators and country-level context. 

### Official Sources
- Municipal Development Plans and Strategies
- Official Sources for vetted information.

### Data Coverage and Resolution
- **Geographic Resolution**: Municipality level - 145 municipalities and 29 cities across Serbia
- **Temporal Coverage**: Primarily 2021-2024, with historical trends and future projections where available
- **Update Frequency**: Annual updates for statistical indicators; project data updated when new data becomes available.
""")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)
# Data Processing
st.markdown("## Data Processing and Integration")

st.markdown("""
### Data Processing
All data obtained in GIS formats (vector, raster) was computed on the Municipal level and outputted to CSV files using data processing pipelines created in Python and Google Earth Engine. Raster-based datasets aggregated pixel values within municipal boundaries. 
Point-based infrastructure data are spatially joined to municipal polygons. Network data (roads, utilities) are aggregated by municipality. Time-series data are interpolated or extrapolated where gaps exist, within reason, and annualized for temporal consistency.
Certain indicators are normalized to population or area, where appropriate. All indicators are standardized to the 0-100 scale, grouped by years in order to integrate them into the same scoring framework. Outliers are manually reviewed and adjusted where appropriate.

Text-based indicators are extracted from project documents, strategies, and reports. They are then summarized, extracted for key information, and stored in a database to be used for the AI-powered analysis. Only information from official or vetted sources is used 
to ensure reliability and transparency. More information on the data sources can be found in the [GPBP Master Data Catalogue](https://docs.google.com/spreadsheets/d/1xsWi5HChiHtk--TzHkbswFWvmYxjTpI2HzSDrrJVOZU/edit?gid=835116754#gid=835116754).
For how the indicators were individually computed, please refer to the [Indicator Methodology](https://docs.google.com/document/d/17LhzOH-EnxfAWaBF8_FHCup8E_fsDe4p0VVfrUG4Aac/edit?usp=sharing).
""")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)
# Scoring and Aggregation
st.markdown("## Scoring and Aggregation")

st.markdown("""
To compute the main scores from the indicators in a standardized manner, the Toxicological Prioritization Index (ToxPI) approach (Marvel et al. 2018; Reif et al. 2013; Bhandari et al. 2020; Lewis et al. 2023) was used, which has been used extensively to communicate risk prioritization and profiling information. 
ToxPI utilizes a weighted average to aggregate data to provide an overall relative aggregate score. Each indicator used to compute the categories was equally weighted upon aggregation. Scores were converted to percentiles from 0 – 100, where higher values indicate greater performance. 
Each indicator, category, and score were equally weighted at each aggregation level. This ensures that the scores are fair and transparent, and that the scores are not biased by the weighting of the indicators.
This methodology has been previously utilized by the US Environmental Defense Fund's [Climate Vulnerability Index](https://www.climatevulnerabilityindex.org/) tool.
""")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)

# AI Integration
st.markdown("## AI-Powered Analysis")

st.markdown("""
The LDT-DE leverages Large Language Models (LLMs) to enhance data analysis and interpretation:

### Natural Language Processing
- **Document Analysis**: Extraction of key information from project documents, strategies, and reports
- **Comparative Analysis**: Generation of narrative summaries comparing municipalities
- **Recommendation Synthesis**: AI-generated investment recommendations based on multi-indicator analysis

### Use Cases
1. **Gap Analysis**: Identify gaps in Prosperity, Livability, and Infrastructure relative to national benchmarks
2. **Project Alignment**: Match municipal needs with existing WBIF projects and eligibility criteria
3. **Best Practice Identification**: Surface successful interventions on the subnational and national level in the Western Balkans.

### Quality Assurance
- All AI-generated content is flagged as such for user transparency
- Recommendations are grounded in quantitative data and cite specific indicators
- Human expert review for critical decision-support outputs
- Continuous model evaluation and refinement based on user feedback
""")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)
# Limitations
st.markdown("## Limitations and Considerations")

st.markdown("""
Users should be aware of several important limitations:

### Data Limitations
- **Timeliness**: Data before 2021 is not available for all indicators.
- **Completeness**: OpenSteetMap data is often missing, incompletely, or outdated. 
- **Granularity**: Municipal-level data may mask intra-municipal variation
- **Comparability**: Differences in data collection methods across sources may affect comparisons

### Methodological Considerations
- **Equal Weighting**: Default equal weights may not reflect all policy priorities; feedback is welcome to adjust the weights as needed.
- **Indicator Selection**: The indicator set is comprehensive but not exhaustive. Feedback is welcome to add new indicators as needed.

### AI-Related Considerations
- **Probabilistic Outputs**: AI-generated text may occasionally contain inaccuracies or hallucinations.
- **Context Limitations**: LLMs may lack specific local context not present in training data.
- **Interpretation**: AI recommendations should be validated by domain experts before informing decisions.

We recommend users:
- Validate critical findings against source data
- Consult with local stakeholders and experts
- Consider qualitative factors not captured in quantitative indicators
- Use the tool as **decision-support**, not decision-replacement.
""")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)
# References and Further Information
st.markdown("## References and Further Information")

st.markdown("""

### Contact

For questions about the methodology or data sources, please contact:
- **LDT-DE Product Owner**: Son Le at sonle.h96@gmail.com

### Acknowledgments

The LDT-DE methodology draws inspiration from established tools including the [U.S. Climate Vulnerability Index](https://www.climatevulnerabilityindex.org/), 
the [EU Regional Competitiveness Index](https://ec.europa.eu/regional_policy/information-sources/maps/regional-competitiveness_en), The Big Data Observatory,and various World Bank spatial planning frameworks. 
We acknowledge the Serbian Ministry of Finance, Republic Geodetic Authority, and our development partners 
for their data contributions and technical input.
""")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)

# Organization Logos - centered and sized with equal spacing
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

with col1:
    st.write("")
    
with col2:
    st.image("data/wbg logo.png")

with col3:
    st.image("data/VDKC-Logo-Color.jpg")
    
with col4:
    st.image("data/ASG_Logo.png")
    
with col5:
    st.write("")

# Version info
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85rem; margin-top: 2rem;'>
    <p><em>Methodology version 2.0 | Last updated: November 2025</em></p>
    <p>© 2024 World Bank Group | <a href="https://pim-pam.net/" target="_blank">PimPam Network</a></p>
</div>
""", unsafe_allow_html=True)
