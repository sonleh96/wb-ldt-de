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
        
        /* Green launch button styling */
        .stButton > button {
            background-color: green !important;
            color: white !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            padding: 15px 40px !important;
            border-radius: 8px !important;
            border: none !important;
            cursor: pointer !important;
            transition: all 0.3s !important;
            min-height: 60px !important;
        }
        
        .stButton > button:hover {
            background-color: #059669 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
        }
        
        .columns-section {
            padding: 0 3rem;
        }
        
        /* Footer section */
        .footer-section {
            text-align: center;
            padding: 20px 20px 0 20px;
        }
        
        .footer-text {
            color: #1e3a8a;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 60px;
        }
        
        @media (max-width: 768px) {
            .columns-section {
                padding: 0 1.5rem;
            }
            
            .stButton > button {
                font-size: 1.2rem;
                padding: 20px 40px;
                min-height: 60px;
            }
        }
    </style>
""", unsafe_allow_html=True)



# Main title
# st.write("# About")

# st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)

st.image("images/about image 1.jpg", use_container_width=True)

# Opening narrative with real-world context
st.markdown("""
In 2014, devastating floods swept across Serbia and the Western Balkans, displacing over 30,000 people and causing an estimated €1.5 billion in damages. The disaster exposed significant infrastructure vulnerabilities and revealed stark disparities in how different communities could prepare for, withstand, and recover from such events. Some municipalities had the resources and planning capacity to respond effectively. Many did not.

## Understanding development disparities is critical to building regional resilience and prosperity

Serbia's municipalities face diverse and complex development challenges. While some regions thrive with robust infrastructure, economic opportunities, and access to essential services, others struggle with aging infrastructure, limited connectivity, environmental degradation, and shrinking populations. Decades of uneven investment, geographic isolation, and economic restructuring have created disparities across the country – making it harder for certain communities to achieve sustainable development and climate resilience.

## Visualizing development needs across Serbia

The **Local Development Tracker Decision Engine (LDT-DE)** visualizes how drivers of development challenges affect municipalities across Serbia. By integrating geospatial data, remote sensing, and advanced analytics, the LDT-DE provides a comprehensive view of each municipality's strengths and vulnerabilities across three critical pillars:

- **Prosperity** – Measures economic vitality through energy access and consumption patterns. Using nighttime luminosity data, this pillar assesses how effectively municipalities provide energy to their populations and built-up areas, serving as a proxy for economic development and industrial activity.

- **Livability** – Evaluates quality of life through education, health, and environmental conditions. This pillar examines access to healthcare and educational services, solid waste management capacity, greenhouse gas emissions, and air quality to understand how well municipalities support human development and environmental sustainability.

- **Infrastructure** – Assesses the availability and resilience of critical infrastructure systems. This pillar focuses on digital connectivity, transportation networks (road and rail), and the vulnerability of these systems to climate risks, measuring a municipality's capacity to provide and maintain essential services.

Better understanding of the intersections between economic development, quality of life, and infrastructure resilience is critical to effectively targeting investments where they are needed most. The LDT-DE provides a robust, data-driven approach to understanding locally relevant conditions at the municipal scale.

Comprising indicators across multiple development domains – from energy access and digital connectivity to healthcare accessibility and transportation networks – this analytical tool integrates the cumulative factors that shape a community's development trajectory. Equipping policymakers with actionable data enables them to prioritize resources, allocate funding strategically, and advocate for the changes their communities need.

""")

st.image("images/About image 2.webp", use_container_width=True)

st.markdown("""
## Making investments where they are needed most

The Serbian government and international development partners, including the World Bank Group, are making significant investments to improve equity and build resilience in vulnerable communities. But the right investments must flow to the right places for these efforts to be effective. The LDT-DE is instrumental in empowering communities and policymakers to better prioritize resources and target interventions.

In particular, the LDT-DE gives planners, local government officials, national agencies, development partners, and research teams a means to:
- **Identify priority areas** for infrastructure and social investments
- **Track progress** over time with quantitative indicators
- **Align projects** with national and regional development strategies
- **Access grant opportunities** by demonstrating evidence-based needs
- **Advocate for resources** using transparent, data-driven insights

The tool provides community-based organizations and local governments access to actionable data that can help them compete for funding, demonstrate impact, and advocate for increased support where it matters most.

## Comprehensive, data-driven view of municipal development

With support from the Serbian Ministry of Finance, the Republic Geodetic Authority, and multiple World Bank teams, the LDT-DE represents the most thorough compilation of development indicators at the municipal level across Serbia – integrating economic, environmental, infrastructure, and social metrics from diverse sources.

From the beginning, local government partners and national stakeholders were included in the development of the LDT-DE. The team adopted a holistic, systems-based approach that considers the cumulative impacts of multiple development factors. They identified and evaluated both comprehensive national datasets and granular geospatial data. Feedback from government partners at each stage of development ensured the tool included data reflecting real priorities and challenges, which is crucial for effective policymaking and helps ensure programs meet actual needs on the ground.

Additionally, this extensive evaluation highlighted important gaps where comprehensive data are lacking, such as gender-disaggregated indicators, detailed environmental health outcomes, water quality monitoring, and localized climate adaptation measures. The LDT-DE can elevate these gaps and motivate needed investments in data infrastructure and research.

## Integration with the PimPam GPBP Ecosystem

The LDT-DE is part of the broader **Geospatial Planning & Budgeting Platform (GPBP)**, developed by the World Bank Group as part of the [PimPam Network](https://pim-pam.net/). This tool not only centralizes and streamlines various remote sensing and geospatial data sources, but also leverages key insights from complementary platforms and digital apps in the GPBP ecosystem:

- **[Country Benchmarking Dashboard (CBD)](https://cbd.pim-pam.net/)** – Compare Serbia's performance against regional and international benchmarks
- **[Climate Change Screening Tool (CCS)](https://gpbp.adamplatform.eu/)** – Assess climate risks and vulnerabilities for specific projects and locations
- **[Climate Risk Threshold Database (RTD)](https://gpbprtd.eu.pythonanywhere.com/)** – Access standardized climate risk thresholds for environmentally conscious Cost-Benefit Analysis
- **[Public Infrastructure Access Tool (PIA)](https://www.figma.com/proto/MRIuLeqyVOFGJQwVi0sVAg/PIA-final?node-id=14101-76623&p=f&t=wMUuiwyzr7W56K36-0&scaling=min-zoom&content-scaling=fixed&page-id=14101%3A64991&starting-point-node-id=14101%3A76623)** – Map accessibility to critical public infrastructure

By integrating these complementary tools, the LDT-DE provides a 360-degree view of development challenges and opportunities, enabling more informed, evidence-based decision-making for sustainable and equitable regional development.
""")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)

# Call to action section
st.markdown("""
## Explore the LDT Decision Engine

Ready to see how your municipality ranks across development indicators? Launch the tool to explore interactive visualizations, compare municipalities, and access AI-powered insights for evidence-based planning.
""")

st.markdown("", unsafe_allow_html=True)
st.markdown("", unsafe_allow_html=True)

# Launch Button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 Launch the LDT Decision Engine", use_container_width=True, key="launch_from_about"):
        st.switch_page("gpbp-ldt-de.py")

st.markdown("<div style='margin: 40px 0;'></div>", unsafe_allow_html=True)

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)

# Contact and footer
st.markdown("""
## Contact and Inquiries

For questions, feedback, or partnership opportunities, please contact:
- **Email**: [kkaiser@worldbank.org](mailto:kkaiser@worldbank.org) or [sonle.h96@gmail.com](mailto:sonle.h96@gmail.com)
- **PimPam Network**: [https://pim-pam.net/](https://pim-pam.net/)
""")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)

# Footer Section
st.markdown('<div class="columns-section">', unsafe_allow_html=True)
st.markdown("""
    <div class="footer-section">
        <div class="footer-text">
            Implemented by
        </div>
    </div>
""", unsafe_allow_html=True)

# Organization Logos
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

with col1:
    st.write("")
    
with col2:
    st.image("images/wbg logo.png")

with col3:
    st.image("images/VDKC-Logo-Color.jpg")
    
with col4:
    st.image("images/ASG_Logo.png")
    
with col5:
    st.write("")

# Copyright
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem; margin-top: 2rem;'>
    <p>© 2024 World Bank Group | <a href="https://pim-pam.net/" target="_blank">PimPam GPBP</a></p>
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Close columns-section

