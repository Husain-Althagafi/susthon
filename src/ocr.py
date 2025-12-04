import io
from pathlib import Path
from typing import Union

from PIL import Image

try:
    import pytesseract
except Exception:  # pragma: no cover - optional dependency at runtime
    pytesseract = None

try:
    from PyPDF2 import PdfReader
except Exception:  # pragma: no cover - optional dependency at runtime
    PdfReader = None


def extract_text(file_data: Union[bytes, io.BytesIO], filename: str = "") -> str:
    """
    Extract text from PDFs or images. Falls back to treating the content as UTF-8 text.
    """
    ext = Path(filename).suffix.lower()
    content = file_data
    if isinstance(file_data, io.BytesIO):
        content = file_data.getvalue()

    # PDF path
    if ext == ".pdf" and PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except Exception:
            pass

    # Image path
    if ext in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"} and pytesseract is not None:
        try:
            image = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(image)
        except Exception:
            pass

    # Plain text fallback
    try:
        return content.decode("utf-8", errors="ignore")
    except Exception:
        return ""
