from unittest.mock import MagicMock
import pytest
from src.gcs import read_csv_from_gcs, get_image_from_gcs
import pandas as pd
from io import BytesIO
from PIL import Image

@pytest.fixture
def mock_gcs_client():
    """Fixture to create a mock GCS client."""
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    
    return mock_client, mock_blob

def test_read_csv_from_gcs(mock_gcs_client):
    mock_client, mock_blob = mock_gcs_client
    
    # Prepare mock CSV data
    csv_data = "col1,col2\nval1,val2"
    csv_bytes = csv_data.encode('utf-8')
    mock_blob.download_as_bytes.return_value = csv_bytes

    # Call the function
    df = read_csv_from_gcs(mock_client, "test-bucket", "test-file.csv")

    # Assertions
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (1, 2)
    assert df.columns.tolist() == ['col1', 'col2']
    mock_client.bucket.assert_called_with("test-bucket")
    mock_client.bucket.return_value.blob.assert_called_with("test-file.csv")
    mock_blob.download_as_bytes.assert_called_once()

def test_get_image_from_gcs(mock_gcs_client):
    mock_client, mock_blob = mock_gcs_client
    
    # Prepare mock image data
    img = Image.new('RGB', (60, 30), color = 'red')
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()
    mock_blob.download_as_bytes.return_value = img_bytes

    # Call the function
    result_image = get_image_from_gcs(mock_client, "test-bucket", "test-image.png")

    # Assertions
    assert isinstance(result_image, Image.Image)
    assert result_image.size == (60, 30)
    mock_client.bucket.assert_called_with("test-bucket")
    mock_client.bucket.return_value.blob.assert_called_with("test-image.png")
    mock_blob.download_as_bytes.assert_called_once()
