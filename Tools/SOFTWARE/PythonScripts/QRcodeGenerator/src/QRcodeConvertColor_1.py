# BRIAN COX copyright 2025
#
# SHORTCUT SCRIPT:
#   runQRcodeGenerator.command
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
#   cd Dropbox/GitHub/MTWABP/Tools/SOFTWARE/PythonScripts/QRcodeGenerator/
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src" AND PASS HTML LINK ARGUMENTS
#   python src/QRcodeGenerator_1.py "https://example.com/page1"
# ----------------------------

#!/usr/bin/env python3
# """
# qr_colorize_diamond_dual.py

# Colorize a black/white QR image so BOTH dark and light modules follow a
# dual-color diamond (Manhattan distance) pattern:

#   Even ring: dark -> BLUE,  light -> CYAN
#   Odd  ring: dark -> RED,   light -> YELLOW

# This keeps the functional structure (dark vs light) but renders each with
# its own alternating color pair based on ring parity.

# Usage:
#     python qr_colorize_diamond_dual.py --input qr.png --output qr_dual.png \
#         --ring-width 2 --center auto

# Options let you customize colors and whether to keep the outer margin white.

# Notes:
# - Keep the “light” colors sufficiently light for reliable scanning.
# - Matte, high-contrast colors scan more reliably than shiny/translucent.
# """

import argparse
import cv2
import numpy as np
from typing import Tuple


def parse_bgr(s: str) -> Tuple[int, int, int]:
    parts = [int(x) for x in s.split(",")]
    if len(parts) != 3:
        raise ValueError("Color must be 'B,G,R' with three integers 0-255.")
    for v in parts:
        if not (0 <= v <= 255):
            raise ValueError("Each color channel must be in 0..255.")
    return tuple(parts)  # type: ignore[return-value]


def auto_center(mask: np.ndarray) -> Tuple[int, int]:
    """Compute centroid of dark pixels (mask==1)."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        h, w = mask.shape
        return w // 2, h // 2
    cx = int(np.round(xs.mean()))
    cy = int(np.round(ys.mean()))
    return cx, cy


def colorize_qr_dual(
    img: np.ndarray,
    ring_width: int = 2,
    center_mode: str = "geo",
    thresh_mode: str = "otsu",
    # Even ring colors (dark/light)
    even_dark: Tuple[int, int, int] = (255, 0, 0),    # BLUE (BGR)
    even_light: Tuple[int, int, int] = (255, 255, 0),  # CYAN (BGR)
    # Odd ring colors (dark/light)
    odd_dark: Tuple[int, int, int] = (0, 0, 255),     # RED (BGR)
    odd_light: Tuple[int, int, int] = (0, 255, 255),   # YELLOW (BGR)
    preserve_margin_white: bool = True,
    margin_threshold: int = 4,
) -> np.ndarray:
    """
    Colorize both dark and light QR modules with alternating ring color pairs.

    - ring_width: thickness in pixels for Manhattan rings.
    - center_mode: 'geo' or 'auto' (centroid of dark pixels).
    - thresh_mode: 'otsu' or 'fixed'.
    - preserve_margin_white: if True, leave pixels outside the QR quiet zone white.
      (Quiet zone is inferred by expanding the bounding box of dark pixels by margin_threshold.)
    - margin_threshold: how many pixels to expand bounding box to approximate quiet zone.
    """
    # Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img.copy()

    # Threshold to binary (dark vs light)
    if thresh_mode == "otsu":
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        _, bw = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)

    # Dark modules are black (0)
    dark_mask = (bw == 0).astype(np.uint8)  # 1 where dark, 0 where light
    h, w = bw.shape

    # Center for diamond rings
    if center_mode == "auto":
        cx, cy = auto_center(dark_mask)
    else:
        cx, cy = w // 2, h // 2

    # Manhattan distance & rings
    xs = np.arange(w, dtype=np.int32)
    ys = np.arange(h, dtype=np.int32)
    X, Y = np.meshgrid(xs, ys)
    manhattan = np.abs(X - cx) + np.abs(Y - cy)
    rings = (manhattan // max(1, ring_width)) % 2  # 0 even, 1 odd

    # Output buffer (start white)
    out = np.full((h, w, 3), (255, 255, 255), dtype=np.uint8)

    # Optional: limit coloring to QR + quiet zone area so margins stay white
    if preserve_margin_white:
        ys_nonzero, xs_nonzero = np.nonzero(dark_mask)
        if len(xs_nonzero) > 0:
            xmin, xmax = xs_nonzero.min(), xs_nonzero.max()
            ymin, ymax = ys_nonzero.min(), ys_nonzero.max()
            xmin = max(0, xmin - margin_threshold)
            xmax = min(w - 1, xmax + margin_threshold)
            ymin = max(0, ymin - margin_threshold)
            ymax = min(h - 1, ymax + margin_threshold)
            roi_mask = np.zeros_like(dark_mask, dtype=np.uint8)
            roi_mask[ymin:ymax + 1, xmin:xmax + 1] = 1
        else:
            roi_mask = np.ones_like(dark_mask, dtype=np.uint8)
    else:
        roi_mask = np.ones_like(dark_mask, dtype=np.uint8)

    # Build masks
    even_ring = (rings == 0) & (roi_mask == 1)
    odd_ring  = (rings == 1) & (roi_mask == 1)

    # Within each ring parity, split dark vs light
    even_dark_mask  = even_ring & (dark_mask == 1)
    even_light_mask = even_ring & (dark_mask == 0)
    odd_dark_mask   = odd_ring  & (dark_mask == 1)
    odd_light_mask  = odd_ring  & (dark_mask == 0)

    # Apply colors
    out[even_dark_mask]  = even_dark
    out[even_light_mask] = even_light
    out[odd_dark_mask]   = odd_dark
    out[odd_light_mask]  = odd_light

    return out


def main():
    ap = argparse.ArgumentParser(description="Dual-color QR diamond pattern (colors for both dark and light modules).")
    ap.add_argument("--input", required=True, help="Path to input QR image (black/white).")
    ap.add_argument("--output", required=True, help="Path to save output image (PNG recommended).")
    ap.add_argument("--ring-width", type=int, default=2, help="Manhattan ring thickness in pixels.")
    ap.add_argument("--center", default="geo", choices=["geo", "auto"], help="Ring origin: image center or centroid.")
    ap.add_argument("--thresh", default="otsu", choices=["otsu", "fixed"], help="Binarization mode.")
    ap.add_argument("--preserve-margin-white", action="store_true",
                    help="Keep margins (outside QR quiet zone) white.")
    # Custom colors (B,G,R) if you want to override defaults
    ap.add_argument("--even-dark", default="255,0,0", help="Even ring DARK color (B,G,R). Default BLUE.")
    ap.add_argument("--even-light", default="255,255,0", help="Even ring LIGHT color (B,G,R). Default CYAN.")
    ap.add_argument("--odd-dark", default="0,0,255", help="Odd ring DARK color (B,G,R). Default RED.")
    ap.add_argument("--odd-light", default="0,255,255", help="Odd ring LIGHT color (B,G,R). Default YELLOW.")
    ap.add_argument("--margin-threshold", type=int, default=4, help="Quiet-zone expansion (pixels) for margin preservation.")
    args = ap.parse_args()

    img = cv2.imread(args.input, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise SystemExit(f"Failed to read input: {args.input}")

    out = colorize_qr_dual(
        img=img,
        ring_width=args.ring_width,
        center_mode=args.center,
        thresh_mode=args.thresh,
        even_dark=parse_bgr(args.even_dark),
        even_light=parse_bgr(args.even_light),
        odd_dark=parse_bgr(args.odd_dark),
        odd_light=parse_bgr(args.odd_light),
        preserve_margin_white=args.preserve_margin_white,
        margin_threshold=args.margin_threshold,
    )

    ok = cv2.imwrite(args.output, out)
    if not ok:
        raise SystemExit(f"Failed to write output: {args.output}")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()

