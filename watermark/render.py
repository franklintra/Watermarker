from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont


def load_font(font_size: int, font_path: Optional[str] = None) -> ImageFont.FreeTypeFont:
    """Try to load a TrueType font. Fall back to PIL default if none found.

    If font_path is provided, try it first.
    """
    if font_path:
        try:
            return ImageFont.truetype(font_path, font_size)
        except Exception:
            pass
    candidates = [
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, font_size)
        except Exception:
            continue
    return ImageFont.load_default()


def make_watermark_overlay(
    size_px,
    text: str,
    angle_deg: float = 35.0,
    opacity: float = 0.38,
    color: Tuple[int, int, int] = (112, 112, 112),
    target_frac: float = 0.6,
    min_font_frac: float = 0.03,
    max_font_frac: float = 0.12,
    line_spacing_frac: float = 0.2,
    sparsity: float = 1.3,
    font_path: Optional[str] = None,
    wrap: bool = True,
):
    """Create an RGBA watermark overlay image of given pixel size.

    - Auto-sizes font based on page width and text length.
    - Wraps text into multiple lines if needed to fit a target width.
    - Repeats the text block on a grid, then rotates layer for a diagonal pattern.
    - Uses gray (#808080) with specified opacity (0..1).
    """
    w, h = size_px
    if w <= 0 or h <= 0:
        raise ValueError("Invalid overlay size")

    meas_img = Image.new("L", (10, 10))
    meas_draw = ImageDraw.Draw(meas_img)

    def text_bbox(text_s: str, font_obj: ImageFont.ImageFont):
        try:
            b = meas_draw.textbbox((0, 0), text_s, font=font_obj)
            return b[2] - b[0], b[3] - b[1]
        except Exception:
            return meas_draw.textsize(text_s, font=font_obj)

    target_width_px = max(100, int(w * target_frac))
    min_font_px = max(18, int(w * min_font_frac))
    max_font_px = max(min_font_px, int(w * max_font_frac))

    def best_single_line_font_size() -> int:
        lo, hi = min_font_px, max_font_px
        best = lo
        while lo <= hi:
            mid = (lo + hi) // 2
            f = load_font(mid, font_path)
            tw, _ = text_bbox(text, f)
            if tw <= target_width_px:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    single_fs = best_single_line_font_size()
    single_font = load_font(single_fs, font_path)
    single_w, _ = text_bbox(text, single_font)
    need_wrap = wrap and (single_w > int(w * 0.9))

    def wrap_text_to_width(text_s: str, font_obj: ImageFont.ImageFont, max_w_px: int):
        words = text_s.split()
        if not words:
            return [text_s]
        lines = []
        current = words[0]
        for word in words[1:]:
            trial = current + " " + word
            tw, _ = text_bbox(trial, font_obj)
            if tw <= max_w_px:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)

        fixed_lines = []
        for ln in lines:
            tw, _ = text_bbox(ln, font_obj)
            if tw <= max_w_px or len(ln) <= 1:
                fixed_lines.append(ln)
                continue
            buf = ""
            for ch in ln:
                trial = buf + ch
                tw2, _ = text_bbox(trial, font_obj)
                if tw2 <= max_w_px or not buf:
                    buf = trial
                else:
                    fixed_lines.append(buf)
                    buf = ch
            if buf:
                fixed_lines.append(buf)
        return fixed_lines

    if need_wrap:
        wrap_fs = max(single_fs, min(max_font_px, int(w * 0.08)))
        font = load_font(wrap_fs, font_path)
        lines = wrap_text_to_width(text, font, target_width_px)
    else:
        font = single_font
        lines = [text]

    line_spacing = int(max(4, font.size * line_spacing_frac))
    line_sizes = [text_bbox(ln, font) for ln in lines]
    block_w = max((lw for lw, lh in line_sizes), default=0)
    block_h = sum((lh for lw, lh in line_sizes)) + line_spacing * (len(lines) - 1)

    tile_w, tile_h = w * 2, h * 2
    tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)

    step_x = max(1, int(block_w * 1.25 * sparsity))
    step_y = max(1, int(block_h * 1.6 * sparsity))

    fill = (
        int(color[0]),
        int(color[1]),
        int(color[2]),
        max(0, min(255, int(255 * opacity))),
    )

    row = 0
    y = -block_h
    while y < tile_h + step_y:
        offset = (row % 2) * (step_x // 2)
        x = -block_w - step_x
        while x < tile_w + step_x:
            yy = y
            for (ln, (lw, lh)) in zip(lines, line_sizes):
                draw.text((x + offset, yy), ln, font=font, fill=fill)
                yy += lh + line_spacing
            x += step_x
        row += 1
        y += step_y

    rotated = tile.rotate(angle_deg, resample=Image.BICUBIC, expand=True)
    left = max(0, (rotated.width - w) // 2)
    top = max(0, (rotated.height - h) // 2)
    overlay = rotated.crop((left, top, left + w, top + h))
    return overlay
