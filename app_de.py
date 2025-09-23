#Import required libraries
import os
from typing import Dict, Any, Optional
import base64
from io import BytesIO

import streamlit as st
import pandas as pd
from openai import OpenAI
from google.cloud import storage
from google.oauth2 import service_account
from PIL import Image

from general_workflow import run_analysis

# Access secrets directly, no need for json.loads()
openai_api_key = os.getenv('openai_apikey')

# private_key_id = os.getenv('private_key_id')
# private_key = os.getenv('private_key', '').replace('\\n', '\n')
# client_email = os.getenv('client_email')
# client_id = os.getenv('client_id')
# auth_uri = os.getenv('auth_uri')
# token_uri = os.getenv('token_uri')
# client_x509_cert_url = os.getenv('client_x509_cert_url')
# auth_provider_x509_cert_url = os.getenv('auth_provider_x509_cert_url')

# creds_info = {
#     "type": "service_account",
#     "project_id": "wb-ldt",
#     "private_key_id": private_key_id,
#     "private_key": private_key, 
#     "client_email": client_email,
#     "client_id": client_id,
#     "auth_uri": auth_uri,
#     "token_uri": token_uri,
# "auth_provider_x509_cert_url": auth_provider_x509_cert_url,
#     "client_x509_cert_url": client_x509_cert_url,
# "universe_domain": "googleapis.com"
# }

# credentials = service_account.Credentials.from_service_account_info(creds_info)
credentials = service_account.Credentials.from_service_account_file(
    r"D:\Work\WB\LDT\credentials\wb-ldt-948953b71056.json"
    # "/Users/sonle/Documents/work/WB/LDT_DecisionEngine/credentials/wb-ldt-948953b71056.json"
)
storage_client = storage.Client(credentials=credentials)

# Set OpenAI API Key
os.environ['OPENAI_API_KEY'] = openai_api_key

# Initialize Google Cloud Storage client
BUCKET_NAME = "wb-ldt"

# Configure page layout to use wide mode for better space utilization
st.set_page_config(
    page_title="LDT Decision Engine",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to maximize content space utilization
st.markdown("""
    <style>
    /* Reduce padding around main content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: none;
    }
    
    /* Reduce sidebar width slightly to give more space to main content */
    .css-1d391kg {
        width: 300px;
    }
    
    /* Ensure content uses full width */
    .stApp > div {
        width: 100%;
    }
    
    /* Improve text readability with better spacing */
    .stMarkdown {
        text-align: justify;
    }
    </style>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def read_csv_from_gcs(bucket_name: str, file_path: str, **kwargs: Any) -> pd.DataFrame:
    """
    Read a CSV file from Google Cloud Storage into a pandas DataFrame.
    
    Args:
        bucket_name (str): Name of the GCS bucket
        file_path (str): Path to the CSV file in the bucket
        **kwargs: Additional arguments passed to pd.read_csv
        
    Returns:
        pd.DataFrame: The loaded DataFrame
        
    Note:
        Results are cached for 1 hour using Streamlit's caching mechanism
    """
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    data = blob.download_as_bytes()
    return pd.read_csv(BytesIO(data), **kwargs)

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_image_from_gcs(bucket_name: str, image_name: str) -> Image.Image:
    """
    Fetch and open an image from Google Cloud Storage.
    
    This function retrieves an image file from a GCS bucket and returns it as a PIL Image object.
    It's used primarily for loading UI assets like logos and icons.
    
    Args:
        bucket_name (str): Name of the GCS bucket containing the image
        image_name (str): Full path to the image file within the bucket
        
    Returns:
        Image.Image: Opened PIL Image object ready for display or manipulation
        
    Raises:
        google.api_core.exceptions.NotFound: If the image or bucket doesn't exist
        PIL.UnidentifiedImageError: If the downloaded data is not a valid image
        
    Example:
        >>> logo = get_image_from_gcs("my-bucket", "assets/logo.png")
        >>> st.image(logo)
    """
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(image_name)
    image_data = blob.download_as_bytes()
    image = Image.open(BytesIO(image_data))
    return image

# Load CSVs from Google Cloud Storage
df_indicatorlist = read_csv_from_gcs(BUCKET_NAME, "decision_engine/inputs/Indicator List v2.csv",
                                     delimiter=',', encoding='cp1252', on_bad_lines='warn')

df_indicators = read_csv_from_gcs(BUCKET_NAME, "decision_engine/inputs/SRB Absolute Full_v4.csv")

# List of Regions #
regions = df_indicators['ENGLISH_NAME'].unique().tolist()
regions_sr = df_indicators['SERBIAN_NAME_CYRILLIC'].unique().tolist()

# DataFrame of National Averages #
averages_df = df_indicators.groupby('year')[df_indicators.columns[4:]].mean().reset_index()

# Load the image
im = get_image_from_gcs(BUCKET_NAME, "decision_engine/inputs/LDT-logo.png")


# Convert image to base64 - To be able to add to page
def get_base64_from_image(image: Image.Image) -> str:
    """
    Convert a PIL Image to a base64 encoded string.
    
    Args:
        image (Image.Image): PIL Image object to convert
        
    Returns:
        str: Base64 encoded string representation of the image
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# wb_logo = get_image_from_gcs(BUCKET_NAME, "decision_engine/inputs/World Bank Group Logo.jpg")
# st.sidebar.image(wb_logo, use_container_width =True)

pimpam_logo = get_image_from_gcs(BUCKET_NAME, "decision_engine/inputs/wbg-pimpam.png")
st.sidebar.image(pimpam_logo, use_container_width =True)

gpbp_logo = get_image_from_gcs(BUCKET_NAME, "decision_engine/inputs/GPBP logo.jpg")
st.logo(gpbp_logo, size='large')

with st.sidebar:
    # Global Font Styling
    st.markdown(
        """
        <style>
            .sidebar-text {
                text-align: left;
                font-family: Arial, sans-serif;
                font-size: 0.9rem;
                color: black;
                line-height: 1.5;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # About Section
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
            <li><a href="https://www.figma.com/proto/MRIuLeqyVOFGJQwVi0sVAg/PIA-final?node-id=14101-76623&p=f&t=wMUuiwyzr7W56K36-0&scaling=min-zoom&content-scaling=fixed&page-id=14101%3A64991&starting-point-node-id=14101%3A76623" target="_blank">Public Infrastructure Access Tool</a> (PIA)</li>
            
        </div>
        """,
        unsafe_allow_html=True
    )

    # Divider for separation
    st.markdown("<hr style='border: 1px solid #ccc;'>", unsafe_allow_html=True)

    # Documentaiton
    st.write('### 📄 Documentation')
    st.markdown(
        """
        <div class ="sidebar-text">
            The following documentation regarding the GPBP LDT - DE is available:
            <li><a href="https://docs.google.com/presentation/d/19iGMTUGeB7LNRGnFxKTYuRexLW0OjAmn/edit?slide=id.g2e47b9337ae_0_98#slide=id.g2e47b9337ae_0_98" 
                target="_blank">Pitch Deck</a></li>
            <li><a href="https://docs.google.com/document/d/1eoCPpdTx9z5NI2lX20aAFzLC1_kHGVfd/edit?usp=sharing&ouid=107640506223612923418&rtpof=true&sd=true" target="_blank">EIG in the WeBA6</a></li>
            <li><a href="https://docs.google.com/document/d/17LhzOH-EnxfAWaBF8_FHCup8E_fsDe4p0VVfrUG4Aac/edit?usp=sharing" target="_blank">Indicator Methodology</a></li>
            <li><a href="https://docs.google.com/document/d/1IaHR46oQ8gcmZwwIH6LLMGyyl76Cf0nsgvEY0wuf9OM/edit?usp=sharing" target="_blank">Technical Documentation</a></li>
        </div>
        """, unsafe_allow_html=True
    )

    # Divider for separation
    st.markdown("<hr style='border: 1px solid #ccc;'>", unsafe_allow_html=True)

    # Disclaimer Section
    st.write("### ⚠️ Disclaimer")
    st.markdown(
        """
        <div class="sidebar-text">
            <p>
                The <strong>GPBP LDT - DE</strong> leverages <strong>Generative AI</strong> to analyze data and suggest region-specific and project-level recommendations.
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


languages = {"English": "en", "Serbian": "sr"}

# Get current language from query params (Streamlit 1.32+ style)
query_params = st.query_params
current_lang_code = query_params.get("lang", ["en"])[0]

# Reverse map: 'en' -> 'English'
reverse_languages = {v: k for k, v in languages.items()}
default_language = reverse_languages.get(current_lang_code, "English")

# Define language switch handler
def set_language() -> None:
    """
    Handle language switching in the Streamlit app.
    
    This function updates the query parameters and session state
    when the language selection changes, while preserving other
    session state variables.
    """
    if "selected_language" in st.session_state:
        new_lang_code = languages[st.session_state["selected_language"]]
        st.query_params["lang"] = new_lang_code

        # Only reset category if it's not already set for the new language
        # This prevents unnecessary resets that cause subheaders to disappear
        if new_lang_code == "en" and "option_category" not in st.session_state:
            st.session_state.option_category = "Education"
        elif new_lang_code == "sr" and "option_category" not in st.session_state:
            st.session_state.option_category = "Образовање"
        
        # Preserve other session state variables that should persist across language changes
        # Don't clear analysis flags or results unless explicitly needed

# Language selection radio
sel_lang = st.radio(
    "Language",
    options=list(languages.keys()),
    index=list(languages.keys()).index(default_language),
    horizontal=True,
    on_change=set_language,  # ← this triggers your reset
    key="selected_language",
)


# Display language choice and code
st.markdown(f"Selected Language: {sel_lang}")
lang_code = languages[sel_lang]


# Convert and embed the image
icon_html = f'<img src="data:image/png;base64,{get_base64_from_image(im)}" width="30" style="vertical-align: middle; margin-right: 10px;">'

df_projects = read_csv_from_gcs(BUCKET_NAME, "decision_engine/inputs/wbif_project_examples_v2.csv", sep=";")
df_projects = df_projects.drop(['Estimated Completion', 'Beneficiary Body', 'Total Grant', 'Total Loan'], axis=1)

# Define header and subheader based on language
if lang_code == "en":
    app_title = "GPBP LDT - Decision Engine"
    # Display title with icon
    st.markdown(
        f"<h1 style='display: flex; align-items: center;'>{icon_html}{app_title}</h1>",
        unsafe_allow_html=True
    )

    app_subheader = "Hello, I can produce an automated analysis of regional performances based on the themes you're interested in. Then, I can make public investment recommendations based on the analysis."
    # Display subheader
    st.subheader(app_subheader)
    if "option_category" not in st.session_state:
        st.session_state.option_category = "Education"

    run_analysis(df_indicatorlist, df_indicators, averages_df, df_projects, regions, storage_client, language=lang_code)

elif lang_code == "sr":
    app_title = "GPBP LDT - мотор за одлучивање"
    app_subheader = "Здраво, могу да извршим аутоматизовану анализу регионалних перформанси на основу тема које вас занимају. атим могу да дам препоруке за јавне инвестиције на основу анализе"
    # Display subheader
    # Display title with icon
    st.markdown(
        f"<h1 style='display: flex; align-items: center;'>{icon_html}{app_title}</h1>",
        unsafe_allow_html=True
    )
    st.subheader(app_subheader)
    if "option_category" not in st.session_state:
        st.session_state.option_category = "Образовање"

    run_analysis(df_indicatorlist, df_indicators, averages_df, df_projects, regions_sr, storage_client, language=lang_code)