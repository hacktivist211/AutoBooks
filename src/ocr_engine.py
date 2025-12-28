import time
import logging
from pathlib import Path
from typing import Dict, Any
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

def extract_text_from_pdf(filepath: str) -> Dict[str, Any]:
    """
    Extract text from PDF using OCR.

    Args:
        filepath: Path to the PDF file

    Returns:
        Dict with keys: success (bool), text (str), pages (int), error (str or None)
    """
    start_time = time.time()

    try:
        # Validate file exists
        pdf_path = Path(filepath)
        if not pdf_path.exists():
            error_msg = f"PDF file not found: {filepath}"
            logger.error(error_msg)
            return {
                "success": False,
                "text": "",
                "pages": 0,
                "error": error_msg
            }

        # Convert PDF to images
        logger.info(f"Converting PDF to images: {filepath}")
        images = convert_from_path(filepath, dpi=150)

        if not images:
            error_msg = "No images extracted from PDF"
            logger.error(error_msg)
            return {
                "success": False,
                "text": "",
                "pages": 0,
                "error": error_msg
            }

        # Extract text from each page
        extracted_text = []
        for i, image in enumerate(images):
            logger.debug(f"Extracting text from page {i+1}")
            try:
                page_text = pytesseract.image_to_string(image)
                extracted_text.append(page_text)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {i+1}: {str(e)}")
                extracted_text.append("")

        # Combine all pages
        full_text = "\n\n".join(extracted_text)

        extraction_time = time.time() - start_time
        logger.info(f"OCR extraction completed in {extraction_time:.2f}s for {len(images)} pages")

        return {
            "success": True,
            "text": full_text,
            "pages": len(images),
            "error": None
        }

    except Exception as e:
        extraction_time = time.time() - start_time
        error_msg = f"OCR extraction failed after {extraction_time:.2f}s: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "text": "",
            "pages": 0,
            "error": error_msg
        }