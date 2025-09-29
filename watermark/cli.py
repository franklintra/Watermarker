import argparse
import os
import sys
from typing import Optional, Set
import fitz  # PyMuPDF

from .pdf import raster_flatten_pdf_with_watermark, estimate_pdf_dpi
from .images import images_to_pdf_with_watermark
from .utils import (
    is_pdf_file,
    is_image_file,
    parse_hex_color,
    parse_page_range,
)


class SmartArgumentParser(argparse.ArgumentParser):
    def error(self, message):  # type: ignore[override]
        msg = message
        if (
            isinstance(message, str)
            and "the following arguments are required" in message
            and "input" in message
            and "output" in message
        ):
            msg = message.rstrip(".\n ") + ", and TEXT (positional) or --text"
        super().error(msg)


def parse_args(argv=None):
    p = SmartArgumentParser(
        description="Raster-flatten a PDF or image and overlay a diagonal repeated watermark.",
        usage="%(prog)s [options] input output TEXT  (or: %(prog)s [options] --text TEXT input output)",
        epilog=(
            "Examples:\n"
            "  %(prog)s in.pdf out.pdf \"Bernard Nicod\"\n"
            "  %(prog)s --text \"Bernard Nicod\" in.pdf out.pdf\n"
            "  %(prog)s --format jpeg --quality 85 --angle 40 in.pdf out.pdf \"Confidential\"\n"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("input", metavar="input", help="Path to input PDF or image")
    p.add_argument("output", metavar="output", help="Path to output PDF")
    p.add_argument(
        "text_positional",
        metavar="TEXT",
        nargs="?",
        help="REQUIRED watermark text (positional). Alternatively use --text.",
    )

    # Watermark styling
    p.add_argument(
        "--text",
        dest="text",
        metavar="TEXT",
        help="REQUIRED if positional TEXT not provided; overrides positional if both given",
    )
    p.add_argument("--angle", type=float, default=35.0, help="Watermark angle in degrees")
    p.add_argument("--opacity", type=float, default=0.38, help="Watermark opacity (0..1)")
    p.add_argument("--color", type=str, default="#707070", help="Watermark color as hex, e.g. #707070")
    p.add_argument("--sparsity", type=float, default=1.3, help="Pattern spacing multiplier (higher is more sparse)")
    p.add_argument("--target-width-frac", type=float, default=0.6, help="Target fraction of page width for text block")
    p.add_argument("--min-font-frac", type=float, default=0.03, help="Min font size as fraction of page width")
    p.add_argument("--max-font-frac", type=float, default=0.12, help="Max font size as fraction of page width")
    p.add_argument("--line-spacing-frac", type=float, default=0.2, help="Line spacing as fraction of font size")
    p.add_argument("--font", dest="font_path", type=str, default=None, help="Path to a .ttf/.ttc font file to use")
    p.add_argument("--no-wrap", action="store_true", help="Disable wrapping; force single-line watermark")

    # Rasterization / encoding
    p.add_argument("--dpi", type=str, default="auto", help="Rasterization DPI: integer or 'auto'")
    p.add_argument("--min-auto-dpi", type=int, default=60, help="Lower bound for auto DPI (PDF only)")
    p.add_argument("--max-auto-dpi", type=int, default=400, help="Upper bound for auto DPI (PDF only)")
    p.add_argument("--format", choices=["auto", "png", "jpeg"], default="auto", help="Image format to embed in PDF")
    p.add_argument("--quality", type=int, default=85, help="JPEG quality (if format is jpeg or auto)")
    p.add_argument("--pages", type=str, default=None, help="Page selection for PDFs, e.g. '1-3,5,7-'")

    # Utilities
    p.add_argument("--analyze", action="store_true", help="Analyze input and print DPI details; do not write output")
    p.add_argument("--verbose", action="store_true", help="Verbose per-page/frame logging to stderr")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    inpath = args.input
    outpath = args.output
    text = args.text if args.text is not None else args.text_positional
    if not text:
        print("Error: watermark text is required (provide as positional or --text).", file=sys.stderr)
        return 2

    if not os.path.isfile(inpath):
        print(f"Error: input file not found: {inpath}", file=sys.stderr)
        return 2

    dpi_opt: Optional[int]
    if isinstance(args.dpi, str) and args.dpi.strip().lower() == "auto":
        dpi_opt = None
    else:
        try:
            dpi_val = int(args.dpi)
            if dpi_val < 50 or dpi_val > 1200:
                print("Warning: unusual DPI; using auto instead.", file=sys.stderr)
                dpi_opt = None
            else:
                dpi_opt = dpi_val
        except Exception:
            dpi_opt = None

    try:
        color = parse_hex_color(args.color)
    except Exception as e:
        print(f"Error: invalid --color value: {e}", file=sys.stderr)
        return 2

    pages_set: Optional[Set[int]] = None
    if args.pages:
        pages_set = parse_page_range(args.pages)

    try:
        if args.analyze:
            if is_pdf_file(inpath):
                from .pdf import analyze_pdf as _analyze

                return _analyze(inpath, max_auto_dpi=args.max_auto_dpi)
            elif is_image_file(inpath):
                from PIL import Image as _Image
                from .utils import extract_image_dpi as _extract

                with _Image.open(inpath) as im:
                    emb = _extract(im)
                    print(f"Image: {im.width}x{im.height} px, embedded DPI: {emb if emb else 'n/a'}")
                return 0
            else:
                print("Analyze: unsupported input.", file=sys.stderr)
                return 2

        if is_pdf_file(inpath):
            eff_dpi = dpi_opt or min(
                (estimate_pdf_dpi(inpath, args.min_auto_dpi, args.max_auto_dpi) or 200),
                args.max_auto_dpi if args.max_auto_dpi > 0 else 1200,
            )
            if dpi_opt is None:
                print(f"Info: using DPI {eff_dpi} (auto)", file=sys.stderr)
            raster_flatten_pdf_with_watermark(
                inpath,
                outpath,
                text,
                dpi=eff_dpi,
                max_auto_dpi=args.max_auto_dpi,
                img_format=args.format,
                jpeg_quality=args.quality,
                verbose=args.verbose,
                angle=args.angle,
                opacity=args.opacity,
                color=color,
                target_frac=args.target_width_frac,
                min_font_frac=args.min_font_frac,
                max_font_frac=args.max_font_frac,
                line_spacing_frac=args.line_spacing_frac,
                sparsity=args.sparsity,
                font_path=args.font_path,
                wrap=(not args.no_wrap),
                pages=pages_set,
            )
        elif is_image_file(inpath):
            images_to_pdf_with_watermark(
                inpath,
                outpath,
                text,
                dpi=dpi_opt,
                img_format=args.format,
                jpeg_quality=args.quality,
                verbose=args.verbose,
                angle=args.angle,
                opacity=args.opacity,
                color=color,
                target_frac=args.target_width_frac,
                min_font_frac=args.min_font_frac,
                max_font_frac=args.max_font_frac,
                line_spacing_frac=args.line_spacing_frac,
                sparsity=args.sparsity,
                font_path=args.font_path,
                wrap=(not args.no_wrap),
            )
        else:
            try:
                with fitz.open(inpath):
                    pass
                eff_dpi = dpi_opt or min(
                    (estimate_pdf_dpi(inpath, args.min_auto_dpi, args.max_auto_dpi) or 200),
                    args.max_auto_dpi if args.max_auto_dpi > 0 else 1200,
                )
                if dpi_opt is None:
                    print(f"Info: using DPI {eff_dpi} (auto)", file=sys.stderr)
                raster_flatten_pdf_with_watermark(
                    inpath,
                    outpath,
                    text,
                    dpi=eff_dpi,
                    max_auto_dpi=args.max_auto_dpi,
                    img_format=args.format,
                    jpeg_quality=args.quality,
                    verbose=args.verbose,
                    angle=args.angle,
                    opacity=args.opacity,
                    color=color,
                    target_frac=args.target_width_frac,
                    min_font_frac=args.min_font_frac,
                    max_font_frac=args.max_font_frac,
                    line_spacing_frac=args.line_spacing_frac,
                    sparsity=args.sparsity,
                    font_path=args.font_path,
                    wrap=(not args.no_wrap),
                    pages=pages_set,
                )
            except Exception:
                try:
                    images_to_pdf_with_watermark(
                        inpath,
                        outpath,
                        text,
                        dpi=dpi_opt,
                        img_format=args.format,
                        jpeg_quality=args.quality,
                        verbose=args.verbose,
                        angle=args.angle,
                        opacity=args.opacity,
                        color=color,
                        target_frac=args.target_width_frac,
                        min_font_frac=args.min_font_frac,
                        max_font_frac=args.max_font_frac,
                        line_spacing_frac=args.line_spacing_frac,
                        sparsity=args.sparsity,
                        font_path=args.font_path,
                        wrap=(not args.no_wrap),
                    )
                except Exception:
                    print("Error: unsupported input format or unreadable file.", file=sys.stderr)
                    return 3
    except Exception as e:
        print(f"Failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
