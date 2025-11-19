import streamlit as st

# Custom CSS for resources page with centered content
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
        
        /* Resource boxes */
        .resource-box {
            background-color: #f8fafc;
            padding: 1.5rem;
            margin: 1.5rem 0;
            border-radius: 4px;
        }
        
        .resource-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 0.75rem;
        }
        
        .resource-description {
            color: #4b5563;
            line-height: 1.6;
            margin-bottom: 1rem;
        }
        
        .resource-link {
            display: inline-block;
            color: #0066cc;
            font-weight: 500;
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
st.markdown("# Resources")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)

st.markdown("""
Access comprehensive documentation and resources to understand and effectively use the Local Development Tracker Decision Engine. These materials provide technical details, policy context, and practical guidance for different stakeholder groups.
""")

st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)

# Resource 1: Pitch Deck
st.markdown("""
<div class="resource-box">
    <div class="resource-title">📊 LDT Decision Engine Pitch Deck</div>
    <div class="resource-description">
        A comprehensive presentation introducing the Local Development Tracker Decision Engine, its objectives, 
        and value proposition. This deck provides an overview of the tool's capabilities, target users, 
        and expected impact on regional development planning in Serbia. Ideal for stakeholders seeking 
        a high-level understanding of the platform and its role in the broader GPBP ecosystem.
    </div>
    <a href="https://docs.google.com/presentation/d/19iGMTUGeB7LNRGnFxKTYuRexLW0OjAmn/edit?slide=id.g2e47b9337ae_0_98#slide=id.g2e47b9337ae_0_98" 
       target="_blank" class="resource-link">→ View Pitch Deck</a>
</div>
""", unsafe_allow_html=True)

# Resource 2: EIG Report
st.markdown("""
<div class="resource-box">
    <div class="resource-title">🌍 Enhancing Infrastructure Governance (EIG) Report for WeBA6</div>
    <div class="resource-description">
        Detailed documentation on climate-informed Public Investment Management (PIM) in the Western Balkans, 
        including Serbia. This report contextualizes the LDT-DE within broader infrastructure governance strategies for the region. 
        Essential reading for policymakers and development partners working on public investment management (PIM) and sustainability initiatives in the Western Balkans.
    </div>
    <a href="https://docs.google.com/document/d/1eoCPpdTx9z5NI2lX20aAFzLC1_kHGVfd/edit?usp=sharing&ouid=107640506223612923418&rtpof=true&sd=true" 
       target="_blank" class="resource-link">→ Read EIG Report</a>
</div>
""", unsafe_allow_html=True)

# Resource 3: Technical Documentation
st.markdown("""
<div class="resource-box">
    <div class="resource-title">📘 GPBP-LDT-DE Technical Documentation</div>
    <div class="resource-description">
        Comprehensive technical documentation covering the LDT-DE's architecture, data sources, indicator 
        calculations, and analytical methodologies. This resource provides in-depth information for technical 
        users, researchers, and data scientists interested in understanding how the platform processes 
        geospatial data and generates municipal rankings. Includes details on AI integration and 
        data processing pipelines.
    </div>
    <a href="https://docs.google.com/document/d/1IaHR46oQ8gcmZwwIH6LLMGyyl76Cf0nsgvEY0wuf9OM/edit?usp=sharing" 
       target="_blank" class="resource-link">→ Access Technical Documentation</a>
</div>
""", unsafe_allow_html=True)

        
st.markdown("<hr style='border: 1px solid #ddd; margin: 2rem 0;'>", unsafe_allow_html=True)

# Additional Resources Section
st.markdown("""
## Additional Resources

For more information about the broader GPBP ecosystem and complementary tools, visit:
- **[PimPam Network](https://pim-pam.net/)** – Explore the full suite of geospatial planning tools

## Contact and Inquiries

For questions about these resources or to request additional documentation, please contact:
- **Email**: [kkaiser@worldbank.org](kkaiser@worldbank.org) or [sonle.h96@gmail.com](sonle.h96@gmail.com)
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
    if st.button("🚀 Launch the LDT Decision Engine", use_container_width=True, key="launch_from_resources"):
        st.switch_page("gpbp-ldt-de.py")
        
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
    st.image("data/wbg logo.png")

with col3:
    st.image("data/VDKC-Logo-Color.jpg")
    
with col4:
    st.image("data/ASG_Logo.png")
    
with col5:
    st.write("")

# Copyright
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem; margin-top: 2rem;'>
    <p>© 2024 World Bank Group | <a href="https://pim-pam.net/" target="_blank">PimPam GPBP</a></p>
</div>
""", unsafe_allow_html=True)