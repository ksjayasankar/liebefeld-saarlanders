"""D-29: a business model sent as PDF becomes plain text that agency staff review before Apertus sees it.

Docling (local, MIT) reads the PDF's text layer in reading order (columns, lists, tables); EasyOCR reads only the regions
without a text layer, such as scanned pages and text inside images. Page headers and footers are left out."""
from functools import cache
from io import BytesIO
from threading import Lock

from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import ConversionStatus, DocumentStream, InputFormat
from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from .config import env

MAX_BYTES, MAX_PAGES, TIMEOUT = 10_000_000, 40, 120   # a business model or pitch deck; seconds per document
OCR_LANGS = ["en", "de", "fr"]
LOCK = Lock()   # one conversion at a time: the layout, table and OCR models are shared


@cache
def converter() -> DocumentConverter:
    options = PdfPipelineOptions(do_ocr=True, ocr_options=EasyOcrOptions(lang=OCR_LANGS), do_table_structure=True,
                                 document_timeout=TIMEOUT, accelerator_options=AcceleratorOptions(device=env("TORCH_DEVICE")))
    c = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    c.initialize_pipeline(InputFormat.PDF)
    return c


def text(data: bytes) -> tuple[str, int]:
    """Plain text and page count. Raises ValueError with a message for staff when the file cannot be read in full."""
    if not data.startswith(b"%PDF-"):
        raise ValueError("the file is not a PDF")
    if len(data) > MAX_BYTES:
        raise ValueError(f"the PDF is larger than {MAX_BYTES // 1_000_000} MB")
    with LOCK:
        r = converter().convert(DocumentStream(name="upload.pdf", stream=BytesIO(data)), raises_on_error=False,
                                max_num_pages=MAX_PAGES, max_file_size=MAX_BYTES)
    if r.status != ConversionStatus.SUCCESS:   # partial success (timeout, unreadable page) is a failure: no silent gaps
        raise ValueError(f"the PDF could not be read in full ({r.status.value}, at most {MAX_PAGES} pages): "
                         + "; ".join(e.error_message for e in r.errors))
    out = r.document.export_to_text().strip()
    if not out:
        raise ValueError("no text found in the PDF")
    return out, len(r.document.pages)
