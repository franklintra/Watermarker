"""
Watermark package: utilities to raster-flatten PDFs or images and overlay
repeating diagonal watermark text.

Public API re-exports common entry points for convenience.
"""

from .pdf import (
    raster_flatten_pdf_with_watermark,
    analyze_pdf,
    estimate_pdf_dpi,
)
from .images import images_to_pdf_with_watermark
from .render import make_watermark_overlay, load_font
from .utils import (
    parse_hex_color,
    parse_page_range,
    extract_image_dpi,
    is_pdf_file,
    is_image_file,
)

__all__ = [
    # PDF operations
    "raster_flatten_pdf_with_watermark",
    "analyze_pdf",
    "estimate_pdf_dpi",
    # Image operations
    "images_to_pdf_with_watermark",
    # Rendering helpers
    "make_watermark_overlay",
    "load_font",
    # Utilities
    "parse_hex_color",
    "parse_page_range",
    "extract_image_dpi",
    "is_pdf_file",
    "is_image_file",
]

