"""Extract the highest-quality image from each PDF in test-data/ and save as PNG.

For PDFs with embedded raster images, the largest image is extracted directly.
For vector-only PDFs, the page is rendered at high DPI.
"""

import sys, pathlib

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("PyMuPDF is required.  Install with:  pip install PyMuPDF")

TEST_DATA = pathlib.Path(__file__).resolve().parent.parent / "test-data"
RENDER_DPI = 300


def extract_best_image(pdf_path: pathlib.Path) -> None:
    doc = fitz.open(pdf_path)
    out_path = pdf_path.with_suffix(".png")

    # Try embedded raster images first
    best = None  # (pixel_count, image_bytes, ext, w, h)
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            base = doc.extract_image(xref)
            w, h = base["width"], base["height"]
            pixels = w * h
            if best is None or pixels > best[0]:
                best = (pixels, base["image"], base["ext"], w, h)

    if best is not None:
        if best[2] == "png":
            out_path.write_bytes(best[1])
        else:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(best[1]))
            img.save(out_path, "PNG")
        print(f"  {pdf_path.name} -> {out_path.name}  ({best[3]}x{best[4]}, embedded)")
        doc.close()
        return

    # No embedded images — render the first page at high DPI
    page = doc[0]
    zoom = RENDER_DPI / 72  # 72 pts/inch is the PDF default
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(str(out_path))
    print(f"  {pdf_path.name} -> {out_path.name}  ({pix.width}x{pix.height}, rendered @ {RENDER_DPI} DPI)")
    doc.close()


def main() -> None:
    pdfs = sorted(TEST_DATA.glob("*.pdf"))
    if not pdfs:
        print("No PDF files found in", TEST_DATA)
        return

    print(f"Found {len(pdfs)} PDF(s) in {TEST_DATA}\n")
    for pdf in pdfs:
        extract_best_image(pdf)


if __name__ == "__main__":
    main()
