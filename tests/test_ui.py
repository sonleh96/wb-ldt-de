from PIL import Image
from src.ui import get_base64_from_image

def test_get_base64_from_image():
    # Create a dummy 1x1 red pixel image
    img = Image.new('RGB', (1, 1), color='red')
    
    b64_string = get_base64_from_image(img)
    
    # This is the known base64 representation of a 1x1 red PNG
    expected_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/wcAAwAB/epv2AAAAABJRU5ErkJggg=="
    
    assert b64_string == expected_b64
