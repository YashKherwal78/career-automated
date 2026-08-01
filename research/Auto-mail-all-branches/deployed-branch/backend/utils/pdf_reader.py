"""Extract plain text from a PDF file object (bytes)."""
import io
import fitz  # PyMuPDF


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Return concatenated page text from *file_bytes* (PDF)."""
    doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
    pages = [page.get_text() for page in doc]
    return "\n".join(pages).strip()
