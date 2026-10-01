"""Read complete text PDFs within the existing size limits."""
from pathlib import Path
from pypdf import PdfReader
MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_TEXT_CHARS = 120_000

def read_contract_text(pdf: Path) -> str:
    """Read every page, rejecting files this script cannot extract as text."""
    if pdf.suffix.lower() != '.pdf':
        raise ValueError('Pass a PDF file.')
    if pdf.stat().st_size > MAX_PDF_BYTES:
        raise ValueError('PDF exceeds 20 MB.')
    reader = PdfReader(pdf)
    if reader.is_encrypted:
        raise ValueError('Encrypted PDFs are not supported.')
    if len(reader.pages) > 200:
        raise ValueError('PDF exceeds 200 pages.')
    pages = [page.extract_text() or '' for page in reader.pages]
    if not pages or any(not page.strip() for page in pages):
        raise ValueError('Unreadable PDF pages; supply a text-based PDF.')
    text = '\n\n'.join(f'PAGE {i}\n{page}' for i, page in enumerate(pages, 1))
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError('PDF text exceeds 120,000 characters.')
    return text
