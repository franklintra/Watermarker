Watermark
=========

Raster-flatten a PDF or image and overlay a repeated watermark.

Usage
-----

- CLI once installed/in this repo:
  - `python -m watermark --help`
  - `watermark in.pdf out.pdf "Confidential"`
  - `watermark --format jpeg --quality 85 --angle 40 in.pdf out.pdf "Sample"`

- Programmatic API:
  - `from watermark import raster_flatten_pdf_with_watermark, images_to_pdf_with_watermark`

Notes
-----

- The legacy script `watermark_pdf.py` remains as a thin wrapper invoking the new package CLI for backward compatibility.
