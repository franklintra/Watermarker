import os
from typing import Optional, Set, Tuple

from PIL import Image


def is_pdf_file(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(5)
            return head.startswith(b"%PDF-")
    except Exception:
        return False


def is_image_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def extract_image_dpi(pil_img: Image.Image) -> Optional[int]:
    info = getattr(pil_img, "info", {}) or {}
    if "dpi" in info:
        try:
            xdpi, ydpi = info["dpi"]
            if isinstance(xdpi, tuple):
                xdpi = xdpi[0]
            if isinstance(ydpi, tuple):
                ydpi = ydpi[0]
            avg = int(round((float(xdpi) + float(ydpi)) / 2.0))
            if avg > 0:
                return avg
        except Exception:
            pass
    if "jfif_density" in info:
        try:
            xden, yden = info.get("jfif_density", (0, 0))
            units = info.get("jfif_unit", info.get("jfif_units", 0))  # 1=DPI, 2=DPCM
            if units == 1:
                avg = int(round((float(xden) + float(yden)) / 2.0))
                if avg > 0:
                    return avg
            elif units == 2:
                avg = int(round(((float(xden) + float(yden)) / 2.0) * 2.54))
                if avg > 0:
                    return avg
        except Exception:
            pass
    return None


def parse_hex_color(s: str) -> Tuple[int, int, int]:
    s = s.strip()
    if s.startswith('#'):
        s = s[1:]
    if len(s) == 3:
        s = ''.join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError("Color must be in #RGB, #RRGGBB form")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return (r, g, b)


def parse_page_range(spec: str) -> Set[int]:
    """Parse page range like '1-3,5,7-' into set of 1-based numbers.

    Open-ended ranges like '7-' are represented with negative markers (-7) and
    should be resolved later when page count is known.
    """
    pages: Set[int] = set()
    if not spec:
        return pages
    parts = [p.strip() for p in spec.split(',') if p.strip()]
    for p in parts:
        if '-' in p:
            a, b = p.split('-', 1)
            a = a.strip()
            b = b.strip()
            if a and b:
                try:
                    start = int(a)
                    end = int(b)
                    if start > end:
                        start, end = end, start
                    for n in range(start, end + 1):
                        pages.add(n)
                except Exception:
                    continue
            elif a and not b:
                try:
                    start = int(a)
                    pages.add(-(start))
                except Exception:
                    continue
            elif b and not a:
                try:
                    end = int(b)
                    for n in range(1, end + 1):
                        pages.add(n)
                except Exception:
                    continue
        else:
            try:
                pages.add(int(p))
            except Exception:
                continue
    return pages
