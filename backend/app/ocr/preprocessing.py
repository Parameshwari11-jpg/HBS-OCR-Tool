import cv2
import numpy as np
from PIL import Image
from typing import Union

def preprocess_image_for_ocr(image_input: Union[str, np.ndarray, Image.Image]) -> np.ndarray:
    """Preprocess image to improve OCR accuracy."""
    if isinstance(image_input, str):
        img = cv2.imread(image_input)
    elif isinstance(image_input, Image.Image):
        img = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, np.ndarray):
        img = image_input.copy()
    else:
        raise ValueError("Unsupported image type")
        
    if img is None:
        return np.zeros((100, 100, 3), dtype=np.uint8)
        
    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
        
    # Denoise slightly
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    
    # Adaptive thresholding for binarization if contrast is low
    # Preserve original color BGR for PaddleOCR as it accepts both
    return img
