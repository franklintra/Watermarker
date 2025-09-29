import io
import os
import sys
from typing import Optional, Tuple

from PIL import Image


def encode_image_for_pdf(img: Image.Image, fmt: str = "auto", jpeg_quality: int = 85) -> Tuple[bytes, str]:
    """Encode PIL image to bytes for PDF embedding.

    fmt: 'auto'|'png'|'jpeg' — if 'auto', pick the smaller of PNG or JPEG.
    Returns (bytes, chosen_format)
    """
    fmt = (fmt or "auto").lower()
    if fmt not in {"auto", "png", "jpeg"}:
        fmt = "auto"
    if fmt == "png":
        bio = io.BytesIO()
        img.save(bio, format="PNG", optimize=True)
        return bio.getvalue(), "png"
    if fmt == "jpeg":
        bio = io.BytesIO()
        img.save(bio, format="JPEG", quality=jpeg_quality, optimize=True, subsampling="4:2:0")
        return bio.getvalue(), "jpeg"
    bio_png = io.BytesIO()
    img.save(bio_png, format="PNG", optimize=True)
    png_bytes = bio_png.getvalue()
    bio_jpg = io.BytesIO()
    img.save(bio_jpg, format="JPEG", quality=jpeg_quality, optimize=True, subsampling="4:2:0")
    jpg_bytes = bio_jpg.getvalue()
    if len(jpg_bytes) < len(png_bytes):
        return jpg_bytes, "jpeg"
    return png_bytes, "png"


def save_image_with_format(
    img: Image.Image,
    output_image_path: str,
    dpi: Optional[int] = None,
    jpeg_quality: int = 85,
    verbose: bool = False,
) -> None:
    """Save an image inferring format from file extension.

    Handles alpha channel for formats that support it. Adds DPI metadata when possible.
    """
    ext = os.path.splitext(output_image_path)[1].lower()
    ext_to_fmt = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".webp": "WEBP",
        ".bmp": "BMP",
        ".tif": "TIFF",
        ".tiff": "TIFF",
    }
    fmt = ext_to_fmt.get(ext, "PNG")

    # JPEG/BMP don't support alpha
    out_img = img
    if fmt in {"JPEG", "BMP"}:
        out_img = img.convert("RGB")

    eff_dpi = dpi or 200
    save_kwargs = {"dpi": (eff_dpi, eff_dpi)}

    if fmt == "JPEG":
        save_kwargs.update({
            "quality": jpeg_quality,
            "optimize": True,
            "subsampling": "4:2:0",
        })
    elif fmt == "PNG":
        save_kwargs.update({
            "optimize": True,
        })

    if verbose:
        print(f"Saving image as {fmt} to {output_image_path}", file=sys.stderr)

    out_img.save(output_image_path, format=fmt, **save_kwargs)

