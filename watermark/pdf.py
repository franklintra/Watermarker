import io
import os
import sys
from typing import List, Optional, Set, Tuple

import fitz  # PyMuPDF
from PIL import Image

from .render import make_watermark_overlay
from .encoding import encode_image_for_pdf, save_image_with_format
from .utils import is_image_file


def page_to_image(page, dpi: int = 200) -> Image.Image:
    """Render a PyMuPDF page to a PIL RGB image at given DPI."""
    scale = float(dpi) / 72.0
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    mode = "RGBA" if pix.alpha else "RGB"
    img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def flatten_with_watermark(
    page,
    text: str,
    dpi: int,
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
) -> Image.Image:
    base = page_to_image(page, dpi=dpi)
    overlay = make_watermark_overlay(
        base.size,
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
    composited = Image.alpha_composite(base.convert("RGBA"), overlay)
    return composited.convert("RGB")


def estimate_pdf_dpi(path: str, min_dpi: int = 60, max_dpi: int = 400) -> Optional[int]:
    """Estimate a sensible DPI based on the largest images on pages.

    Heuristic:
    - For each page, consider the image covering the largest area; if it covers >= 40% of the page, take its DPI as the page's candidate.
    - If no such large image exists, consider all images covering >= 20% and compute a weighted median by area coverage.
    - Clamp final estimate to [min_dpi, max_dpi].
    Returns None if no candidates are found.
    """
    try:
        with fitz.open(path) as doc:
            page_max_candidates: List[int] = []
            weighted_candidates: List[Tuple[int, float]] = []  # (dpi, weight)
            for page in doc:
                try:
                    rect = page.rect
                    page_area = rect.width * rect.height
                    images = page.get_images(full=True) or []
                    best_by_area: Optional[Tuple[float, int]] = None  # (area_ratio, dpi)
                    for img in images:
                        xref = img[0]
                        w_px = int(img[2]) if len(img) > 3 else None
                        h_px = int(img[3]) if len(img) > 3 else None
                        if not w_px or not h_px:
                            continue
                        try:
                            rects = page.get_image_rects(xref) or []
                        except Exception:
                            rects = []
                        for r in rects:
                            if r.width <= 0 or r.height <= 0:
                                continue
                            w_in = r.width / 72.0
                            h_in = r.height / 72.0
                            if w_in <= 0 or h_in <= 0:
                                continue
                            area_ratio = (r.width * r.height) / page_area if page_area else 0.0
                            dpi_x = w_px / w_in
                            dpi_y = h_px / h_in
                            cand = int(round(min(dpi_x, dpi_y)))
                            if cand <= 0:
                                continue
                            if best_by_area is None or area_ratio > best_by_area[0]:
                                best_by_area = (area_ratio, cand)
                            if area_ratio >= 0.2:
                                weighted_candidates.append((cand, area_ratio))
                    if best_by_area and best_by_area[0] >= 0.4:
                        page_max_candidates.append(best_by_area[1])
                except Exception:
                    continue

            est: Optional[int] = None
            if page_max_candidates:
                arr = sorted(page_max_candidates)
                mid = len(arr) // 2
                est = arr[mid] if len(arr) % 2 == 1 else (arr[mid - 1] + arr[mid]) // 2
            elif weighted_candidates:
                weighted_candidates.sort(key=lambda t: t[0])  # sort by dpi
                total_w = sum(w for _, w in weighted_candidates) or 1.0
                cum = 0.0
                target = total_w / 2.0
                chosen = weighted_candidates[0][0]
                for dpi_val, w in weighted_candidates:
                    cum += w
                    if cum >= target:
                        chosen = dpi_val
                        break
                est = int(round(chosen))

            if est is not None:
                return max(min_dpi, min(max_dpi, est))
    except Exception:
        pass
    return None


def raster_flatten_pdf_with_watermark(
    input_pdf: str,
    output_pdf: str,
    text: str,
    dpi: Optional[int] = None,
    max_auto_dpi: int = 400,
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
    pages: Optional[Set[int]] = None,
) -> None:
    with fitz.open(input_pdf) as doc:
        if dpi is None:
            est = estimate_pdf_dpi(input_pdf, 60, 400) or 200
            if max_auto_dpi > 0:
                dpi = min(est, max_auto_dpi)
            else:
                dpi = est
        if pages:
            actual_pages: Set[int] = set()
            total = len(doc)
            for n in pages:
                if n > 0:
                    if 1 <= n <= total:
                        actual_pages.add(n)
                else:
                    start = -n
                    for i in range(start, total + 1):
                        actual_pages.add(i)
            pages = actual_pages
        out = fitz.open()
        try:
            for idx, page in enumerate(doc, start=1):
                if pages is not None and idx not in pages:
                    continue
                rect = page.rect
                img = flatten_with_watermark(
                    page,
                    text=text,
                    dpi=int(dpi),
                    angle=angle,
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
                img_bytes, chosen_fmt = encode_image_for_pdf(img, fmt=img_format, jpeg_quality=jpeg_quality)
                if verbose:
                    print(
                        f"Page {idx}: encoded as {chosen_fmt.upper()} ({len(img_bytes)/1024:.1f} KiB)",
                        file=sys.stderr,
                    )

                new_page = out.new_page(width=rect.width, height=rect.height)
                new_page.insert_image(new_page.rect, stream=img_bytes, keep_proportion=False)
        finally:
            out.save(output_pdf)
            out.close()


def raster_flatten_pdf_to_images_with_watermark(
    input_pdf: str,
    output_image_path: str,
    text: str,
    dpi: Optional[int] = None,
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
    pages: Optional[Set[int]] = None,
    jpeg_quality: int = 85,
) -> list:
    """Rasterize a PDF to watermarked image file(s), based on output extension.

    - If exactly one page selected, writes to `output_image_path`.
    - If multiple pages selected, writes numbered files: `<stem>-001<ext>`, `<stem>-002<ext>`, ...
    Returns list of output file paths written.
    """
    outputs: list = []
    with fitz.open(input_pdf) as doc:
        # Determine effective DPI if not provided
        if dpi is None:
            est = estimate_pdf_dpi(input_pdf, 60, 400) or 200
            dpi = est

        # Resolve page selection
        selected: list[int] = []
        if pages:
            actual_pages: Set[int] = set()
            total = len(doc)
            for n in pages:
                if n > 0:
                    if 1 <= n <= total:
                        actual_pages.add(n)
                else:
                    start = -n
                    for i in range(start, total + 1):
                        actual_pages.add(i)
            selected = sorted(actual_pages)
        else:
            selected = list(range(1, len(doc) + 1))

        base_dir, base_name = os.path.split(output_image_path)
        stem, ext = os.path.splitext(base_name)

        seq = 0
        multi = len(selected) > 1
        for idx, page in enumerate(doc, start=1):
            if idx not in selected:
                continue
            seq += 1
            img = flatten_with_watermark(
                page,
                text=text,
                dpi=int(dpi),
                angle=angle,
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
            if multi:
                out_path = os.path.join(base_dir, f"{stem}-{seq:03d}{ext}")
            else:
                out_path = output_image_path
            save_image_with_format(img, out_path, dpi=dpi, jpeg_quality=jpeg_quality, verbose=verbose)
            outputs.append(out_path)

    if verbose:
        if len(outputs) > 1:
            print(f"Wrote {len(outputs)} images: e.g., {outputs[0]}", file=sys.stderr)
        elif outputs:
            print(f"Wrote image: {outputs[0]}", file=sys.stderr)
    return outputs


def analyze_pdf(input_pdf: str, max_auto_dpi: int = 400) -> int:
    try:
        with fitz.open(input_pdf) as doc:
            print(f"Analyzing: {input_pdf}")
            all_candidates = []
            for i, page in enumerate(doc, start=1):
                rect = page.rect
                w_in = rect.width / 72.0
                h_in = rect.height / 72.0
                print(f"Page {i}: {rect.width:.1f}x{rect.height:.1f} pt ({w_in:.2f}x{h_in:.2f} in)")
                images = page.get_images(full=True) or []
                page_area = rect.width * rect.height
                if not images:
                    print("  No embedded images")
                for img in images:
                    try:
                        xref = img[0]
                        w_px = int(img[2]) if len(img) > 3 else None
                        h_px = int(img[3]) if len(img) > 3 else None
                        rects = page.get_image_rects(xref) or []
                    except Exception:
                        rects = []
                        w_px, h_px = None, None
                    for r in rects:
                        w_in_img = r.width / 72.0
                        h_in_img = r.height / 72.0
                        area_ratio = (r.width * r.height) / page_area if page_area else 0.0
                        if w_px and h_px and w_in_img > 0 and h_in_img > 0:
                            dpi_x = w_px / w_in_img
                            dpi_y = h_px / h_in_img
                            dpi_cand = int(round(min(dpi_x, dpi_y)))
                            if area_ratio >= 0.3:
                                all_candidates.append(dpi_cand)
                            print(
                                f"  Image xref {xref}: {w_px}x{h_px} px over {w_in_img:.2f}x{h_in_img:.2f} in, "
                                f"area {area_ratio*100:.1f}% -> ~{dpi_x:.0f}x{dpi_y:.0f} DPI (cand {dpi_cand})"
                            )
                        else:
                            print(
                                f"  Image xref {xref}: {w_px}x{h_px} px at rect {w_in_img:.2f}x{h_in_img:.2f} in (insufficient data)"
                            )
            est = estimate_pdf_dpi(input_pdf, 60, 400)
            if est is None:
                print("No DPI candidates found; default would be 200.")
            else:
                chosen = min(est, max_auto_dpi) if max_auto_dpi > 0 else est
                print(f"Estimated DPI (heuristic): {est}")
                if chosen != est:
                    print(f"Chosen DPI after clamp (max {max_auto_dpi}): {chosen}")
        return 0
    except Exception as e:
        print(f"Analyze failed: {e}", file=sys.stderr)
        return 1
