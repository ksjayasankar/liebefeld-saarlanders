"""PDF intake (D-29) on generated PDFs of a fictional company: born-digital two-column deck, scanned page, bad input."""
import os

import pytest
from weasyprint import HTML

os.environ.setdefault("TORCH_DEVICE", "cpu")

from navigator import pdf  # noqa: E402

DECK = """<style>@page{size:A4 landscape;margin:2cm} .cols{column-count:2;column-gap:1.5cm} td,th{border:1px solid #999;padding:4px}</style>
<h1>Examplegait AG</h1><div class="cols"><h2>Problem</h2><p>Gait changes in Parkinson's disease are detected late, often only at
the next clinic visit. Neurologists lack continuous data from daily life.</p>
<h2>Solution</h2><p>Our insole sensor measures stride length, cadence and freezing of gait at home. An app sends alerts to the
treating neurologist.</p></div>
<ul><li>A clinical partner to run a pilot study with patients.</li></ul>
<table><tr><th>Milestone</th><th>Date</th></tr><tr><td>Pilot study</td><td>2027</td></tr></table>"""


def test_digital_pdf_keeps_reading_order_lists_and_tables():
    text, pages = pdf.text(HTML(string=DECK).write_pdf())
    assert pages == 1
    assert text.index("detected late") < text.index("Solution") < text.index("stride length")   # column by column
    assert "A clinical partner to run a pilot study with patients." in text
    assert "| Pilot study" in text


def test_scanned_page_is_read_by_ocr(tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(8.27, 11.69), dpi=150)
    fig.text(0.1, 0.8, "We plan to move our research team to Bern.", fontsize=14)
    fig.savefig(tmp_path / "scan.png")
    plt.close(fig)
    text, _ = pdf.text(HTML(string='<img src="scan.png" style="width:100%">', base_url=str(tmp_path)).write_pdf())
    assert "move our research team to Bern" in text


def test_rejects_non_pdf_and_too_many_pages():
    with pytest.raises(ValueError, match="not a PDF"):
        pdf.text(b"<html>not a pdf</html>")
    with pytest.raises(ValueError, match="could not be read in full"):
        pdf.text(HTML(string="<p style='page-break-after:always'>Page.</p>" * (pdf.MAX_PAGES + 1)).write_pdf())
