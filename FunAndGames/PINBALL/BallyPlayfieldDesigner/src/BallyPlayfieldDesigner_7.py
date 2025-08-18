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
import math, argparse, os
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import ezdxf
from ezdxf.colors import int2rgb
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea, QCheckBox, QFileDialog, QDockWidget
)

# --------- Simple renderer pieces (trimmed to essentials) ----------
BG_COLOR = (0,0,0)
FG_COLOR = (255,255,255)
LINE_THICKNESS = 1
POINT_RADIUS = 2
ARC_SEGMENTS = 180
SPLINE_SAMPLES = 300
MARGIN_PX = 20

ACI_TO_BGR = {
    1:(0,0,255),2:(0,255,255),3:(0,255,0),4:(255,255,0),
    5:(255,0,0),6:(255,0,255),7:(255,255,255),
}

def compute_model_bbox(msp) -> Tuple[float,float,float,float]:
    minx,miny,maxx,maxy = float("inf"),float("inf"),float("-inf"),float("-inf")
    def up(x,y):
        nonlocal minx,miny,maxx,maxy
        minx=min(minx,x); miny=min(miny,y); maxx=max(maxx,x); maxy=max(maxy,y)
    for e in msp:
        t = e.dxftype()
        try:
            if t == "LINE":
                (x1,y1,_),(x2,y2,_) = e.dxf.start, e.dxf.end; up(x1,y1); up(x2,y2)
            elif t in ("LWPOLYLINE","POLYLINE"):
                pts = (list(e.get_points("xy")) if t=="LWPOLYLINE"
                       else [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices])
                for x,y in pts: up(x,y)
            elif t in ("CIRCLE","ARC"):
                cx,cy,_ = e.dxf.center; r=e.dxf.radius; up(cx-r,cy-r); up(cx+r,cy+r)
            elif t == "ELLIPSE":
                cx,cy,_=e.dxf.center; mx,my,_=e.dxf.major_axis; ratio=e.dxf.ratio
                a = math.hypot(mx,my); b=a*ratio
                for dx in (-a,a): up(cx+dx,cy+dx); up(cx+dx,cy-dx)  # quick bound
            elif t == "SPLINE":
                for x,y,*_ in e.approximate(SPLINE_SAMPLES): up(x,y)
            elif t == "POINT":
                x,y,_=e.dxf.location; up(x,y)
        except Exception: pass
    if minx==float("inf"): return (0,0,1,1)
    return (minx,miny,maxx,maxy)

def get_entity_color(doc, e):
    aci = getattr(e.dxf, "color", 256)
    if getattr(e.dxf, "true_color", None) is not None:
        r,g,b = int2rgb(e.dxf.true_color); return (b,g,r)
    if aci not in (0,256,None): return ACI_TO_BGR.get(aci, FG_COLOR)
    try:
        layer = doc.layers.get(e.dxf.layer); return ACI_TO_BGR.get(layer.color, FG_COLOR)
    except Exception: return FG_COLOR

def world_to_screen(points: np.ndarray, pan: Tuple[float,float], scale: float, h: int) -> np.ndarray:
    if points.size == 0: return points.astype(np.int32)
    pts = points.astype(np.float64)
    pts *= scale; pts[:,1] *= -1.0
    pts[:,0] += pan[0]; pts[:,1] += pan[1] + h/2.0
    return np.rint(pts).astype(np.int32)

class DXFLayer:
    def __init__(self, path, doc, msp, color=None, visible=True):
        self.path = path
        self.name = os.path.basename(path)
        self.doc = doc
        self.msp = msp
        self.color = color
        self.visible = visible

def load_layer(path: str, color=(255,255,255)) -> DXFLayer:
    doc = ezdxf.readfile(path)
    return DXFLayer(path, doc, doc.modelspace(), color==None, True)

class DXFRenderer:
    #def __init__(self, layers: List[DXFLayer], w=1280, h=800):
    def __init__(self, layers: List[DXFLayer], w=500, h=1000):
        self.layers = layers; self.w=w; self.h=h
        self._update_bbox(); self.scale=1.0; self.pan=(0.0,0.0); self.fit()

    def _update_bbox(self):
        if not self.layers: self.bbox=(0,0,1,1); return
        xs,ys,Xs,Ys=[],[],[],[]
        for L in self.layers:
            xmin,ymin,xmax,ymax = compute_model_bbox(L.msp)
            xs.append(xmin); ys.append(ymin); Xs.append(xmax); Ys.append(ymax)
        self.bbox = (min(xs),min(ys),max(Xs),max(Ys))

    def fit(self):
        xmin,ymin,xmax,ymax = self.bbox
        dx=max(xmax-xmin,1e-9); dy=max(ymax-ymin,1e-9)
        sx=(self.w-2*MARGIN_PX)/dx; sy=(self.h-2*MARGIN_PX)/dy
        self.scale=min(sx,sy)
        cx=(xmin+xmax)/2; cy=(ymin+ymax)/2
        p = world_to_screen(np.array([[cx,cy]]), (0,0), self.scale, self.h)[0]
        target = np.array([self.w//2, self.h//2], dtype=np.float64)
        offset = target - p
        self.pan = (float(offset[0]), float(offset[1]-self.h/2))

    def draw(self) -> np.ndarray:
        canvas = np.zeros((self.h, self.w, 3), np.uint8); canvas[:] = BG_COLOR
        for L in self.layers:
            if not L.visible: continue
            doc, msp = L.doc, L.msp
            for e in msp:
                try:
                    color = L.color or get_entity_color(doc, e)
                    t=e.dxftype()
                    if t=="LINE":
                        p1=np.array([[e.dxf.start.x,e.dxf.start.y]]); p2=np.array([[e.dxf.end.x,e.dxf.end.y]])
                        s1=world_to_screen(p1,self.pan,self.scale,self.h)[0]; s2=world_to_screen(p2,self.pan,self.scale,self.h)[0]
                        cv2.line(canvas, tuple(s1), tuple(s2), color, LINE_THICKNESS, cv2.LINE_AA)
                    elif t in ("LWPOLYLINE","POLYLINE"):
                        if t=="LWPOLYLINE":
                            pts=np.array([[x,y] for (x,y,*_) in e.get_points("xy")], dtype=np.float64); closed=bool(e.closed)
                        else:
                            pts=np.array([[v.dxf.location.x,v.dxf.location.y] for v in e.vertices], dtype=np.float64); closed=bool(e.is_closed)
                        if pts.size:
                            spts=world_to_screen(pts,self.pan,self.scale,self.h); cv2.polylines(canvas,[spts],closed,color,LINE_THICKNESS,cv2.LINE_AA)
                    elif t=="CIRCLE":
                        cx,cy,_=e.dxf.center; r=e.dxf.radius
                        c=world_to_screen(np.array([[cx,cy]]),self.pan,self.scale,self.h)[0]; rr=max(1,int(round(r*self.scale)))
                        cv2.circle(canvas, tuple(c), rr, color, LINE_THICKNESS, cv2.LINE_AA)
                    elif t=="ARC":
                        cx,cy,_=e.dxf.center; r=e.dxf.radius; a1,a2=e.dxf.start_angle,e.dxf.end_angle
                        # CCW unwrap
                        s=a1%360; sweep=(a2-s)%360; sweep = 360 if sweep==0 else sweep
                        segs=max(2,int(ARC_SEGMENTS*sweep/360))
                        ang=np.deg2rad(np.linspace(s, s+sweep, segs))
                        pts=np.stack([cx+r*np.cos(ang), cy+r*np.sin(ang)], axis=1)
                        spts=world_to_screen(pts,self.pan,self.scale,self.h); cv2.polylines(canvas,[spts],False,color,LINE_THICKNESS,cv2.LINE_AA)
                    elif t=="ELLIPSE":
                        cx,cy,_=e.dxf.center; major=np.array(e.dxf.major_axis,dtype=float); ratio=float(e.dxf.ratio)
                        L=np.linalg.norm(major[:2]); 
                        if L<1e-12: continue
                        mu=major[:2]/L; mv=np.array([-mu[1],mu[0]],float)*(L*ratio)
                        s=e.dxf.start_param; ep=e.dxf.end_param; sw=(ep-s)%(2*np.pi); sw=2*np.pi if sw==0 else sw
                        ts=np.linspace(s,s+sw,ARC_SEGMENTS)
                        xy=np.stack([cx+mu[0]*np.cos(ts)*L+mv[0]*np.sin(ts), cy+mu[1]*np.cos(ts)*L+mv[1]*np.sin(ts)], axis=1)
                        spts=world_to_screen(xy,self.pan,self.scale,self.h); cv2.polylines(canvas,[spts],False,color,LINE_THICKNESS,cv2.LINE_AA)
                    elif t=="SPLINE":
                        pts=e.approximate(SPLINE_SAMPLES); pts2d=np.array([[p[0],p[1]] for p in pts], float)
                        if pts2d.size: spts=world_to_screen(pts2d,self.pan,self.scale,self.h); cv2.polylines(canvas,[spts],False,color,LINE_THICKNESS,cv2.LINE_AA)
                    elif t=="POINT":
                        x,y,_=e.dxf.location; spt=world_to_screen(np.array([[x,y]]),self.pan,self.scale,self.h)[0]
                        cv2.circle(canvas, tuple(spt), POINT_RADIUS, color, -1, cv2.LINE_AA)
                except Exception: continue
        return canvas

# --------- Qt UI ----------
class ImageView(QLabel):
    def __init__(self, renderer: DXFRenderer):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.renderer = renderer
        self.setFocusPolicy(Qt.StrongFocus)
        self._dragging = False
        self._last = None

    def wheelEvent(self, e):
        delta = e.angleDelta().y()
        factor = 1.2 if delta > 0 else (1/1.2)
        self.renderer.scale *= factor

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dragging = True
            self._last = e.position().toPoint()

    def mouseMoveEvent(self, e):
        if self._dragging:
            p = e.position().toPoint()
            dx = p.x() - self._last.x()
            dy = p.y() - self._last.y()
            px, py = self.renderer.pan
            self.renderer.pan = (px + dx, py + dy)
            self._last = p

    def mouseReleaseEvent(self, e):
        self._dragging = False

    def keyPressEvent(self, e):
        key = e.key()
        px, py = self.renderer.pan
        if key == Qt.Key_Left:  self.renderer.pan = (px - 20, py)
        elif key == Qt.Key_Right: self.renderer.pan = (px + 20, py)
        elif key == Qt.Key_Up:   self.renderer.pan = (px, py - 20)
        elif key == Qt.Key_Down: self.renderer.pan = (px, py + 20)
        elif key in (Qt.Key_F, Qt.Key_0): self.renderer._update_bbox(); self.renderer.fit()

class LayerPanel(QWidget):
    def __init__(self, window, renderer: DXFRenderer):
        super().__init__()
        self.window = window
        self.renderer = renderer
        self.v = QVBoxLayout(self); self.v.setContentsMargins(8,8,8,8); self.v.setSpacing(6)

        top = QHBoxLayout()
        add_btn = QPushButton("Add DXF…")
        add_btn.clicked.connect(self.on_add)
        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(lambda: (self.renderer._update_bbox(), self.renderer.fit()))
        top.addWidget(add_btn); top.addWidget(fit_btn); top.addStretch(1)
        self.v.addLayout(top)

        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.body = QWidget(); self.body_layout = QVBoxLayout(self.body); self.body_layout.addStretch(1)
        self.scroll.setWidget(self.body)
        self.v.addWidget(self.scroll)

        self.rebuild()

    def rebuild(self):
        # Clear
        while self.body_layout.count() > 1:
            item = self.body_layout.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()
        # Add a checkbox per layer
        for i, L in enumerate(self.renderer.layers):
            cb = QCheckBox(f"{i+1:02d}  {L.name}")
            cb.setChecked(L.visible)
            cb.toggled.connect(lambda state, idx=i: self.on_toggle(idx, state))
            self.body_layout.insertWidget(i, cb)

    def on_toggle(self, idx: int, state: bool):
        if 0 <= idx < len(self.renderer.layers):
            self.renderer.layers[idx].visible = state

    def on_add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add DXF Files", str(Path("DXF").resolve()), "DXF Files (*.dxf)")
        if not paths: return
        # Cycle simple colors for visibility
        palette = [(255,255,255),(0,0,255),(0,255,0),(255,0,0),(0,255,255),(255,255,0),(255,0,255),(128,128,128)]
        for i, p in enumerate(paths):
            color = palette[(len(self.renderer.layers) + i) % len(palette)]
            try:
                self.renderer.layers.append(load_layer(p, color))
            except Exception as ex:
                print(f"Failed to load {p}: {ex}")
        self.renderer._update_bbox()
        self.rebuild()

class MainWindow(QMainWindow):
    def __init__(self, renderer: DXFRenderer):
        super().__init__()
        self.setWindowTitle("DXF Viewer (Qt + OpenCV)")
        self.view = ImageView(renderer)
        self.setCentralWidget(self.view)

        # Layers dock
        self.panel = LayerPanel(self, renderer)
        dock = QDockWidget("Layers", self); dock.setWidget(self.panel); dock.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Menu actions
        add_act = QAction("&Add DXF…", self); add_act.triggered.connect(self.panel.on_add)
        fit_act = QAction("&Fit", self); fit_act.setShortcut("F"); fit_act.triggered.connect(lambda: (renderer._update_bbox(), renderer.fit()))
        self.menuBar().addMenu("&File").addAction(add_act)
        self.menuBar().addMenu("&View").addAction(fit_act)

        # Render timer (about 60 FPS, adjust if you like)
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick); self.timer.start(16)

    def _tick(self):
        # Render via OpenCV then push to QLabel as QPixmap
        frame = self.view.renderer.draw()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888)
        self.view.setPixmap(QPixmap.fromImage(qimg))

def list_dxf_files(start_dir: str) -> List[str]:
    base = Path(start_dir).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    return [str(p) for p in sorted(base.glob("**/*.dxf"))]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dxf", nargs="*", help="DXF files to open (optional)")
    parser.add_argument("--dxf-dir", default="DXF", help="Default DXF folder for the file dialog")
    #parser.add_argument("--w", type=int, default=1280); parser.add_argument("--h", type=int, default=800)
    parser.add_argument("--w", type=int, default=500); parser.add_argument("--h", type=int, default=1000)
    args = parser.parse_args()

    files = args.dxf or list_dxf_files(args.dxf_dir)[:1]  # open the first found if none given
    layers = []
    palette = [(255,255,255),(0,0,255),(0,255,0),(255,0,0),(0,255,255),(255,255,0),(255,0,255),(128,128,128)]
    for i, p in enumerate(files):
        try: layers.append(load_layer(p, palette[i % len(palette)]))
        except Exception as ex: print(f"Failed to load {p}: {ex}")
    if not layers:
        print(f"No DXF files found in {args.dxf_dir}. Use the Add DXF… button to load.")
        # Start with an empty renderer so UI still opens
    renderer = DXFRenderer(layers, args.w, args.h)

    app = QApplication([])
    win = MainWindow(renderer)
    win.resize(args.w+320, args.h+120)
    win.show()
    app.exec()

if __name__ == "__main__":
    main()
