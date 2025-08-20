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

#!/usr/bin/env python3
import math, argparse, os, csv
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import ezdxf
from ezdxf.colors import int2rgb
from ezdxf.addons import Importer  # NEW
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QScrollArea, QCheckBox, QFileDialog, QDockWidget,
    QMessageBox,
)

# --------- Simple renderer pieces (trimmed to essentials) ----------
BG_COLOR = (0,0,0)
FG_COLOR = (255,255,255)
LINE_THICKNESS = 1
POINT_RADIUS = 2
ARC_SEGMENTS = 180
SPLINE_SAMPLES = 300
MARGIN_PX = 20

# Simple color palette to cycle for added layers
PALETTE = [
    (255,255,255),(0,0,255),(0,255,0),(255,0,0),
    (0,255,255),(255,255,0),(255,0,255),(128,128,128),
]

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
                # quick bound (conservative)
                up(cx-a, cy-a); up(cx+a, cy+a)
                up(cx-b, cy-b); up(cx+b, cy+b)
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
    # FIXED: pass color (was mistakenly passing boolean from `color==None`)
    return DXFLayer(path, doc, doc.modelspace(), color==None , True)

class DXFRenderer:
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
                        # CCW unwrap to avoid wrong-direction arcs
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

        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.on_export_csv)

        import_btn = QPushButton("Import CSV")
        import_btn.clicked.connect(self.on_import_csv)

        export_dxf_btn = QPushButton("Export DXF")        # NEW
        export_dxf_btn.clicked.connect(self.on_export_dxf)  # NEW

        # for w in (add_btn, fit_btn, export_btn, import_btn):
        #     top.addWidget(w)

        for w in (add_btn, fit_btn, export_btn, import_btn, export_dxf_btn):  # UPDATED
            top.addWidget(w)
        
        top.addStretch(1)
        self.v.addLayout(top)

        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.body = QWidget(); self.body_layout = QVBoxLayout(self.body); self.body_layout.addStretch(1)
        self.scroll.setWidget(self.body)
        self.v.addWidget(self.scroll)

        self.rebuild()

    def rebuild(self):
        # Clear all items except the trailing stretch
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
        for i, p in enumerate(paths):
            color = PALETTE[(len(self.renderer.layers) + i) % len(PALETTE)]
            try:
                self.renderer.layers.append(load_layer(p, color))
            except Exception as ex:
                print(f"Failed to load {p}: {ex}")
        self.renderer._update_bbox()
        self.rebuild()

    # ----- NEW: Export visible layer list to CSV -----
    def on_export_csv(self):
        visible_paths = [str(Path(L.path).resolve()) for L in self.renderer.layers if L.visible]
        if not visible_paths:
            QMessageBox.information(self, "Export CSV", "No visible layers to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Visible Layers to CSV",
            str(Path.cwd() / "visible_layers.csv"),
            "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["path"])
                for p in visible_paths:
                    writer.writerow([p])
            QMessageBox.information(self, "Export CSV", f"Exported {len(visible_paths)} paths:\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Export CSV", f"Failed to export:\n{ex}")

    # ----- NEW: Import layer list from CSV (replaces current stack) -----
    # def on_import_csv(self):
    #     path, _ = QFileDialog.getOpenFileName(
    #         self,
    #         "Import Visible Layers CSV",
    #         str(Path.cwd()),
    #         "CSV Files (*.csv)"
    #     )
    #     if not path:
    #         return
    #     try:
    #         imported_paths: List[str] = []

    #         with open(path, "r", newline="") as f:
    #             reader = csv.reader(f)
    #             rows = list(reader)

    #         if not rows:
    #             QMessageBox.warning(self, "Import CSV", "CSV is empty.")
    #             return

    #         # Accept either headered (path) or single-column paths
    #         if len(rows[0]) == 1 and rows[0][0].strip().lower() == "path":
    #             data_rows = rows[1:]
    #         else:
    #             data_rows = rows

    #         for r in data_rows:
    #             if not r: continue
    #             p = r[0].strip()
    #             if p:
    #                 imported_paths.append(p)

    #         if not imported_paths:
    #             QMessageBox.warning(self, "Import CSV", "No paths found in CSV.")
    #             return

    #         resp = QMessageBox.question(
    #             self, "Import CSV",
    #             f"Load {len(imported_paths)} file(s) from CSV and REPLACE current layers?",
    #             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
    #         )
    #         if resp != QMessageBox.Yes:
    #             return

    #         new_layers: List[DXFLayer] = []
    #         failures: List[str] = []
    #         for i, p in enumerate(imported_paths):
    #             try:
    #                 color = PALETTE[(len(new_layers)) % len(PALETTE)]
    #                 new_layers.append(load_layer(p, color))
    #             except Exception as ex:
    #                 failures.append(f"{p}  ({ex})")

    #         self.renderer.layers[:] = new_layers
    #         self.renderer._update_bbox()
    #         self.renderer.fit()
    #         self.rebuild()

    #         msg = f"Loaded {len(new_layers)} layer(s)."
    #         if failures:
    #             msg += f"\nFailed ({len(failures)}):\n" + "\n".join(failures[:10])
    #             if len(failures) > 10:
    #                 msg += f"\n… and {len(failures)-10} more."
    #         QMessageBox.information(self, "Import CSV", msg)

    #     except Exception as ex:
    #         QMessageBox.critical(self, "Import CSV", f"Failed to import:\n{ex}")

    def on_import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Visible Layers CSV",
            str(Path.cwd()),
            "CSV Files (*.csv)"
        )
        if not path:
            return

        try:
            # --- read CSV (accepts single-column with or without header 'path') ---
            with open(path, "r", newline="") as f:
                rows = [r for r in csv.reader(f)]

            if not rows:
                QMessageBox.warning(self, "Import CSV", "CSV is empty.")
                return

            if len(rows[0]) == 1 and rows[0][0].strip().lower() == "path":
                rows = rows[1:]  # drop header

            imported_paths: List[str] = []
            for r in rows:
                if not r:
                    continue
                p = r[0].strip()
                if p:
                    imported_paths.append(str(Path(p).expanduser().resolve()))

            if not imported_paths:
                QMessageBox.warning(self, "Import CSV", "No paths found in CSV.")
                return

            # --- append (no replacement) with dedup by absolute path ---
            existing = {str(Path(L.path).resolve()) for L in self.renderer.layers}
            added = 0
            skipped: List[str] = []
            failures: List[str] = []

            for p in imported_paths:
                if p in existing:
                    skipped.append(p)
                    continue
                try:
                    # Use native DXF colors (no override). If you want per-file colors,
                    # pass a color: load_layer(p, PALETTE[(len(self.renderer.layers)) % len(PALETTE)])
                    self.renderer.layers.append(load_layer(p))
                    existing.add(p)
                    added += 1
                except Exception as ex:
                    failures.append(f"{p}  ({ex})")

            # Update view; keep current zoom/pan (no auto-fit)
            self.renderer._update_bbox()
            self.rebuild()

            # Summary
            msg = f"Added {added} layer(s)."
            if skipped:
                msg += f"\nSkipped duplicates: {len(skipped)}"
            if failures:
                msg += f"\nFailed ({len(failures)}):\n" + "\n".join(failures[:10])
                if len(failures) > 10:
                    msg += f"\n… and {len(failures)-10} more."
            QMessageBox.information(self, "Import CSV", msg)

        except Exception as ex:
            QMessageBox.critical(self, "Import CSV", f"Failed to import:\n{ex}")

    # Export DXF file of visible layers
    def on_export_dxf(self):
        # Collect visible source documents
        visible_layers = [L for L in self.renderer.layers if L.visible]
        if not visible_layers:
            QMessageBox.information(self, "Export DXF", "No visible layers to export.")
            return

        # Ask where to save
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Combined DXF",
            str(Path.cwd() / "combined.dxf"),
            "DXF Files (*.dxf)"
        )
        if not out_path:
            return

        try:
            # Create a fresh DXF (R2018 is a good default; change if you need older)
            out_doc = ezdxf.new(dxfversion="R2018", setup=True)
            out_msp = out_doc.modelspace()

            # Import each visible file into the output
            imported_from = 0
            for L in visible_layers:
                src_doc = L.doc
                src_msp = src_doc.modelspace()

                # Importer moves entities + required table resources (layers, linetypes, blocks, etc.)
                imp = Importer(src_doc, out_doc)
                imp.import_entities(list(src_msp), out_msp)
                imp.finalize()
                imported_from += 1

            # Save
            out_doc.saveas(out_path)
            QMessageBox.information(
                self, "Export DXF",
                f"Exported entities from {imported_from} visible file(s) into:\n{out_path}\n\n"
                "Notes:\n"
                "• Original layer names and colors are preserved.\n"
                "• If multiple inputs define the SAME layer name with different properties, "
                "  the first imported definition is kept for that name."
            )

        except Exception as ex:
            QMessageBox.critical(self, "Export DXF", f"Failed to export:\n{ex}")


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

        # Menus
        file_menu = self.menuBar().addMenu("&File")
        add_act = QAction("&Add DXF…", self); add_act.triggered.connect(self.panel.on_add)
        import_act = QAction("&Import CSV…", self); import_act.triggered.connect(self.panel.on_import_csv)
        export_act = QAction("E&xport CSV…", self); export_act.triggered.connect(self.panel.on_export_csv)

        export_dxf_act = QAction("Export &DXF…", self)              # NEW
        export_dxf_act.triggered.connect(self.panel.on_export_dxf)  # NEW

        # file_menu.addActions([add_act, import_act, export_act])
        file_menu.addActions([add_act, import_act, export_act, export_dxf_act])  # UPDATED

        view_menu = self.menuBar().addMenu("&View")
        fit_act = QAction("&Fit", self); fit_act.setShortcut("F"); fit_act.triggered.connect(lambda: (renderer._update_bbox(), renderer.fit()))
        view_menu.addAction(fit_act)

        # Render timer (~60 FPS)
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
    parser.add_argument("--w", type=int, default=500); parser.add_argument("--h", type=int, default=1000)
    args = parser.parse_args()

    files = args.dxf or list_dxf_files(args.dxf_dir)[:1]  # open the first found if none given
    layers = []
    for i, p in enumerate(files):
        try: layers.append(load_layer(p, PALETTE[i % len(PALETTE)]))
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
