import os
import logging
from PIL import Image

logger = logging.getLogger("image_converter")

def convert_to_web_image(source_path: str, output_dir: str, base_name: str) -> tuple[str, int, int]:
    """
    Converts any image (including MathType WMF/EMF, TIFF, BMP) to a browser-ready PNG.
    Returns (relative_filename, width, height).
    """
    ext = os.path.splitext(source_path)[1].lower()
    target_filename = f"{base_name}.png"
    target_path = os.path.join(output_dir, target_filename)

    width, height = 400, 300

    try:
        # Open with Pillow
        with Image.open(source_path) as img:
            width, height = img.size
            if ext in ('.png', '.jpg', '.jpeg', '.webp') and os.path.exists(source_path):
                # Standard web format, copy or save as png
                img.save(target_path, format="PNG")
            else:
                # Vector metafile or uncompressed format (WMF, EMF, BMP, TIFF)
                rgb_img = img.convert("RGBA" if "A" in img.mode else "RGB")
                rgb_img.save(target_path, format="PNG")
                
        return target_filename, width, height
    except Exception as e:
        logger.warning(f"Failed to convert image {source_path} via PIL: {e}")
        # If already PNG/JPG, return original filename
        if ext in ('.png', '.jpg', '.jpeg', '.webp'):
            return os.path.basename(source_path), width, height
            
        # Fallback: copy file directly
        import shutil
        shutil.copyfile(source_path, target_path)
        return target_filename, width, height
