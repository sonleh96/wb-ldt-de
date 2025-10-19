from typing import Any
from io import BytesIO

import pandas as pd
import geopandas as gpd
import streamlit as st
from google.cloud import storage
from PIL import Image

@st.cache_data(ttl=3600)
def read_csv_from_gcs(
    _storage_client: storage.Client, bucket_name: str, file_path: str, **kwargs: Any
) -> pd.DataFrame:
    """
    Read a CSV file from Google Cloud Storage into a pandas DataFrame.
    Results are cached for 1 hour using Streamlit's caching mechanism.
    
    Args:
        _storage_client (storage.Client): Authenticated GCS client.
        bucket_name (str): Name of the GCS bucket.
        file_path (str): Path to the CSV file in the bucket.
        **kwargs: Additional arguments passed to pd.read_csv.
        
    Returns:
        pd.DataFrame: The loaded DataFrame.
    """
    bucket = _storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    data = blob.download_as_bytes()
    return pd.read_csv(BytesIO(data), **kwargs)

@st.cache_data(ttl=3600)
def read_geojson_from_gcs(
    _storage_client: storage.Client, bucket_name: str, file_path: str
) -> gpd.GeoDataFrame:
    """
    Fetch and open a GeoJSON file from Google Cloud Storage.
    Results are cached for 1 hour.
    """
    bucket = _storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    data = blob.download_as_bytes()
    return gpd.read_file(BytesIO(data))

@st.cache_data(ttl=3600)
def get_image_from_gcs(
    _storage_client: storage.Client, bucket_name: str, image_name: str
) -> Image.Image:
    """
    Fetch and open an image from Google Cloud Storage.
    Results are cached for 1 hour.
    
    Args:
        _storage_client (storage.Client): Authenticated GCS client.
        bucket_name (str): Name of the GCS bucket containing the image.
        image_name (str): Full path to the image file within the bucket.
        
    Returns:
        Image.Image: Opened PIL Image object.
    """
    bucket = _storage_client.bucket(bucket_name)
    blob = bucket.blob(image_name)
    image_data = blob.download_as_bytes()
    image = Image.open(BytesIO(image_data))
    return image
