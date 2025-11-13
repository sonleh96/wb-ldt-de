import streamlit as st

st.markdown(
            """
    <style>
        /* Force all markdown text to align left */
        .stMarkdown, .stMarkdown div, .sidebar-text {
            text-align: left !important;
            font-family: Arial, sans-serif;
            font-size: 0.9rem;
            color: black;
            line-height: 1.5;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.write("### 🌍 About the App")
st.markdown(
            """
            <div class="sidebar-text">
                <strong>The Geospatial Planning & Budgeting Platform (GPBP) Local Development Tracker Decision Engine (LDT-DE)</strong> harnesses regional geospatial data developed by the LDT to help policymakers prioritize projects focused on 
                regional environmental and economic development. It was developed by the World Bank Group as part of the 
                <a href="https://pim-pam.net/" target="_blank">PimPam Network</a>.
                This tool not only centralizes and streamlines various remote sensing and geospatial data sources, but also leverages key insights from complementary platforms and digital apps on the PimPam GPBP, such as:
                <li><a href="https://cbd.pim-pam.net/" target="_blank">Country Benchmarking Dashboard</a> (CBD)</li>
                <li><a href="https://gpbp.adamplatform.eu/" target="_blank">Climate Change Screening Tool</a> (CCS)</li>
                <li><a href="https://gpbprtd.eu.pythonanywhere.com/" target="_blank">Climate Risk Threshold Database</a> (RTD)</li>
                <li><a href="https://www.figma.com/proto/MRIuLeqyVOFGJQwVi0sVAg/PIA-final?node-id=14101-76623&p=f&t=wMUuiwyzr7W56K36-0&scaling=min-zoom&content-scaling=fixed&page-id=14101%3A64991&starting-point-node-id=14101%3A76623" target="_blank">Public Infrastructure Access Tool</a> (PIA)</li>
            </div>
            """,
            unsafe_allow_html=True
        )
st.markdown("<hr style='border: 1px solid #ccc;'>", unsafe_allow_html=True)
st.write('### 📄 Documentation')
st.markdown("""
        <div class ="sidebar-text">
            The following documentation regarding the GPBP LDT - DE is available:
            <li><a href="https://docs.google.com/presentation/d/19iGMTUGeB7LNRGnFxKTYuRexLW0OjAmn/edit?slide=id.g2e47b9337ae_0_98#slide=id.g2e47b9337ae_0_98" 
                target="_blank">Pitch Deck</a></li>
            <li><a href="https://docs.google.com/document/d/1eoCPpdTx9z5NI2lX20aAFzLC1_kHGVfd/edit?usp=sharing&ouid=107640506223612923418&rtpof=true&sd=true" target="_blank">EIG in the WeBA6</a></li>
            <li><a href="https://docs.google.com/document/d/17LhzOH-EnxfAWaBF8_FHCup8E_fsDe4p0VVfrUG4Aac/edit?usp=sharing" target="_blank">Indicator Methodology</a></li>
            <li><a href="https://docs.google.com/document/d/1IaHR46oQ8gcmZwwIH6LLMGyyl76Cf0nsgvEY0wuf9OM/edit?usp=sharing" target="_blank">Technical Documentation</a></li>
        </div>
        """, unsafe_allow_html=True)
st.markdown("<hr style='border: 1px solid #ccc;'>", unsafe_allow_html=True)
st.write("### ⚠️ Disclaimer")
st.markdown(
            """
            <div class="sidebar-text">
                <p>
                    The <strong>GPBP Tools</strong> leverage <strong>Generative AI</strong> to analyze data and suggest region-specific and project-level recommendations.
                </p>
                <p>
                    While we strive to deliver <strong>high-quality and accurate outputs</strong>, AI-generated responses may occasionally contain
                    <strong>inaccuracies, outdated information</strong>, or <strong>unintended biases</strong>. Additionally, due to the probabilistic nature of generative AI, 
                    the system may produce <strong>slightly different recommendations</strong> across sessions—even when provided with similar inputs.
                </p>
                <p>
                    We strongly recommend that users <strong>verify critical information independently</strong> before making decisions based on these outputs.
                </p>
            </div>
        """,
        unsafe_allow_html=True
        )
st.markdown("<hr style='border: 1px solid #ccc;'>", unsafe_allow_html=True)