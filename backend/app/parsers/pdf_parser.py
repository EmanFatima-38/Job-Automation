import pdfplumber
from pypdf import PdfReader


def extract_text_from_pdf(path: str) -> str:
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if text.strip():
            return text
    except Exception:
        pass

    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)
