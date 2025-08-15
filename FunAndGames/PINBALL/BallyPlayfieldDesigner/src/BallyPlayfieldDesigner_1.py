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

#!/usr/bin/env python3
import argparse
import math
from typing import Tuple, List, Optional

import cv2
import numpy as np
import ezdxf
from ezdxf.colors import int2rgb

# ---------------------------
# Config
# ---------------------------
WINDOW_NAME = "DXF Viewer (OpenCV)"
BG_COLOR = (0, 0, 0)          # Black background (B, G, R)
FG_COLOR = (255, 255, 255)    # Default white for entities
POINT_RADIUS = 2
ARC_SEGMENTS = 180            # Segments for approximating arcs/ellipses if needed
SPLINE_SAMPLES = 300          # Samples for spline approximation
MARGIN_PX = 20                # Margin around drawing when fitting to screen
INITIAL_W = 1280
INITIAL_H = 800
LINE_THICKNESS = 1            # Pixels

# Basic AutoCAD ACI -> BGR mapping (partial, common colors)
ACI_TO_BGR = {
    1:  (0, 0, 255),     # red
    2:  (0, 255, 255),   # yellow
    3:  (0, 255, 0),     # green
    4:  (255, 255, 0),   # cyan
    5:  (255, 0, 0),     # blue
    6:  (255, 0, 255),   # magenta
    7:  (255, 255, 255), # white
    8:  (128, 128, 128), # dark gray
    9:  (192, 192, 192), # light gray
}

# ---------------------------
# Geometry helpers
# ---------------------------
def compute_model_bbox(msp) -> Tuple[float, float, float, float]:
    """
    Walk modelspace and compute a conservative XY bounding box.
    """
    minx, miny = float("inf"), float("inf")
    maxx, maxy = float("-inf"), float("-inf")

    def update_xy(x, y):
        nonlocal minx, miny, maxx, maxy
        minx = min(minx, x)
        miny = min(miny, y)
        maxx = max(maxx, x)
        maxy = max(maxy, y)

    for e in msp:
        t = e.dxftype()
        try:
            if t == "LINE":
                (x1, y1, _), (x2, y2, _) = e.dxf.start, e.dxf.end
                update_xy(x1, y1); update_xy(x2, y2)
            elif t in ("LWPOLYLINE", "POLYLINE"):
                pts = list(e.get_points("xy")) if t == "LWPOLYLINE" else [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
                for x, y in pts:
                    update_xy(x, y)
            elif t == "CIRCLE":
                cx, cy, _ = e.dxf.center
                r = e.dxf.radius
                update_xy(cx - r, cy - r); update_xy(cx + r, cy + r)
            elif t == "ARC":
                cx, cy, _ = e.dxf.center
                r = e.dxf.radius
                update_xy(cx - r, cy - r); update_xy(cx + r, cy + r)
            elif t == "ELLIPSE":
                # Approximate via ellipse extreme box using major/minor axes
                center = e.dxf.center
                mx, my, _ = e.dxf.major_axis
                ratio = e.dxf.ratio
                ax = math.hypot(mx, my)
                bx = ax * ratio
                cx, cy = center[0], center[1]
                update_xy(cx - ax, cy - ax)
                update_xy(cx + ax, cy + ax)
                update_xy(cx - bx, cy - bx)
                update_xy(cx + bx, cy + bx)
            elif t == "SPLINE":
                # Approximate by sampling in XY
                pts = e.approximate(SPLINE_SAMPLES)
                for x, y, *_ in pts:
                    update_xy(x, y)
            elif t == "POINT":
                x, y, _ = e.dxf.location
                update_xy(x, y)
            # Ignore others for bbox (TEXT, DIMENSION, etc.) – can be added similarly
        except Exception:
            # Skip problematic entities for robustness
            pass

    if minx == float("inf"):
        # Empty drawing
        return 0.0, 0.0, 1.0, 1.0
    return minx, miny, maxx, maxy

def get_entity_color(doc, e) -> Tuple[int, int, int]:
    """Return BGR color for entity (ACI or truecolor or layer color), fallback to FG_COLOR."""
    # 256 = BYLAYER, 0 = ByBlock
    aci = e.dxf.color if hasattr(e.dxf, "color") else 256

    # Truecolor?
    if hasattr(e.dxf, "true_color") and e.dxf.true_color is not None:
        r, g, b = int2rgb(e.dxf.true_color)
        return (b, g, r)

    if aci not in (0, 256, None):
        return ACI_TO_BGR.get(aci, FG_COLOR)

    # ByLayer
    try:
        layer = doc.layers.get(e.dxf.layer)
        aci_layer = layer.color
        return ACI_TO_BGR.get(aci_layer, FG_COLOR)
    except Exception:
        return FG_COLOR

def world_to_screen(points: np.ndarray, pan: Tuple[float, float], scale: float, h: int) -> np.ndarray:
    """
    Map world XY to screen pixels.
    points: Nx2 array
    pan: (tx, ty) pixels
    scale: pixels per world-unit
    h: image height for Y flip (DXF Y up -> image Y down)
    """
    if points.size == 0:
        return points.astype(np.int32)
    pts = points.copy().astype(np.float64)
    # scale
    pts *= scale
    # flip Y
    pts[:, 1] *= -1.0
    # pan
    pts[:, 0] += pan[0]
    pts[:, 1] += pan[1]
    # shift down because origin is at top-left in image coords
    pts[:, 1] += h / 2.0
    return np.rint(pts).astype(np.int32)

# ---------------------------
# Renderer
# ---------------------------
class DXFRenderer:
    def __init__(self, doc, msp, width=INITIAL_W, height=INITIAL_H):
        self.doc = doc
        self.msp = msp
        self.w = width
        self.h = height

        # Fit/transform state
        xmin, ymin, xmax, ymax = compute_model_bbox(msp)
        self.model_bbox = (xmin, ymin, xmax, ymax)

        self.scale = 1.0    # pixels per model unit
        self.pan = (0.0, 0.0)  # pixel offset
        self._fit_to_view()

        # Interaction
        self.dragging = False
        self.last_mouse = (0, 0)

    def _fit_to_view(self):
        xmin, ymin, xmax, ymax = self.model_bbox
        dx = max(xmax - xmin, 1e-9)
        dy = max(ymax - ymin, 1e-9)
        sx = (self.w - 2 * MARGIN_PX) / dx
        sy = (self.h - 2 * MARGIN_PX) / dy
        self.scale = min(sx, sy)

        # Center model
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        # After scaling & Y flip, we place model center at (w/2, h/2)
        # Our world_to_screen already adds h/2 for Y; so pan X centers horizontally,
        # and pan Y recenters vertically around the flipped coords.
        # Compute where (cx, cy) would go with zero pan:
        p = np.array([[cx, cy]], dtype=np.float64)
        p_screen = world_to_screen(p, (0, 0), self.scale, self.h)[0]
        # desired center:
        target = np.array([self.w // 2, self.h // 2], dtype=np.float64)
        offset = target - p_screen
        self.pan = (float(offset[0]), float(offset[1] - self.h/2))  # subtract the +h/2 added in mapping

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
            # Wheel: positive = forward (zoom in), negative = backward
            delta = 1 if flags > 0 else -1
            factor = 1.2 if delta > 0 else (1 / 1.2)
            # Zoom about cursor: adjust pan so the cursor stays where it is
            # Convert cursor to world-ish pivot (approx in pixels):
            self.scale *= factor

    def draw(self) -> np.ndarray:
        canvas = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        canvas[:] = BG_COLOR

        for e in self.msp:
            color = get_entity_color(self.doc, e)
            t = e.dxftype()

            try:
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
                    cx, cy, _ = e.dxf.center
                    r = e.dxf.radius
                    center = world_to_screen(np.array([[cx, cy]]), self.pan, self.scale, self.h)[0]
                    rr = max(1, int(round(r * self.scale)))
                    cv2.circle(canvas, tuple(center), rr, color, LINE_THICKNESS, cv2.LINE_AA)

                elif t == "ARC":
                    cx, cy, _ = e.dxf.center
                    r = e.dxf.radius
                    start = e.dxf.start_angle
                    end = e.dxf.end_angle
                    center = world_to_screen(np.array([[cx, cy]]), self.pan, self.scale, self.h)[0]
                    rr = max(1, int(round(r * self.scale)))
                    # OpenCV angles go clockwise with 0 at 3 o'clock, and Y down; DXF is CCW with Y up.
                    # Easiest robust way: approximate with polyline.
                    angles = np.linspace(np.deg2rad(start), np.deg2rad(end), ARC_SEGMENTS)
                    pts = np.stack([cx + r*np.cos(angles), cy + r*np.sin(angles)], axis=1)
                    spts = world_to_screen(pts, self.pan, self.scale, self.h)
                    cv2.polylines(canvas, [spts], False, color, LINE_THICKNESS, cv2.LINE_AA)

                elif t == "ELLIPSE":
                    # Approximate with polyline sampling along param
                    cx, cy, _ = e.dxf.center
                    major = np.array(e.dxf.major_axis, dtype=float)
                    ratio = float(e.dxf.ratio)
                    # param from start to end
                    start = float(e.dxf.start_param)
                    end = float(e.dxf.end_param)
                    ts = np.linspace(start, end, ARC_SEGMENTS)
                    # Local ellipse points
                    u = major[:2]  # 2D major axis vector
                    if np.linalg.norm(u) < 1e-12:
                        continue
                    mu = u / np.linalg.norm(u)
                    # Create minor axis vector perpendicular to major in XY
                    mv = np.array([-mu[1], mu[0]], dtype=float) * (np.linalg.norm(u) * ratio)

                    xy = np.stack([cx + mu[0]*np.cos(ts)*np.linalg.norm(u) + mv[0]*np.sin(ts),
                                   cy + mu[1]*np.cos(ts)*np.linalg.norm(u) + mv[1]*np.sin(ts)], axis=1)
                    spts = world_to_screen(xy, self.pan, self.scale, self.h)
                    cv2.polylines(canvas, [spts], False, color, LINE_THICKNESS, cv2.LINE_AA)

                elif t == "SPLINE":
                    pts = e.approximate(SPLINE_SAMPLES)  # returns Nx3 points
                    pts2d = np.array([[p[0], p[1]] for p in pts], dtype=np.float64)
                    if pts2d.size:
                        spts = world_to_screen(pts2d, self.pan, self.scale, self.h)
                        cv2.polylines(canvas, [spts], False, color, LINE_THICKNESS, cv2.LINE_AA)

                elif t == "POINT":
                    x, y, _ = e.dxf.location
                    spt = world_to_screen(np.array([[x, y]]), self.pan, self.scale, self.h)[0]
                    cv2.circle(canvas, tuple(spt), POINT_RADIUS, color, -1, cv2.LINE_AA)

                # Add more entity types (e.g., TEXT, MTEXT) as needed.

            except Exception:
                # Ignore entity draw errors to keep viewer robust
                continue

        return canvas

# ---------------------------
# Main
# ---------------------------
def main():
    ap = argparse.ArgumentParser(description="Display a DXF file with OpenCV (pan/zoom).")
    ap.add_argument("dxf_file", help="Path to .dxf file")
    ap.add_argument("--width", type=int, default=INITIAL_W, help="Window width")
    ap.add_argument("--height", type=int, default=INITIAL_H, help="Window height")
    args = ap.parse_args()

    doc = ezdxf.readfile(args.dxf_file)
    msp = doc.modelspace()

    renderer = DXFRenderer(doc, msp, args.width, args.height)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_GUI_EXPANDED | cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(WINDOW_NAME, renderer.on_mouse)

    while True:
        frame = renderer.draw()
        cv2.imshow(WINDOW_NAME, frame)

        # key = cv2.waitKey(16) & 0xFF  # ~60 FPS
        # if key == 27:  # ESC
        #     break
        # elif key in (ord('f'), ord('F')):
        #     renderer._fit_to_view()
        # elif key == ord('+') or key == ord('='):
        #     renderer.scale *= 1.2
        # elif key == ord('-') or key == ord('_'):
        #     renderer.scale /= 1.2
        # elif key == ord('0'):
        #     renderer._fit_to_view()

        key = cv2.waitKey(16) & 0xFF  # ~60 FPS
        if key == 27:  # ESC
            break
        elif key in (ord('f'), ord('F')):
            renderer._fit_to_view()
        elif key == ord('+') or key == ord('='):
            renderer.scale *= 1.2
        elif key == ord('-') or key == ord('_'):
            renderer.scale /= 1.2
        elif key == ord('0'):
            renderer._fit_to_view()
        elif key == 81:  # Left arrow
            renderer.pan = (renderer.pan[0] - 20, renderer.pan[1])
        elif key == 83:  # Right arrow
            renderer.pan = (renderer.pan[0] + 20, renderer.pan[1])
        elif key == 82:  # Up arrow
            renderer.pan = (renderer.pan[0], renderer.pan[1] - 20)
        elif key == 84:  # Down arrow
            renderer.pan = (renderer.pan[0], renderer.pan[1] + 20)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
