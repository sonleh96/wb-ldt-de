import streamlit as st
from google.oauth2 import service_account
from google.cloud import storage

from src.config import BUCKET_NAME
from src.gcs import get_image_from_gcs
from src.ui import fix_appearance

fix_appearance()

# --- Initialization ---
@st.cache_resource
def init_gcs_client():
    """Initialize Google Cloud Storage client using credentials from Streamlit secrets."""
    creds_dict = {
        "type": "service_account",
        "project_id": st.secrets["gcs"]["project_id"],
        "private_key_id": st.secrets["gcs"]["private_key_id"],
        "private_key": st.secrets["gcs"]["private_key"], 
        "client_email": st.secrets["gcs"]["client_email"],
        "client_id": st.secrets["gcs"]["client_id"],
        "auth_uri": st.secrets["gcs"]["auth_uri"],
        "token_uri": st.secrets["gcs"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcs"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcs"]["client_x509_cert_url"],
        "universe_domain": "googleapis.com"
    }
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    return storage.Client(credentials=credentials)

storage_client = init_gcs_client()
pimpam_logo = get_image_from_gcs(storage_client, BUCKET_NAME, "decision_engine/inputs/wbg-pimpam.png")
gpbp_logo = get_image_from_gcs(storage_client, BUCKET_NAME, "decision_engine/inputs/GPBP logo.jpg")

st.sidebar.image(pimpam_logo, use_container_width=True)
st.logo(gpbp_logo, size='large')

pages = {
    # "Home": [st.Page("home.py", title="Home")],
    
    "GPBP-LDT-DE": [
        st.Page("gpbp-ldt-de.py", title="Launch the app"),
        # st.Page("gpbp-pia.py", title="Public Infrastructure Access Tool (PIA)"),
    ],
    "Resources": [
        st.Page("about.py", title="About"),
        # st.Page("methodology.py", title="Methodology"),
    ],
}

pg = st.navigation(pages)
pg.run()