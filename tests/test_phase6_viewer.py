import pytest
import os
import re
from netlist import prepare_svg_for_rendering

try:
    import pymupdf
    from PIL import Image
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

def test_splitjoin_styling_in_svg():
    sample_svg = """<svg width="400" height="200" xmlns="http://www.w3.org/2000/svg">
<path class="splitjoinBody" d="M 10 10 L 20 20 Z" />
<path class="wire" d="M 30 30 L 40 40" />
<rect class="splitjoinBody" x="50" y="50" width="10" height="10" />
<rect class="box" x="70" y="70" width="20" height="20" />
</svg>"""

    styled = prepare_svg_for_rendering(sample_svg)

    # 1. splitjoin path gets filled with black
    splitjoin_paths = re.findall(r'<path[^>]*splitjoinBody[^>]*>', styled, re.IGNORECASE)
    assert len(splitjoin_paths) >= 1
    assert 'fill="#000"' in splitjoin_paths[0]

    # 2. normal wire path gets fill="none"
    normal_paths = re.findall(r'<path[^>]*class="wire"[^>]*>', styled, re.IGNORECASE)
    assert len(normal_paths) >= 1
    assert 'fill="none"' in normal_paths[0]

    # 3. splitjoin rect gets filled with black
    splitjoin_rects = re.findall(r'<rect[^>]*splitjoinBody[^>]*>', styled, re.IGNORECASE)
    assert len(splitjoin_rects) >= 1
    assert 'fill="#000"' in splitjoin_rects[0]

    # 4. normal box rect gets fill="none"
    normal_rects = re.findall(r'<rect[^>]*class="box"[^>]*>', styled, re.IGNORECASE)
    assert len(normal_rects) >= 1
    assert 'fill="none"' in normal_rects[0]

def test_pixmap_capping_large_netlist():
    if not PYMUPDF_AVAILABLE:
        pytest.skip("PyMuPDF not available")

    # Generate a massive SVG (8000x8000 points)
    huge_svg = """<svg width="8000" height="8000" viewBox="0 0 8000 8000" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="8000" height="8000" fill="white"/>
<line x1="100" y1="100" x2="7900" y2="7900" stroke="black"/>
</svg>"""

    doc = pymupdf.open(stream=huge_svg.encode("utf-8"), filetype="svg")
    page = doc[0]

    MAX_PIXMAP_DIM = 4096
    scale = 5.0  # max zoom 500%
    page_w = page.rect.width
    page_h = page.rect.height
    est_w = page_w * (scale * 96.0 / 72.0)
    est_h = page_h * (scale * 96.0 / 72.0)

    if est_w > MAX_PIXMAP_DIM or est_h > MAX_PIXMAP_DIM:
        scale_cap = min(MAX_PIXMAP_DIM / max(est_w, 1.0), MAX_PIXMAP_DIM / max(est_h, 1.0))
        scale = scale * scale_cap

    dpi = max(24, int(96 * scale))
    pix = page.get_pixmap(dpi=dpi)

    assert pix.width <= MAX_PIXMAP_DIM
    assert pix.height <= MAX_PIXMAP_DIM
    assert pix.samples is not None
