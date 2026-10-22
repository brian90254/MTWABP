#!/usr/bin/env python3
"""Vellum-inspired 2D workflow prototype. Python 3 + tkinter; inches internally."""
import copy
import json
import math
from fractions import Fraction
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


def distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


def anchors(obj):
    if obj['type'] == 'line':
        a, b = obj['a'], obj['b']
        return [(a, 'endpoint'), (b, 'endpoint'),
                ([(a[0]+b[0])/2, (a[1]+b[1])/2], 'midpoint')]
    c, r = obj['center'], obj['radius']
    return [(c, 'center')] + [([c[0]+r*x, c[1]+r*y], 'quadrant')
                               for x, y in [(1,0), (0,1), (-1,0), (0,-1)]]


def hit_distance(p, obj):
    if obj['type'] == 'circle':
        return abs(distance(p, obj['center'])-obj['radius'])
    a, b = obj['a'], obj['b']
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy or 1)))
    return distance(p, [a[0]+t*dx, a[1]+t*dy])


def grid_values(spacing, subdivisions):
    """Validate dialog values; a subdivision is one division of a major interval."""
    try:
        spacing = float(Fraction(str(spacing).strip().rstrip('"').strip()))
        divisions = float(subdivisions)
    except (ValueError, TypeError, ZeroDivisionError, OverflowError):
        raise ValueError('Enter a positive spacing in inches and a whole subdivision count.')
    if not math.isfinite(spacing) or not 1e-6 <= spacing <= 1e7:
        raise ValueError('Grid spacing must be between 0.000001 and 10,000,000 inches.')
    if not math.isfinite(divisions) or not divisions.is_integer() or not 1 <= divisions <= 100:
        raise ValueError('Subdivisions must be a whole number from 1 to 100.')
    return spacing, int(divisions)


def grid_candidates(p, step):
    """Nearest intersection, vertical grid line, and horizontal grid line."""
    x, y = (round(v / step) * step for v in p)
    return [([x, y], 'grid intersection'), ([x, p[1]], 'vertical grid line'),
            ([p[0], y], 'horizontal grid line')]


def line_grid_candidates(p, obj, step):
    """Nearest segment/grid crossing in each grid direction, without enumeration.

    Project onto the infinite line first. Rounding its coordinate to a grid
    multiple, clamped to the segment's crossing range, gives the nearest
    crossing in that direction. This remains bounded even for very fine grids.
    """
    a, b = obj['a'], obj['b']
    d = [b[i]-a[i] for i in (0, 1)]
    length2 = sum(v*v for v in d)
    if length2 == 0:
        return []
    t = sum((p[i]-a[i])*d[i] for i in (0, 1)) / length2
    result = []
    for axis in (0, 1):
        if d[axis] == 0:
            continue
        low, high = sorted((a[axis]/step, b[axis]/step))
        first, last = math.ceil(low-1e-10), math.floor(high+1e-10)
        if first > last:
            continue
        k = max(first, min(last, round((a[axis]+t*d[axis])/step)))
        u = (k*step-a[axis])/d[axis]
        if -1e-10 <= u <= 1+1e-10:
            q = [a[i]+max(0, min(1, u))*d[i] for i in (0, 1)]
            q[axis] = k*step
            result.append((q, 'line/grid intersection'))
    return result


def alignment_candidates(p, start):
    dx, dy = p[0]-start[0], p[1]-start[1]
    plus, minus = (dx+dy)/2, (dx-dy)/2
    return [([p[0], start[1]], 'horizontal'),
            ([start[0], p[1]], 'vertical'),
            ([start[0]+plus, start[1]+plus], '45°'),
            ([start[0]+minus, start[1]-minus], '135°')]


def grid_positions(low, high, step, scale, min_pixels):
    """Cull dense lines for display only; snapping always uses the actual step."""
    if step*scale < min_pixels:
        return range(0)
    return range(math.ceil(low/step), math.floor(high/step)+1)


def validate(data):
    if not isinstance(data, dict) or data.get('format') != 'draft-prototype-1':
        raise ValueError('This is not a prototype drawing.')
    objects = data.get('objects')
    if not isinstance(objects, list) or len(objects) > 100000:
        raise ValueError('Invalid object list.')
    def number(v):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v)>1e9:
            raise ValueError('Invalid coordinate or radius.')
    def point(v):
        if not isinstance(v, list) or len(v) != 2: raise ValueError('Invalid point.')
        for n in v: number(n)
    for o in objects:
        if not isinstance(o, dict): raise ValueError('Invalid object.')
        if o.get('color') not in ['#202b36', '#2465d8', '#198548', '#c44236']:
            raise ValueError('Invalid pen color.')
        if o.get('type') == 'line':
            point(o.get('a')); point(o.get('b'))
        elif o.get('type') == 'circle':
            point(o.get('center')); number(o.get('radius'))
            if o['radius'] <= 0: raise ValueError('Radius must be positive.')
        else: raise ValueError('Unsupported object type.')
    return objects


class Draft:
    def __init__(self, root):
        self.root = root
        root.title('Draft — 2D workflow prototype')
        root.geometry('1180x780')
        self.objects = []
        self.history = []
        self.future = []
        self.selected = None
        self.start = None
        self.mouse = None
        self.marker = None
        self.scale = 90.0
        self.origin = [480., 330.]
        self.path = None
        self.saved = []
        self.pan = None
        self.tool = tk.StringVar(value='Select')
        self.color = tk.StringVar(value='#202b36')
        self.snap = tk.BooleanVar(value=True)
        self.grid = tk.BooleanVar(value=True)
        self.grid_snap = tk.BooleanVar(value=True)
        self.grid_spacing = 1.0
        self.grid_subdivisions = 4
        self.chain = tk.BooleanVar(value=False)
        self.status = tk.StringVar()
        self.fields = {}
        bar = ttk.Frame(root, padding=7); bar.pack(fill='x')
        for label, fn in [('New', self.new), ('Open', self.open), ('Save', self.save),
                          ('Undo', self.undo), ('Redo', self.redo), ('Fit', self.fit)]:
            ttk.Button(bar, text=label, command=fn).pack(side='left', padx=2)
        ttk.Label(bar, text='   Pen ').pack(side='left')
        for name, color in [('Black','#202b36'), ('Blue','#2465d8'), ('Green','#198548'), ('Red','#c44236')]:
            ttk.Radiobutton(bar, text=name, variable=self.color, value=color).pack(side='left')
        body = ttk.Frame(root); body.pack(fill='both', expand=True)
        side = ttk.Frame(body, padding=10, width=210); side.pack(side='left', fill='y')
        ttk.Label(side, text='DRAWING TOOLS', font=('',11,'bold')).pack(anchor='w', pady=8)
        for name in ['Select', 'Line', 'Circle', 'Move']:
            ttk.Radiobutton(side, text=name, variable=self.tool, value=name,
                            command=self.cancel).pack(anchor='w', pady=5)
        ttk.Checkbutton(side, text='Connected lines', variable=self.chain).pack(anchor='w', pady=6)
        ttk.Separator(side).pack(fill='x', pady=12)
        ttk.Checkbutton(side, text='Object snaps / alignment', variable=self.snap).pack(anchor='w')
        ttk.Checkbutton(side, text='Show grid', variable=self.grid, command=self.draw).pack(anchor='w', pady=6)
        ttk.Checkbutton(side, text='Snap to grid', variable=self.grid_snap).pack(anchor='w')
        ttk.Button(side, text='Grid preferences…', command=self.grid_dialog).pack(fill='x', pady=6)
        ttk.Label(side, text='EXACT ENTRY • INCHES', font=('',10,'bold')).pack(anchor='w', pady=(20,8))
        for key, label in [('x','X'), ('y','Y'), ('length','Length'), ('angle','Angle °'), ('diameter','Diameter')]:
            row = ttk.Frame(side); row.pack(fill='x', pady=3)
            ttk.Label(row, text=label, width=10).pack(side='left')
            v = tk.StringVar(value={'x':'0','y':'0','length':'2','angle':'0','diameter':'1'}[key])
            self.fields[key] = v
            ent = ttk.Entry(row, textvariable=v, width=11); ent.pack(side='left')
            ent.bind('<Return>', lambda e: self.exact())
        ttk.Button(side, text='Apply exact entry', command=self.exact).pack(fill='x', pady=12)
        ttk.Label(side, text='Line: X/Y is start; length + angle.\nCircle: X/Y is center; diameter.\nMove: X/Y is displacement.', wraplength=195).pack(anchor='w')
        ttk.Button(side, text='Load 2-inch line / 1-inch circle', command=self.demo).pack(fill='x', pady=(24,8))
        ttk.Label(side, text='Wheel: zoom\nMiddle drag: pan\nEsc: cancel\nDelete: remove selection\nCtrl+Z / Ctrl+Y: undo / redo\nCtrl+S: save', justify='left').pack(anchor='w', pady=10)
        self.canvas = tk.Canvas(body, bg='white', highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        ttk.Label(root, textvariable=self.status, padding=6).pack(fill='x')
        self.canvas.bind('<Configure>', lambda e: self.draw())
        self.canvas.bind('<Motion>', self.motion)
        self.canvas.bind('<Button-1>', self.click)
        self.canvas.bind('<ButtonPress-2>', self.pan_start)
        self.canvas.bind('<B2-Motion>', self.pan_move)
        self.canvas.bind('<MouseWheel>', lambda e: self.zoom(e, 1.15 if e.delta>0 else 1/1.15))
        self.canvas.bind('<Button-4>', lambda e: self.zoom(e, 1.15))
        self.canvas.bind('<Button-5>', lambda e: self.zoom(e, 1/1.15))
        root.bind('<Escape>', lambda e: self.cancel())
        self.canvas.bind('<Delete>', lambda e: self.delete())
        root.bind('<Control-z>', lambda e: self.undo())
        root.bind('<Control-y>', lambda e: self.redo())
        root.bind('<Control-s>', lambda e: self.save())
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.draw()

    def world(self, x, y):
        return [(x-self.origin[0])/self.scale, (self.origin[1]-y)/self.scale]

    def screen(self, p):
        return [self.origin[0]+p[0]*self.scale, self.origin[1]-p[1]*self.scale]

    def grid_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Grid')
        dialog.transient(self.root)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill='both', expand=True)
        spacing = tk.StringVar(value=f'{self.grid_spacing:g}')
        divisions = tk.StringVar(value=str(self.grid_subdivisions))
        ttk.Label(frame, text='Grid spacing (inches)').grid(row=0, column=0, sticky='w', padx=(0,16), pady=5)
        entry = ttk.Entry(frame, textvariable=spacing, width=14)
        entry.grid(row=0, column=1, pady=5)
        ttk.Label(frame, text='# of subdivisions').grid(row=1, column=0, sticky='w', pady=5)
        ttk.Entry(frame, textvariable=divisions, width=14).grid(row=1, column=1, pady=5)
        def apply():
            try:
                major, count = grid_values(spacing.get(), divisions.get())
            except ValueError as ex:
                messagebox.showerror('Grid preferences', str(ex), parent=dialog)
                return
            self.grid_spacing, self.grid_subdivisions = major, count
            self.mouse = None; self.marker = None
            dialog.destroy()
            self.draw()
        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, columnspan=2, sticky='e', pady=(12,0))
        ttk.Button(buttons, text='Cancel', command=dialog.destroy).pack(side='left', padx=5)
        ttk.Button(buttons, text='OK', command=apply).pack(side='left')
        dialog.bind('<Return>', lambda e: apply())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
        dialog.grab_set()
        entry.focus_set(); entry.selection_range(0, 'end')

    def snap_point(self, p):
        # Ordered tiers: object anchors, line/grid crossings, grid intersections,
        # angular alignment, then grid lines. Each must be within 9 pixels.
        tolerance = 9 / self.scale
        def nearest(candidates):
            best = min(candidates, key=lambda a: distance(p, a[0]), default=None)
            if best is not None and distance(p, best[0]) <= tolerance:
                return list(best[0]), best[1]
            return None
        if self.snap.get():
            candidates = [([0,0], 'origin')]
            for i, o in enumerate(self.objects):
                if self.tool.get() == 'Move' and i == self.selected:
                    continue
                candidates.extend(anchors(o))
            best = nearest(candidates)
            if best: return best
        grid = None
        if self.grid_snap.get():
            step = self.grid_spacing / self.grid_subdivisions
            crossings = []
            for i, o in enumerate(self.objects):
                if o['type'] == 'line' and not (self.tool.get() == 'Move' and i == self.selected):
                    crossings.extend(line_grid_candidates(p, o, step))
            best = nearest(crossings)
            if best: return best
            grid = grid_candidates(p, step)
            best = nearest(grid[:1])
            if best: return best
        if self.snap.get() and self.start is not None and self.tool.get() in ['Line','Move']:
            best = nearest(alignment_candidates(p, self.start))
            if best: return best
        if grid:
            best = nearest(grid[1:])
            if best: return best
        return p, ''

    def motion(self, e):
        self.mouse, self.marker = self.snap_point(self.world(e.x,e.y))
        self.draw()

    def checkpoint(self):
        self.history.append(copy.deepcopy(self.objects)); self.future.clear()

    def cancel(self):
        self.start = None; self.mouse = None; self.marker = None; self.draw()

    def add(self, obj):
        self.checkpoint(); self.objects.append(obj); self.selected = len(self.objects)-1
        self.draw()

    def click(self, e):
        self.canvas.focus_set()
        p, _ = self.snap_point(self.world(e.x,e.y))
        tool = self.tool.get()
        if tool == 'Select':
            raw = self.world(e.x,e.y)
            hits = [(hit_distance(raw,o),i) for i,o in enumerate(self.objects)]
            best = min(hits, default=(float('inf'),None))
            self.selected = best[1] if best[0]*self.scale <= 9 else None
        elif tool == 'Move' and self.selected is None:
            messagebox.showinfo('Move', 'Select an object with the Select tool first.'); return
        elif self.start is None:
            self.start = p
        elif tool == 'Line':
            if distance(self.start,p)>1e-10:
                self.add({'type':'line','a':self.start[:],'b':p,'color':self.color.get()})
                self.start = p if self.chain.get() else None
        elif tool == 'Circle':
            r = distance(self.start,p)
            if r>1e-10:
                self.add({'type':'circle','center':self.start[:],'radius':r,'color':self.color.get()}); self.start=None
        elif tool == 'Move':
            self.move(p[0]-self.start[0], p[1]-self.start[1]); self.start=None
        self.draw()

    def move(self, dx, dy):
        if self.selected is None: raise ValueError('Select an object first.')
        self.checkpoint()
        o = self.objects[self.selected]
        for k in (['a','b'] if o['type']=='line' else ['center']):
            o[k] = [o[k][0]+dx,o[k][1]+dy]
        self.draw()

    def exact(self):
        try:
            tool = self.tool.get()
            keys = ['x','y'] + (['length','angle'] if tool=='Line' else ['diameter'] if tool=='Circle' else [])
            v = {k:float(self.fields[k].get()) for k in keys}
            if any(not math.isfinite(n) or abs(n)>1e7 for n in v.values()): raise ValueError('Enter finite values within ±10,000,000.')
            p=[v['x'],v['y']]
            if tool=='Line':
                if v['length']<=0: raise ValueError('Length must be positive.')
                a=math.radians(v['angle'])
                self.add({'type':'line','a':p,'b':[p[0]+v['length']*math.cos(a),p[1]+v['length']*math.sin(a)],'color':self.color.get()})
            elif tool=='Circle':
                if v['diameter']<=0: raise ValueError('Diameter must be positive.')
                self.add({'type':'circle','center':p,'radius':v['diameter']/2,'color':self.color.get()})
            elif tool=='Move': self.move(*p)
            else: raise ValueError('Choose Line, Circle, or Move for exact entry.')
            self.cancel()
        except ValueError as ex: messagebox.showerror('Exact entry', str(ex))

    def draw_object(self, o, color=None, dash=None):
        opts={'fill':color or o['color'],'width':2}
        if dash: opts['dash']=dash
        if o['type']=='line': self.canvas.create_line(*self.screen(o['a']),*self.screen(o['b']),**opts)
        else:
            x,y=self.screen(o['center']); r=o['radius']*self.scale
            opts['outline']=opts.pop('fill'); opts['fill']=''
            self.canvas.create_oval(x-r,y-r,x+r,y+r,**opts)

    def draw(self):
        c=self.canvas; c.delete('all'); w=c.winfo_width(); h=c.winfo_height()
        step = self.grid_spacing / self.grid_subdivisions
        major_visible = self.grid_spacing*self.scale >= 8
        minor_visible = self.grid_subdivisions > 1 and step*self.scale >= 8
        if self.grid.get():
            lo=self.world(0,h); hi=self.world(w,0)
            for axis in [0,1]:
                for spacing, major in [(step, False), (self.grid_spacing, True)]:
                    if not major and not minor_visible:
                        continue
                    for i in grid_positions(lo[axis], hi[axis], spacing, self.scale, 8):
                        if not major and i % self.grid_subdivisions == 0:
                            continue
                        q=self.screen([i*spacing,0] if axis==0 else [0,i*spacing])
                        coords=(q[0],0,q[0],h) if axis==0 else (0,q[1],w,q[1])
                        c.create_line(*coords, fill='#bcc8d5' if major else '#e4e9ef',
                                      dash=(2,3) if major else (1,4))
        x,y=self.origin
        c.create_line(0,y,w,y,fill='#cbd2db'); c.create_line(x,0,x,h,fill='#cbd2db')
        c.create_text(x+12,y+12,text='0,0',anchor='nw',fill='#8b929a')
        for i,o in enumerate(self.objects):
            self.draw_object(o)
            if i==self.selected:
                for p,_ in anchors(o):
                    a,b=self.screen(p); c.create_rectangle(a-3,b-3,a+3,b+3,outline='#e69d20',fill='#fff2c9')
        if self.start is not None and self.mouse is not None:
            if self.tool.get()=='Line': self.draw_object({'type':'line','a':self.start,'b':self.mouse,'color':'#708296'},dash=(5,3))
            elif self.tool.get()=='Circle': self.draw_object({'type':'circle','center':self.start,'radius':distance(self.start,self.mouse),'color':'#708296'},dash=(5,3))
            a,b=self.screen(self.start)
            c.create_line(0,b,w,b,fill='#b8cddd',dash=(3,5)); c.create_line(a,0,a,h,fill='#b8cddd',dash=(3,5))
            if self.tool.get() in ['Line', 'Move'] and self.marker in ['45°', '135°']:
                slope = -1 if self.marker == '45°' else 1
                c.create_line(0,b-slope*a,w,b+slope*(w-a),fill='#9dbcd5',dash=(3,5))
        if self.mouse is not None and self.marker:
            a,b=self.screen(self.mouse)
            c.create_rectangle(a-5,b-5,a+5,b+5,outline='#bf7300',width=2)
            c.create_text(a+12,b-14,text=self.marker,anchor='w',fill='#9a5b00')
        info = 'Select an object' if self.tool.get()=='Select' else 'Choose first point' if self.start is None else 'Choose second point'
        pos = '' if self.mouse is None else f'   X {self.mouse[0]:.4f}   Y {self.mouse[1]:.4f}'
        hidden = ' (dense lines hidden)' if self.grid.get() and (not major_visible or (self.grid_subdivisions > 1 and not minor_visible)) else ''
        self.status.set(f'{self.tool.get()} • {info}   |   {len(self.objects)} objects   |   inches   |   grid {self.grid_spacing:g} in / {self.grid_subdivisions} = {step:g} in{hidden}{pos}')
        self.root.title(('• ' if self.objects!=self.saved else '')+'Draft — 2D workflow prototype')

    def delete(self):
        if self.selected is not None:
            self.checkpoint(); del self.objects[self.selected]; self.selected=None; self.cancel()

    def undo(self):
        if self.history:
            self.future.append(copy.deepcopy(self.objects)); self.objects=self.history.pop(); self.selected=None; self.cancel()

    def redo(self):
        if self.future:
            self.history.append(copy.deepcopy(self.objects)); self.objects=self.future.pop(); self.selected=None; self.cancel()

    def zoom(self,e,factor):
        p=self.world(e.x,e.y); self.scale=max(.01,min(100000,self.scale*factor))
        self.origin=[e.x-p[0]*self.scale,e.y+p[1]*self.scale]; self.draw()

    def pan_start(self,e): self.pan=[e.x,e.y]

    def pan_move(self,e):
        if self.pan:
            self.origin[0]+=e.x-self.pan[0]; self.origin[1]+=e.y-self.pan[1]
            self.pan=[e.x,e.y]; self.draw()

    def fit(self):
        pts=[p for o in self.objects for p,_ in anchors(o)]
        if not pts: return
        x0=min(p[0] for p in pts); x1=max(p[0] for p in pts)
        y0=min(p[1] for p in pts); y1=max(p[1] for p in pts)
        w=max(100,self.canvas.winfo_width()); h=max(100,self.canvas.winfo_height())
        self.scale=min((w-80)/max(x1-x0,.5),(h-80)/max(y1-y0,.5))
        self.origin=[w/2-(x0+x1)*self.scale/2,h/2+(y0+y1)*self.scale/2]; self.draw()

    def discard(self):
        return self.objects==self.saved or messagebox.askyesno('Unsaved drawing','Discard unsaved changes?')

    def new(self):
        if self.discard():
            self.objects=[]; self.saved=[]; self.history=[]; self.future=[]; self.path=None; self.selected=None; self.cancel()

    def demo(self):
        if not self.discard(): return
        self.checkpoint()
        self.objects=[{'type':'line','a':[-1,0],'b':[1,0],'color':'#198548'},
                      {'type':'circle','center':[0,0],'radius':.5,'color':'#2465d8'}]
        self.path=None; self.selected=None; self.cancel(); self.fit()

    def save(self):
        path=self.path or filedialog.asksaveasfilename(defaultextension='.draft.json',filetypes=[('Draft drawing','*.json')])
        if not path: return
        try:
            with open(path,'w',encoding='utf-8') as f: json.dump({'format':'draft-prototype-1','units':'inches','objects':self.objects},f,indent=2)
            self.path=path; self.saved=copy.deepcopy(self.objects); self.draw()
        except OSError as ex: messagebox.showerror('Save',str(ex))

    def open(self):
        if not self.discard(): return
        path=filedialog.askopenfilename(filetypes=[('Draft drawing','*.json')])
        if not path: return
        try:
            with open(path,encoding='utf-8') as f: objects=validate(json.load(f))
            self.objects=objects; self.saved=copy.deepcopy(objects); self.path=path
            self.history=[]; self.future=[]; self.selected=None; self.cancel(); self.fit()
        except (OSError,ValueError,TypeError) as ex: messagebox.showerror('Open',str(ex))

    def close(self):
        if self.discard(): self.root.destroy()


if __name__=='__main__':
    root=tk.Tk(); Draft(root); root.mainloop()
