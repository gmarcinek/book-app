# PLIK: llm/utils.py

def detect_image_format(image_base64: str) -> str:
    """
    Auto-detect image format from base64 data
    
    Args:
        image_base64: Base64 encoded image data
        
    Returns:
        MIME type string (image/jpeg, image/png, etc.)
    """
    try:
        # Check base64 signature patterns
        if image_base64.startswith("/9j/"):
            return "image/jpeg"
        elif image_base64.startswith("iVBOR"):
            return "image/png"
        elif image_base64.startswith("R0lGOD"):
            return "image/gif"
        elif image_base64.startswith("UklGR"):
            return "image/webp"
        else:
            # Default fallback - most PDF extractions are JPEG
            return "image/jpeg"
    except Exception:
        # Safe fallback
        return "image/jpeg"