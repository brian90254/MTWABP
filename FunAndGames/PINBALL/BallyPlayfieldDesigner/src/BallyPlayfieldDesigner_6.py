# BRIAN COX copyright 2025
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
#   cd Dropbox/GitHub/MTWABP/FunAndGames/PINBALL/BallyPlayfieldDesigner/
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src"
#   python src/BallyPlayfieldDesigner_1.py DXF/your.dxf
# Optional:
#   python src/BallyPlayfieldDesigner_1.py DXF/your.dxf --width 1600 --height 1000


# Controls
# Drag: pan
# Mouse wheel: zoom
# Arrows: pan (step 20 px)
# + / -: zoom in/out
# F or 0: fit all
# A: open OpenCV picker to add more DXFs (multi-select)
# 1-9: toggle layer visibility
# L: list layers in console
# Esc: quit


#!/usr/bin/env python3
import argparse
import math
import os
from pathlib import Path
from typing import Tuple, List, Optional

import cv2
import numpy as np
import ezdxf
from ezdxf.colors import int2rgb

from ezdxf.math import OCS, Vec3

# ---------------------------
# Config
# ---------------------------
WINDOW_NAME = "DXF Viewer (OpenCV)"
PICKER_WIN = "DXF Picker"
BG_COLOR = (0, 0, 0)          # Black background (B, G, R)
FG_COLOR = (255, 255, 255)    # Default white for entities
POINT_RADIUS = 2
ARC_SEGMENTS = 180
SPLINE_SAMPLES = 300
MARGIN_PX = 20
# INITIAL_W = 1280
# INITIAL_H = 800
INITIAL_W = 500
INITIAL_H = 1000
LINE_THICKNESS = 1

# Arrow keycodes after & 0xFF (on most platforms)
#KEY_LEFT, KEY_UP, KEY_RIGHT, KEY_DOWN = 81, 82, 83, 84
KEY_LEFT, KEY_UP, KEY_RIGHT, KEY_DOWN = 3, 1, 2, 0

# Basic AutoCAD ACI -> BGR mapping
ACI_TO_BGR = {
    1:  (0, 0, 255),
    2:  (0, 255, 255),
    3:  (0, 255, 0),
    4:  (255, 255, 0),
    5:  (255, 0, 0),
    6:  (255, 0, 255),
    7:  (255, 255, 255),
    8:  (128, 128, 128),
    9:  (192, 192, 192),
}

# Colors to differentiate stacked files (layers)
LAYER_COLORS = [
    (255, 255, 255),
    (0, 0, 255),
    (0, 255, 0),
    (255, 0, 0),
    (0, 255, 255),
    (255, 255, 0),
    (255, 0, 255),
    (128, 128, 128),
    (0, 128, 255),
]

# ---------------------------
# KEY helpers
# ---------------------------
def layer_idx_from_key(key: int, bank: int) -> int:
    """Map number keys to a layer index within the current 10-layer bank.
       1–9 => slots 0–8, 0 => slot 9. Returns -1 if not a number key."""
    if ord('1') <= key <= ord('9'):
        return bank * 10 + (key - ord('1'))
    if key == ord('0'):
        return bank * 10 + 9
    return -1

# ---------------------------
# ARC helpers
# ---------------------------
def ccw_sweep_deg(start_deg: float, end_deg: float) -> np.ndarray:
    """Return two angles [start, end] unwrapped for a positive CCW sweep in degrees."""
    s = float(start_deg) % 360.0
    e = float(end_deg) % 360.0
    sweep = (e - s) % 360.0
    if sweep == 0.0:
        sweep = 360.0
    return np.array([s, s + sweep], dtype=np.float64)

def ccw_sweep_rad(start_par: float, end_par: float) -> np.ndarray:
    """Like ccw_sweep_deg but for radians (used by ELLIPSE start_param/end_param)."""
    s = float(start_par) % (2*np.pi)
    e = float(end_par) % (2*np.pi)
    sweep = (e - s) % (2*np.pi)
    if sweep == 0.0:
        sweep = 2*np.pi
    return np.array([s, s + sweep], dtype=np.float64)

# ---------------------------
# Geometry helpers
# ---------------------------
def compute_model_bbox(msp) -> Tuple[float, float, float, float]:
    minx, miny = float("inf"), float("inf")
    maxx, maxy = float("-inf"), float("-inf")

    def update_xy(x, y):
        nonlocal minx, miny, maxx, maxy
        minx = min(minx, x); miny = min(miny, y)
        maxx = max(maxx, x); maxy = max(maxy, y)

    for e in msp:
        t = e.dxftype()
        try:
            if t == "LINE":
                (x1, y1, _), (x2, y2, _) = e.dxf.start, e.dxf.end
                update_xy(x1, y1); update_xy(x2, y2)
            elif t in ("LWPOLYLINE", "POLYLINE"):
                pts = (list(e.get_points("xy")) if t == "LWPOLYLINE"
                       else [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices])
                for x, y in pts: update_xy(x, y)
            elif t in ("CIRCLE", "ARC"):
                cx, cy, _ = e.dxf.center; r = e.dxf.radius
                update_xy(cx - r, cy - r); update_xy(cx + r, cy + r)
            elif t == "ELLIPSE":
                cx, cy, _ = e.dxf.center
                mx, my, _ = e.dxf.major_axis
                ratio = e.dxf.ratio
                a = math.hypot(mx, my); b = a * ratio
                update_xy(cx - a, cy - a); update_xy(cx + a, cy + a)
                update_xy(cx - b, cy - b); update_xy(cx + b, cy + b)
            elif t == "SPLINE":
                pts = e.approximate(SPLINE_SAMPLES)
                for x, y, *_ in pts: update_xy(x, y)
            elif t == "POINT":
                x, y, _ = e.dxf.location; update_xy(x, y)
        except Exception:
            pass

    if minx == float("inf"):
        return 0.0, 0.0, 1.0, 1.0
    return minx, miny, maxx, maxy

def get_entity_color(doc, e) -> Tuple[int, int, int]:
    aci = e.dxf.color if hasattr(e.dxf, "color") else 256
    if hasattr(e.dxf, "true_color") and e.dxf.true_color is not None:
        r, g, b = int2rgb(e.dxf.true_color)
        return (b, g, r)
    if aci not in (0, 256, None):
        return ACI_TO_BGR.get(aci, FG_COLOR)
    try:
        layer = doc.layers.get(e.dxf.layer)
        return ACI_TO_BGR.get(layer.color, FG_COLOR)
    except Exception:
        return FG_COLOR

def world_to_screen(points: np.ndarray, pan: Tuple[float, float], scale: float, h: int) -> np.ndarray:
    if points.size == 0:
        return points.astype(np.int32)
    pts = points.astype(np.float64)
    pts *= scale
    pts[:, 1] *= -1.0
    pts[:, 0] += pan[0]
    pts[:, 1] += pan[1] + h / 2.0
    return np.rint(pts).astype(np.int32)

# ---------------------------
# Layer + Renderer
# ---------------------------
class DXFLayer:
    def __init__(self, path: str, doc, msp, color_override=None, visible=True):
        self.path = path
        self.name = os.path.basename(path)
        self.doc = doc
        self.msp = msp
        self.color_override = color_override
        self.visible = visible

class DXFRenderer:
    def __init__(self, layers: List[DXFLayer], width=INITIAL_W, height=INITIAL_H):
        self.layers = layers
        self.w = width
        self.h = height
        self._update_union_bbox()
        self.scale = 1.0
        self.pan = (0.0, 0.0)
        self._fit_to_view()
        self.dragging = False
        self.last_mouse = (0, 0)

    def _update_union_bbox(self):
        if not self.layers:
            self.model_bbox = (0, 0, 1, 1)
            return
        mins = [float("inf"), float("inf")]
        maxs = [float("-inf"), float("-inf")]
        any_found = False
        for layer in self.layers:
            xmin, ymin, xmax, ymax = compute_model_bbox(layer.msp)
            if xmin <= xmax and ymin <= ymax:
                mins[0] = min(mins[0], xmin); mins[1] = min(mins[1], ymin)
                maxs[0] = max(maxs[0], xmax); maxs[1] = max(maxs[1], ymax)
                any_found = True
        self.model_bbox = (mins[0], mins[1], maxs[0], maxs[1]) if any_found else (0, 0, 1, 1)

    def _fit_to_view(self):
        xmin, ymin, xmax, ymax = self.model_bbox
        dx = max(xmax - xmin, 1e-9)
        dy = max(ymax - ymin, 1e-9)
        sx = (self.w - 2 * MARGIN_PX) / dx
        sy = (self.h - 2 * MARGIN_PX) / dy
        self.scale = min(sx, sy)
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        p = np.array([[cx, cy]], dtype=np.float64)
        p_screen = world_to_screen(p, (0, 0), self.scale, self.h)[0]
        target = np.array([self.w // 2, self.h // 2], dtype=np.float64)
        offset = target - p_screen
        self.pan = (float(offset[0]), float(offset[1] - self.h / 2))

    def on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.dragging = True
            self.last_mouse = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging = False
        elif event == cv2.EVENT_MOUSEMOVE and self.dragging:
            dx = x - self.last_mouse[0]
            dy = y - self.last_mouse[1]
            self.pan = (self.pan[0] + dx, self.pan[1] + dy)
            self.last_mouse = (x, y)
        elif event == cv2.EVENT_MOUSEWHEEL:
            delta = 1 if flags > 0 else -1
            factor = 1.2 if delta > 0 else (1/1.2)
            self.scale *= factor

    def draw(self) -> np.ndarray:
        canvas = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        canvas[:] = BG_COLOR
        for layer in self.layers:
            if not layer.visible:
                continue
            doc, msp = layer.doc, layer.msp
            for e in msp:
                try:
                    color = layer.color_override if layer.color_override is not None else get_entity_color(doc, e)
                    t = e.dxftype()
                    if t == "LINE":
                        p1 = np.array([[e.dxf.start.x, e.dxf.start.y]])
                        p2 = np.array([[e.dxf.end.x,   e.dxf.end.y]])
                        s1 = world_to_screen(p1, self.pan, self.scale, self.h)[0]
                        s2 = world_to_screen(p2, self.pan, self.scale, self.h)[0]
                        cv2.line(canvas, tuple(s1), tuple(s2), color, LINE_THICKNESS, cv2.LINE_AA)
                    elif t in ("LWPOLYLINE", "POLYLINE"):
                        if t == "LWPOLYLINE":
                            pts = np.array([[x, y] for (x, y, *_) in e.get_points("xy")], dtype=np.float64)
                            is_closed = bool(e.closed)
                        else:
                            pts = np.array([[v.dxf.location.x, v.dxf.location.y] for v in e.vertices], dtype=np.float64)
                            is_closed = bool(e.is_closed)
                        if pts.size:
                            spts = world_to_screen(pts, self.pan, self.scale, self.h)
                            cv2.polylines(canvas, [spts], is_closed, color, LINE_THICKNESS, cv2.LINE_AA)
                    elif t == "CIRCLE":
                        cx, cy, _ = e.dxf.center; r = e.dxf.radius
                        center = world_to_screen(np.array([[cx, cy]]), self.pan, self.scale, self.h)[0]
                        rr = max(1, int(round(r * self.scale)))
                        cv2.circle(canvas, tuple(center), rr, color, LINE_THICKNESS, cv2.LINE_AA)
                    # elif t == "ARC":
                    #     cx, cy, _ = e.dxf.center; r = e.dxf.radius
                    #     start = e.dxf.start_angle; end = e.dxf.end_angle
                    #     angles = np.linspace(np.deg2rad(start), np.deg2rad(end), ARC_SEGMENTS)
                    #     pts = np.stack([cx + r*np.cos(angles), cy + r*np.sin(angles)], axis=1)
                    #     spts = world_to_screen(pts, self.pan, self.scale, self.h)
                    #     cv2.polylines(canvas, [spts], False, color, LINE_THICKNESS, cv2.LINE_AA)

                    elif t == "ARC":
                        # Unwrap to CCW sweep
                        s_deg, e_deg = ccw_sweep_deg(e.dxf.start_angle, e.dxf.end_angle)
                        cx, cy, cz = e.dxf.center
                        r = float(e.dxf.radius)

                        # Sample angles CCW
                        segs = max(2, int(ARC_SEGMENTS * (e_deg - s_deg) / 360.0))
                        ang = np.deg2rad(np.linspace(s_deg, e_deg, segs))

                        # Points in OCS
                        x_ocs = cx + r * np.cos(ang)
                        y_ocs = cy + r * np.sin(ang)

                        # Map OCS -> WCS if needed (handles mirrored/rotated planes)
                        extr = getattr(e.dxf, "extrusion", (0.0, 0.0, 1.0))
                        if tuple(extr) != (0.0, 0.0, 1.0):
                            ocs = OCS(extr)
                            pts_w = [ocs.to_wcs(Vec3(x, y, 0.0)) for x, y in zip(x_ocs, y_ocs)]
                            pts2d = np.array([(p.x, p.y) for p in pts_w], dtype=np.float64)
                        else:
                            pts2d = np.stack([x_ocs, y_ocs], axis=1)

                        spts = world_to_screen(pts2d, self.pan, self.scale, self.h)
                        cv2.polylines(canvas, [spts], False, color, LINE_THICKNESS, cv2.LINE_AA)

                    # elif t == "ELLIPSE":
                    #     cx, cy, _ = e.dxf.center
                    #     major = np.array(e.dxf.major_axis, dtype=float); ratio = float(e.dxf.ratio)
                    #     start = float(e.dxf.start_param); end = float(e.dxf.end_param)
                    #     ts = np.linspace(start, end, ARC_SEGMENTS)
                    #     u = major[:2]
                    #     if np.linalg.norm(u) < 1e-12: continue
                    #     L = np.linalg.norm(u)
                    #     mu = u / L
                    #     mv = np.array([-mu[1], mu[0]], dtype=float) * (L * ratio)
                    #     xy = np.stack([cx + mu[0]*np.cos(ts)*L + mv[0]*np.sin(ts),
                    #                    cy + mu[1]*np.cos(ts)*L + mv[1]*np.sin(ts)], axis=1)
                    #     spts = world_to_screen(xy, self.pan, self.scale, self.h)
                    #     cv2.polylines(canvas, [spts], False, color, LINE_THICKNESS, cv2.LINE_AA)

                    elif t == "ELLIPSE":
                        cx, cy, cz = e.dxf.center
                        major = np.array(e.dxf.major_axis, dtype=float)  # OCS vector
                        ratio = float(e.dxf.ratio)                       # minor/major
                        if np.linalg.norm(major[:2]) < 1e-12:
                            continue

                        # Unwrap parameters to CCW sweep in radians
                        s_par, e_par = ccw_sweep_rad(e.dxf.start_param, e.dxf.end_param)
                        segs = max(2, int(ARC_SEGMENTS * (e_par - s_par) / (2*np.pi)))
                        ts = np.linspace(s_par, e_par, segs)

                        # Build ellipse in OCS: major length L, unit axes mu (major), mv (minor)
                        L = np.linalg.norm(major[:2])
                        mu = major[:2] / L
                        mv = np.array([-mu[1], mu[0]], dtype=float) * (L * ratio)

                        x_ocs = cx + mu[0]*np.cos(ts)*L + mv[0]*np.sin(ts)
                        y_ocs = cy + mu[1]*np.cos(ts)*L + mv[1]*np.sin(ts)

                        extr = getattr(e.dxf, "extrusion", (0.0, 0.0, 1.0))
                        if tuple(extr) != (0.0, 0.0, 1.0):
                            ocs = OCS(extr)
                            pts_w = [ocs.to_wcs(Vec3(x, y, 0.0)) for x, y in zip(x_ocs, y_ocs)]
                            pts2d = np.array([(p.x, p.y) for p in pts_w], dtype=np.float64)
                        else:
                            pts2d = np.stack([x_ocs, y_ocs], axis=1)

                        spts = world_to_screen(pts2d, self.pan, self.scale, self.h)
                        cv2.polylines(canvas, [spts], False, color, LINE_THICKNESS, cv2.LINE_AA)

                    elif t == "SPLINE":
                        pts = e.approximate(SPLINE_SAMPLES)
                        pts2d = np.array([[p[0], p[1]] for p in pts], dtype=np.float64)
                        if pts2d.size:
                            spts = world_to_screen(pts2d, self.pan, self.scale, self.h)
                            cv2.polylines(canvas, [spts], False, color, LINE_THICKNESS, cv2.LINE_AA)
                    elif t == "POINT":
                        x, y, _ = e.dxf.location
                        spt = world_to_screen(np.array([[x, y]]), self.pan, self.scale, self.h)[0]
                        cv2.circle(canvas, tuple(spt), POINT_RADIUS, color, -1, cv2.LINE_AA)
                except Exception:
                    continue
        return canvas

# ---------------------------
# OpenCV file picker (no Tkinter)
# ---------------------------
def list_dxf_files(start_dir: str) -> List[Path]:
    base = Path(start_dir).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    return sorted([p for p in base.glob("**/*.dxf") if p.is_file()])

def draw_picker_page(canvas, title, items: List[Path], selected: set, cursor_idx: int, page: int, per_page: int):
    canvas[:] = 30  # dark gray background
    h, w = canvas.shape[:2]
    margin = 16
    y = 36

    def put(text, y, scale=0.6, color=(255,255,255), thick=1):
        cv2.putText(canvas, text, (margin, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)

    put(title, y, 0.7); y += 16
    put("↑/↓ move   PgUp/PgDn page   Space select   Enter confirm   Esc cancel", y, 0.5, (200,200,200)); y += 20
    start = page * per_page
    end = min(len(items), start + per_page)

    for i, p in enumerate(items[start:end], start):
        is_cursor = (i == cursor_idx)
        is_selected = (p in selected)
        prefix = ("▶ " if is_cursor else "  ")
        mark = ("[x] " if is_selected else "[ ] ")
        text = f"{prefix}{mark}{p.name}"
        color = (0,255,255) if is_cursor else (255,255,255)
        put(text, y, 0.6, color); y += 22

    put(f"Page {page+1}/{max(1, (len(items)+per_page-1)//per_page)}  •  {len(items)} file(s)", h-12, 0.5, (180,180,180))

def opencv_file_picker(start_dir="DXF", multi=False) -> List[str]:
    files = list_dxf_files(start_dir)
    if not files:
        raise RuntimeError(f"No .dxf files found in {Path(start_dir).resolve()}")

    per_page = 20
    page = 0
    cursor = 0
    selected = set()

    cv2.namedWindow(PICKER_WIN, cv2.WINDOW_GUI_EXPANDED | cv2.WINDOW_AUTOSIZE)
    canvas = np.zeros((600, 800, 3), dtype=np.uint8)

    while True:
        draw_picker_page(canvas, f"Select DXF file{'s' if multi else ''} from: {Path(start_dir).resolve()}",
                         files, selected, cursor, page, per_page)
        cv2.imshow(PICKER_WIN, canvas)
        key = cv2.waitKey(0) & 0xFF

        if key in (27, ord('q')):  # Esc / q
            cv2.destroyWindow(PICKER_WIN)
            return []  # cancel

        elif key == KEY_UP:
            cursor = max(0, cursor - 1)
            if cursor < page * per_page:
                page = max(0, page - 1)

        elif key == KEY_DOWN:
            cursor = min(len(files) - 1, cursor + 1)
            if cursor >= (page + 1) * per_page:
                page = min((len(files) - 1) // per_page, page + 1)

        elif key == ord(' '):
            if multi:
                p = files[cursor]
                if p in selected: selected.remove(p)
                else: selected.add(p)

        elif key == 13 or key == 10:  # Enter
            cv2.destroyWindow(PICKER_WIN)
            if multi:
                return [str(p) for p in (selected if selected else [files[cursor]])]
            else:
                return [str(files[cursor])]

        elif key == 216 or key == 153:  # PageUp (platform-dependent)
            page = max(0, page - 1)
            cursor = min(cursor, min(len(files)-1, (page+1)*per_page - 1))

        elif key == 222 or key == 154:  # PageDown (platform-dependent)
            max_page = max(0, (len(files) - 1) // per_page)
            page = min(max_page, page + 1)
            cursor = max(cursor, page * per_page)

# ---------------------------
# Loading helpers
# ---------------------------
def load_layer_from_path(path: str, color_idx: int) -> DXFLayer:
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    color = LAYER_COLORS[color_idx % len(LAYER_COLORS)]
    #return DXFLayer(path=path, doc=doc, msp=msp, color_override=color, visible=True)
    return DXFLayer(path=path, doc=doc, msp=msp, color_override=None, visible=True)

# ---------------------------
# Main
# ---------------------------
def main():
    ap = argparse.ArgumentParser(description="Display one or more DXF files with OpenCV (no Tkinter).")
    ap.add_argument("dxf_file", nargs="?", help="Initial .dxf file (optional; if omitted, an OpenCV picker opens in ./DXF)")
    ap.add_argument("--width", type=int, default=INITIAL_W, help="Window width")
    ap.add_argument("--height", type=int, default=INITIAL_H, help="Window height")
    ap.add_argument("--dxf-dir", default="DXF", help='Directory to search/pick from (default: "DXF")')
    args = ap.parse_args()

    # Initial file(s)
    if args.dxf_file:
        first_path = args.dxf_file
    else:
        picks = opencv_file_picker(args.dxf_dir, multi=False)
        if not picks:
            print("No file selected.")
            return
        first_path = picks[0]

    layers = [load_layer_from_path(first_path, 0)]
    renderer = DXFRenderer(layers, args.width, args.height)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_GUI_EXPANDED | cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WINDOW_NAME, renderer.on_mouse)

    print("Hotkeys: A=Add DXF (picker), 1–9 toggle layers, L=list layers, F/0=fit, +/-=zoom, arrows=pan, Esc=quit")

    # INIT STARTING LAYER BANK
    layer_bank = 0  # which group of 10 layers the number keys operate on

    while True:
        frame = renderer.draw()
        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(16) & 0xFF  # ~60 FPS

        if key == 27:  # Esc
            break

        elif key in (ord('f'), ord('F'), ord('0')):
            renderer._update_union_bbox()
            renderer._fit_to_view()

        elif key == ord('+') or key == ord('='):
            renderer.scale *= 1.2

        elif key == ord('-') or key == ord('_'):
            renderer.scale /= 1.2

        elif key == KEY_LEFT:
            renderer.pan = (renderer.pan[0] - 20, renderer.pan[1])
        elif key == KEY_RIGHT:
            renderer.pan = (renderer.pan[0] + 20, renderer.pan[1])
        elif key == KEY_UP:
            renderer.pan = (renderer.pan[0], renderer.pan[1] - 20)
        elif key == KEY_DOWN:
            renderer.pan = (renderer.pan[0], renderer.pan[1] + 20)

        # Add more DXFs as layers (multi-select)
        elif key in (ord('a'), ord('A')):
            picks = opencv_file_picker(args.dxf_dir, multi=True)
            if picks:
                start_idx = len(renderer.layers)
                added = 0
                for i, p in enumerate(picks):
                    try:
                        layer = load_layer_from_path(p, start_idx + i)
                        renderer.layers.append(layer)
                        added += 1
                    except Exception as ex:
                        print(f"Failed to load {p}: {ex}")
                if added:
                    print(f"Added {added} layer(s). Press 'L' to list and 1–9 to toggle visibility.")

        # # Toggle visibility of layers 1..9
        # elif key in range(ord('1'), ord('9') + 1):
        #     idx = key - ord('1')  # 0-based
        #     if 0 <= idx < len(renderer.layers):
        #         renderer.layers[idx].visible = not renderer.layers[idx].visible

        # Change the active bank (10 layers per bank)
        elif key in (ord(','), ord('<')):  # prev bank
            max_bank = max(0, (len(renderer.layers) - 1) // 10)
            layer_bank = max(0, layer_bank - 1)
            print(f"Layer bank: {layer_bank+1}/{max_bank+1}  "
                  f"(layers {layer_bank*10+1}-{min((layer_bank+1)*10, len(renderer.layers))})")

        elif key in (ord('.'), ord('>')):  # next bank
            max_bank = max(0, (len(renderer.layers) - 1) // 10)
            layer_bank = min(max_bank, layer_bank + 1)
            print(f"Layer bank: {layer_bank+1}/{max_bank+1}  "
                  f"(layers {layer_bank*10+1}-{min((layer_bank+1)*10, len(renderer.layers))})")

        # Toggle visibility using number keys within the current bank
        elif key in (*range(ord('1'), ord('9') + 1), ord('0')):
            idx = layer_idx_from_key(key, layer_bank)
            if 0 <= idx < len(renderer.layers):
                lay = renderer.layers[idx]
                lay.visible = not lay.visible
                state = "ON" if lay.visible else "OFF"
                print(f"Toggled layer {idx+1} [{lay.name}] -> {state}")

        # List layers
        elif key in (ord('l'), ord('L')):
            print("\nLayers:")
            for i, lay in enumerate(renderer.layers, 1):
                flag = "✓" if lay.visible else "×"
                col = lay.color_override if lay.color_override is not None else ("layer colors")
                print(f"  {i:2d}) [{flag}] {lay.name}  color={col}")

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
