"""
Extraction pipeline.

Flow:
    PDF with selectable text  -> PyMuPDF (fast, no OCR needed)
    Scanned PDF / image       -> Poppler (pdf2image) -> PaddleOCR
    Plain image (jpg/png)     -> straight to PaddleOCR

Returns a dict:
    {
        "text": "<full extracted text>",
        "pages": [ {"page_no": 1, "text": "...", "words": [...]} ],
        "layout": {
            "photo_present": bool,
            "qr_code_present": bool,
            "table_structure": bool,
            "mrz_present": bool,
            "page_count": int,
            "single_page": bool,
            "multi_page": bool,
        }
    }

NOTE: This POC keeps the OCR engines lazily imported so the rest of the app
(classifier, API contract) can be reviewed/tested even where paddleocr /
pymupdf / pdf2image aren't installed yet. Install requirements.txt to run
for real.
"""

import io
import os
import re
from typing import Dict, Any, List


SUPPORTED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


class OCRUnavailableError(RuntimeError):
    """Raised when OCR dependencies/runtime are unavailable for scanned documents."""
    pass


def _has_selectable_text_pdf(file_path: str, min_chars: int = 40) -> bool:
    """Quick check: does this PDF already contain a selectable text layer?"""
    import fitz  # PyMuPDF

    doc = fitz.open(file_path)
    total_chars = 0
    for page in doc:
        total_chars += len(page.get_text().strip())
        if total_chars >= min_chars:
            doc.close()
            return True
    doc.close()
    return False


def _extract_with_pymupdf(file_path: str) -> Dict[str, Any]:
    import fitz

    doc = fitz.open(file_path)
    pages = []
    full_text = []
    photo_present = False

    for i, page in enumerate(doc):
        text = page.get_text()
        pages.append({"page_no": i + 1, "text": text, "words": []})
        full_text.append(text)
        # crude photo/image detection: PDF has embedded images (common on ID cards)
        if page.get_images(full=True):
            photo_present = True

    page_count = len(doc)
    doc.close()

    return {
        "text": "\n".join(full_text),
        "pages": pages,
        "layout": {
            "photo_present": photo_present,
            "qr_code_present": _detect_qr_in_text_heuristic(full_text),
            "table_structure": _detect_table_structure("\n".join(full_text)),
            "mrz_present": _detect_mrz("\n".join(full_text)),
            "page_count": page_count,
            "single_page": page_count == 1,
            "multi_page": page_count > 1,
        },
    }


def _pdf_to_images(file_path: str):
    """Poppler-backed conversion: PDF pages -> PIL images."""
    try:
        from pdf2image import convert_from_path  # wraps poppler's pdftoppm/pdftocairo
        return convert_from_path(file_path, dpi=300)
    except Exception as exc:
        raise OCRUnavailableError(
            "Unable to convert scanned PDF pages for OCR. Ensure pdf2image and Poppler are installed and available on PATH."
        ) from exc


def _extract_with_ocr(images: List["PIL.Image.Image"]) -> Dict[str, Any]:
    """Run PaddleOCR over a list of PIL images (from Poppler or a direct image upload)."""
    try:
        from paddleocr import PaddleOCR
        import numpy as np
    except Exception as exc:
        raise OCRUnavailableError(
            "OCR is required for this scanned/image document, but PaddleOCR or its dependencies are unavailable."
        ) from exc

    # lang='en' is fine for Latin text; Aadhaar/PAN also contain Devanagari script
    # which PaddleOCR's 'en' model will mostly skip -- acceptable for POC since
    # our regex/keyword rules key off the English text.
    ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    pages = []
    full_text = []
    qr_flag = False
    
    for i, img in enumerate(images):
        result = ocr.ocr(np.array(img), cls=True)
        words = []
        page_text_lines = []
        if result and result[0]:
            for line in result[0]:
                box, (text, conf) = line
                words.append({"text": text, "confidence": float(conf), "box": box})
                page_text_lines.append(text)
        page_text = "\n".join(page_text_lines)
        pages.append({"page_no": i + 1, "text": page_text, "words": words})
        full_text.append(page_text)

    joined = "\n".join(full_text)
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$",full_text)
    return {
        "text": joined,
        "pages": pages,
        "layout": {
            "photo_present": True,  # ID cards/scans nearly always have a photo region; refine with a CV face detector later
            "qr_code_present": _detect_qr_in_text_heuristic(full_text),
            "table_structure": _detect_table_structure(joined),
            "mrz_present": _detect_mrz(joined),
            "page_count": len(images),
            "single_page": len(images) == 1,
            "multi_page": len(images) > 1,
        },
    }


def _detect_qr_in_text_heuristic(text_chunks: List[str]) -> bool:
    """
    Cheap heuristic placeholder. A real implementation should run a QR/barcode
    detector (e.g. pyzbar) on the page image directly. Kept here so the
    layout signal exists end-to-end; swap in pyzbar for production accuracy.
    """
    joined = " ".join(text_chunks).lower()
    return "qr" in joined  # weak signal on purpose -- replace with pyzbar.decode(image)


def _detect_table_structure(text: str) -> bool:
    """
    Heuristic: financial statements/ledgers are dense with currency amounts
    and dates, but PDF-to-text extraction often puts each table cell on its
    own line rather than preserving row layout (e.g. PyMuPDF splits a row
    like "01-Apr-2026 | NEFT Payment | 50,000.00" into 3 separate lines).
    So instead of requiring multiple numbers on the SAME line, we count
    currency-amount and date occurrences across the WHOLE document -- a
    real transaction ledger will have many of both.
    """
    amount_pattern = re.compile(r"\d{1,3}(?:,\d{2,3})*\.\d{2}")
    date_pattern = re.compile(r"\d{2}[-/](?:\d{2}|[A-Za-z]{3})[-/]\d{2,4}")

    amount_count = len(amount_pattern.findall(text))
    date_count = len(date_pattern.findall(text))

    return amount_count >= 8 or (amount_count >= 4 and date_count >= 4)


def _detect_mrz(text: str) -> bool:
    """Passport MRZ lines look like 'P<INDSURNAME<<GIVENNAME<<<<<<<<<<<<<<<<<<<<'."""
    return bool(re.search(r"P<[A-Z]{3}[A-Z<]{5,}", text))


def extract_document(file_path: str) -> Dict[str, Any]:
    """
    Main entrypoint. Decides selectable-text-PDF vs scanned-PDF vs image,
    and routes through PyMuPDF or Poppler+PaddleOCR accordingly.
    """
    ext = os.path.splitext(file_path)[1].lower()
    

    if ext == ".pdf":
        if _has_selectable_text_pdf(file_path):
            result = _extract_with_pymupdf(file_path)
            result["extraction_method"] = "pymupdf_text_layer"
            return result
        else:
            images = _pdf_to_images(file_path)  # Poppler
            result = _extract_with_ocr(images)   # PaddleOCR
            result["extraction_method"] = "poppler_paddleocr"
            return result

    elif ext in SUPPORTED_IMAGE_EXT:
        from PIL import Image
        img = Image.open(file_path)
        result = _extract_with_ocr([img])
        result["extraction_method"] = "paddleocr_direct_image"
        return result

    else:
        raise ValueError(f"Unsupported file type: {ext}")
