import streamlit as st

# Custom CSS for the landing page inspired by Climate Vulnerability Index
st.markdown("""
    <style>
        /* Aggressively remove all default Streamlit padding and margins */
        html, body {
            margin: 0 !important;
            padding: 0 !important;
            overflow-x: hidden;
        }
        
        .stApp {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        [data-testid="stAppViewContainer"] {
            padding: 0 !important;
            margin: 0 !important;
        }
        
        .main {
            padding: 0 !important;
            margin: 0 !important;
            overflow-x: hidden;
        }
        
        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
        }
        
        .main > div:first-child {
            padding: 0 !important;
        }
        
        .element-container {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }
        
        /* Remove Streamlit's default responsive padding */
        @media (min-width: 576px) {
            .block-container {
                padding: 0 !important;
            }
        }
        
        @media (min-width: 768px) {
            .block-container {
                padding: 0 !important;
            }
        }
        
        @media (min-width: 1024px) {
            .block-container {
                padding: 0 !important;
            }
        }
        
        .content-wrapper {
            padding: 0;
        }
        
        .columns-section {
            padding: 0 3rem;
        }
        
        @media (max-width: 768px) {
            .columns-section {
                padding: 0 1.5rem;
            }
            
            .hero-section {
                padding: 60px 1.5rem 40px 1.5rem;
            }
            
            .hero-title {
                font-size: 2.5rem;
                margin-bottom: 40px;
            }
            
            .hero-description {
                font-size: 1.2rem;
            }
            
            .stButton > button {
                font-size: 1.2rem;
                padding: 20px 40px;
                min-height: 60px;
            }
        }
        
        /* Banner container - full width edge-to-edge */
        .banner-container {
            width: 100vw !important;
            max-width: 100vw !important;
            margin: 0 !important;
            padding: 0 !important;
            position: relative;
            left: 50%;
            right: 50%;
            margin-left: -50vw !important;
            margin-right: -50vw !important;
            overflow: hidden;
        }
        
        .banner-container img {
            width: 100% !important;
            max-width: 100% !important;
            display: block;
            margin: 0 !important;
            padding: 0 !important;
            object-fit: cover;
        }
        
        /* Override Streamlit's image container */
        .banner-container .stImage {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        .banner-container [data-testid="stImage"] {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* Hero section */
        .hero-section {
            text-align: center;
            padding: 80px 3rem 60px 3rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .hero-title {
            font-size: 4rem;
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 60px;
            color: #1e3a8a;
            margin-left: auto;
            margin-right: auto;
        }
        
        .hero-description {
            font-size: 10 rem;
            line-height: 1.8;
            margin-bottom: 50px;
            color: #4b5563;
            margin-left: auto;
            margin-right: auto;
        }
        
        /* Launch button styling - for main hero button only */
        .stButton > button:not(div.card-button-wrapper button) {
            background-color: green;
            color: white;
            font-size: 10rem;
            font-weight: 800;
            padding: 25px 60px;
            border-radius: 12px;
            border: none;
            cursor: pointer;
            transition: all 0.3s;
            min-height: 80px;
        }
        
        .stButton > button:not(div.card-button-wrapper button):hover {
            background-color: #1e40af;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(30, 58, 138, 0.3);
        }
        
        /* Card button link styling - MUST come BEFORE general button styling */
        div.card-button-wrapper button,
        div.card-button-wrapper button[data-testid="baseButton-primary"],
        div.card-button-wrapper .stButton button {
            background-color: ##9fc5e8 !important;
            color: #9fc5e8 !important;
            font-size: 1rem !important;
            font-weight: 600 !important;
            padding: 12px 24px !important;
            border-radius: 6px !important;
            border: 2px solid #9fc5e8 !important;
            min-height: auto !important;
            width: 100% !important;
        }
        
        div.card-button-wrapper button:hover,
        div.card-button-wrapper button[data-testid="baseButton-primary"]:hover,
        div.card-button-wrapper .stButton button:hover {
            background-color: #0284c7 !important;
            color: #9fc5e8 !important;
            border-color: #9fc5e8 !important;
            transform: translateY(-1px) !important;
        }
        
        
        
        /* Section styling */
        .content-section {
            padding: 60px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .section-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 20px;
            color: #1e3a8a;
        }
        
        .section-description {
            font-size: 1.1rem;
            line-height: 1.7;
            color: #4b5563;
            margin-bottom: 30px;
        }
        
        /* Card styling */
        .info-card {
            background: #f8fafc;
            padding: 25px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        
        .card-title {
            font-size: 1.4rem;
            font-weight: 600;
            color: #03a1fc;
            margin-bottom: 15px;
        }
        
        .card-text {
            font-size: 1rem;
            line-height: 1.6;
            color: #4b5563;
            flex-grow: 1;
        }
        
        .card-text ul {
            margin-top: 10px;
            padding-left: 20px;
        }
        
        .card-text li {
            margin-bottom: 8px;
        }
        
        /* Footer section */
        .footer-section {
            margin-top: 80px;
            padding: 20px 20px 0 20px;
            text-align: center;
        }
        
        .footer-text {
            color: #6b7280;
            font-size: 1rem;
            margin-bottom: 30px;
        }
        
        /* Logo alignment */
        [data-testid="column"] img {
            display: block;
            margin-left: auto;
            margin-right: auto;
        }
        
        /* Link styling */
        a {
            color: #1e3a8a;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        /* Divider */
        .section-divider {
            height: 2px;
            background: linear-gradient(to right, transparent, #ffffff, transparent);
            margin: 60px 3rem;
        }
        
    </style>
""", unsafe_allow_html=True)

# Banner Image - Full Width
st.markdown('<div class="banner-container">', unsafe_allow_html=True)
st.image("images/banner_long.png", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# Start content wrapper for padding
st.markdown('<div class="content-wrapper">', unsafe_allow_html=True)

# Hero Section
st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">The Local Development Tracker Decision Engine</h1>
        <h1 class="hero-subtitle">Serbia Edition</h1>
        <p class="hero-description">
            Leveraging geospatial data and advanced analytics to rank municipalities across Serbia, 
            the Local Development Tracker Decision Engine, part of the World Bank's <a href="https://pim-pam.net/" target="_blank">Geospatial Planning & Budgeting Platform (GPBP)</a>, helps policymakers identify communities 
            facing the greatest development challenges. This tool reveals the drivers behind these 
            challenges, enabling informed decisions to promote prosperity, livability, and sustainable infrastructure development where it's needed most.
        </p>
    </div>
""", unsafe_allow_html=True)

# Launch Button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 Launch the LDT Decision Engine", use_container_width=True):
        st.switch_page("gpbp-ldt-de.py")

st.markdown("<div style='margin: 60px 0;'></div>", unsafe_allow_html=True)

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

# Three Column Layout for Info Cards
st.markdown('<div class="columns-section">', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
        <div class="info-card">
            <div class="card-title">🔬 Methodology</div>
            <div class="card-text">
                From indicator selection to data integration and, finally, to AI-powered recommendations, a detailed view into how the LDT Decision Engine was created.
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Add clickable link to About page
    st.markdown("<div class='card-button-wrapper' style='margin-top: 15px;'>", unsafe_allow_html=True)
    if st.button("Learn about our approach", key="about_link2", use_container_width=True):
        st.switch_page("methodology.py")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("""
            <div class="info-card">
                <div class="card-title">📚 Resources</div>
                <div class="card-text">
                    Access comprehensive documentation, technical guides, and learning materials to understand and 
                    effectively use the LDT Decision Engine.
                </div>
            </div>
        """, unsafe_allow_html=True)
        
    # Add clickable link to About page
    st.markdown("<div class='card-button-wrapper' style='margin-top: 15px;'>", unsafe_allow_html=True)
    if st.button("Browse our available resources", key="about_link", use_container_width=True):
        st.switch_page("resources.py")
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("""
        <div class="info-card">
            <div class="card-title">🛠️ Complementary GPBP Tools</div>
            <div class="card-text">
                The LDT-DE integrates insights from other platforms in the PimPam GPBP ecosystem, empowering a more informed decision-making process.
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Add clickable link to About page
    st.markdown("<div class='card-button-wrapper' style='margin-top: 15px;'>", unsafe_allow_html=True)
    if st.button("Which GPBP tools are utilized in the LDT-DE?", key="about1_link", use_container_width=True):
        st.switch_page("about.py")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Close columns-section

# st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

# # Disclaimer Section
# col1, col2, col3 =  st.columns([1, 3, 1])
# with col2:
#     st.markdown("""
#         <div class="info-card" style="border-left-color: #dc2626; background: #fef2f2;">
#             <div class="card-title" style="color: #dc2626;">⚠️ Important Disclaimer</div>
#             <div class="card-text">
#                 The GPBP Tools leverage <strong>Generative AI</strong> to analyze data and provide recommendations. 
#                 While we strive for accuracy, AI-generated responses <strong>may occasionally contain inaccuracies, 
#                 outdated information, or unintended biases</strong>. We strongly recommend that users 
#                 <strong>verify critical information independently</strong> before making decisions based on these outputs.
#             </div>
#         </div>
#     """, unsafe_allow_html=True)


# Footer Section
st.markdown('<div class="columns-section">', unsafe_allow_html=True)
st.markdown("""
    <div class="footer-section">
        <div class="footer-text" style="font-size: 2rem; font-weight: 700; margin-bottom: 60px; color: #1e3a8a;">
            Implemented by
        </div>
    </div>
""", unsafe_allow_html=True)

# Organization Logos - centered and sized with equal spacing
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

# Additional spacing and contact info
st.markdown("""
    <div style="text-align: center; margin-top: 60px; padding: 20px; color: #6b7280;">
        <p style="margin-bottom: 10px;">For inquiries and feedback, please email <a href="kkaiser@worldbank.org">kkaiser@worldbank.org</a> or <a href="sonle.h96@gmail.com">sonle.h96@gmail.com</a></p>
        <p style="font-size: 0.9rem;">© 2024 World Bank Group - <a href="https://pim-pam.net/" target="_blank">PimPam GPBP</a></p>
    </div>
""", unsafe_allow_html=True)

# Add some spacing at the bottom
st.markdown("<div style='height: 60px;'></div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Close columns-section

# Close content wrapper
st.markdown('</div>', unsafe_allow_html=True)

