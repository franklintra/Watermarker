import os
import sys
from typing import Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image, ImageOps

from .render import make_watermark_overlay
from .encoding import encode_image_for_pdf, save_image_with_format
from .utils import extract_image_dpi


def images_to_pdf_with_watermark(
    input_image_path: str,
    output_pdf: str,
    text: str,
    dpi: Optional[int] = None,
    img_format: str = "auto",
    jpeg_quality: int = 85,
    verbose: bool = False,
    angle: float = 35.0,
    opacity: float = 0.38,
    color: Tuple[int, int, int] = (112, 112, 112),
    target_frac: float = 0.6,
    min_font_frac: float = 0.03,
    max_font_frac: float = 0.12,
    line_spacing_frac: float = 0.2,
    sparsity: float = 1.3,
    font_path: Optional[str] = None,
    wrap: bool = True,
) -> None:
    out = fitz.open()
    try:
        with Image.open(input_image_path) as im:
            n_frames = getattr(im, "n_frames", 1) or 1
            for frame_index in range(n_frames):
                try:
                    im.seek(frame_index)
                except EOFError:
                    break
                frame = im.convert("RGB")
                frame = ImageOps.exif_transpose(frame)
                overlay = make_watermark_overlay(
                    frame.size,
                    text=text,
                    angle_deg=angle,
                    opacity=opacity,
                    color=color,
                    target_frac=target_frac,
                    min_font_frac=min_font_frac,
                    max_font_frac=max_font_frac,
                    line_spacing_frac=line_spacing_frac,
                    sparsity=sparsity,
                    font_path=font_path,
                    wrap=wrap,
                )
                composited = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")

                eff_dpi = dpi or extract_image_dpi(im) or 200
                w_pt = (composited.width * 72.0) / float(eff_dpi)
                h_pt = (composited.height * 72.0) / float(eff_dpi)

                img_bytes, chosen_fmt = encode_image_for_pdf(
                    composited, fmt=img_format, jpeg_quality=jpeg_quality
                )
                if verbose:
                    print(
                        f"Frame {frame_index+1}: encoded as {chosen_fmt.upper()} ({len(img_bytes)/1024:.1f} KiB)",
                        file=sys.stderr,
                    )

                page = out.new_page(width=w_pt, height=h_pt)
                page.insert_image(page.rect, stream=img_bytes, keep_proportion=False)
    finally:
        out.save(output_pdf)
        out.close()


def image_to_image_with_watermark(
    input_image_path: str,
    output_image_path: str,
    text: str,
    dpi: Optional[int] = None,
    jpeg_quality: int = 85,
    verbose: bool = False,
    angle: float = 35.0,
    opacity: float = 0.38,
    color: Tuple[int, int, int] = (112, 112, 112),
    target_frac: float = 0.6,
    min_font_frac: float = 0.03,
    max_font_frac: float = 0.12,
    line_spacing_frac: float = 0.2,
    sparsity: float = 1.3,
    font_path: Optional[str] = None,
    wrap: bool = True,
) -> None:
    """Watermark a single image and save to another image file.

    The output format is inferred from the output file extension.
    Preserves embedded DPI if available; otherwise uses provided dpi or 200.
    """
    with Image.open(input_image_path) as im:
        # Use first frame if animated
        try:
            im.seek(0)
        except Exception:
            pass

        # Normalize orientation
        base = ImageOps.exif_transpose(im)
        # Ensure we composite in RGBA space to retain transparency correctly
        base_rgba = base.convert("RGBA")

        overlay = make_watermark_overlay(
            base_rgba.size,
            text=text,
            angle_deg=angle,
            opacity=opacity,
            color=color,
            target_frac=target_frac,
            min_font_frac=min_font_frac,
            max_font_frac=max_font_frac,
            line_spacing_frac=line_spacing_frac,
            sparsity=sparsity,
            font_path=font_path,
            wrap=wrap,
        )

        composited = Image.alpha_composite(base_rgba, overlay)

        # Determine effective DPI
        emb_dpi = extract_image_dpi(im)
        eff_dpi = dpi or emb_dpi or 200
        save_kwargs = {"dpi": (eff_dpi, eff_dpi)}

        save_image_with_format(composited, output_image_path, dpi=eff_dpi, jpeg_quality=jpeg_quality, verbose=verbose)
