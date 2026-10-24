#!/usr/bin/env python3
"""BrianCAD: a Vellum-inspired 2D desktop drafting application."""
import copy
import json
import math
import os
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, font as tkfont
import cad_geometry as geo
import cad_selection as selection
import cad_trim
from snap_tracking import SnapHistory
from cad_geometry import dist as distance, anchors, hit_distance
from cad_document import Document, COLORS
from cad_tools import METHODS, THREE, DEFAULTS, LABELS, fields_for, point_values, construct
from grid_snap import grid_values, grid_positions, grid_candidates, line_grid_candidates, alignment_candidates


SNAP_HOVER_MS=600
GRID_COLOR='#bcc8d5'
SNAP_LABEL_COLOR='#626a73'

def validate(data):
    """Compatibility entry point for the first prototype's object-only validator."""
    return Document.from_payload(data).objects


class Draft:
    def __init__(self,root):
        self.root=root; self.doc=Document(); self.path=None
        self.scale=90.; self.origin=[470.,320.]; self.pan=None
        self.points=[]; self.refs=[]; self.start=None; self.mouse=None; self.marker=''
        self.snap_history=SnapHistory(); self.tracking_cursor=None; self.pointer_position=None
        self._snap_hover_job=None; self._snap_hover_state=None; self._snap_label_visible=False
        self.snap_label_font=tkfont.nametofont('TkDefaultFont').copy()
        font_size=self.snap_label_font.cget('size')
        self.snap_label_font.configure(size=max(8,font_size-1) if font_size>0 else min(-8,font_size+2))
        self.family=tk.StringVar(value='Select'); self.tool=tk.StringVar(value='Select')
        self.color=tk.StringVar(value=COLORS['Black']); self.snap=tk.BooleanVar(value=True)
        self.grid=tk.BooleanVar(value=True); self.grid_snap=tk.BooleanVar(value=True)
        self.clockwise=tk.BooleanVar(value=False); self.copy_mode=tk.BooleanVar(value=False)
        self.status=tk.StringVar(); self.layer_status=tk.StringVar(); self.params={}; self.last_parameter=None
        self.layer_window=None; self.edit_window=None; self.box_start=None; self.box_end=None
        self.drag=None; self.drag_preview={}; self.drag_error=''; self._bounds_cache={}
        root.title('BrianCAD'); root.geometry('1220x820'); root.minsize(850,620)
        self.build_ui(); self.configure_parameters()
        root.protocol('WM_DELETE_WINDOW',self.close)
        for key,action in [('z',self.undo),('y',self.redo),('s',self.save),('o',self.open)]:
            root.bind('<Control-'+key+'>',lambda e,f=action:self.shortcut(e,f))
            if root.tk.call('tk','windowingsystem')=='aqua':
                root.bind('<Command-'+key+'>',lambda e,f=action:self.shortcut(e,f))
        root.bind('<Escape>',lambda e:self.return_to_select() if self.family.get()=='Trim' else self.cancel())
        self.draw()

    @property
    def objects(self): return self.doc.objects
    @objects.setter
    def objects(self,v): self.doc.objects=v
    @property
    def selected(self): return self.doc.selected
    @selected.setter
    def selected(self,v):
        self.doc.selected=set() if v is None else {v} if isinstance(v,int) else set(v)
        self.doc.point_selection={}
    @property
    def grid_spacing(self): return self.doc.grid_spacing
    @grid_spacing.setter
    def grid_spacing(self,v): self.doc.grid_spacing=v
    @property
    def grid_subdivisions(self): return self.doc.grid_subdivisions
    @grid_subdivisions.setter
    def grid_subdivisions(self,v): self.doc.grid_subdivisions=v

    def build_ui(self):
        bar=ttk.Frame(self.root,padding=6); bar.pack(fill='x')
        for label,fn in [('New',self.new),('Open',self.open),('Save',self.save),('Save as',lambda:self.save(True)),
                         ('Undo',self.undo),('Redo',self.redo),('Fit',self.fit),('Layers...',self.layers_dialog),('Edit objects...',self.edit_dialog)]:
            ttk.Button(bar,text=label,command=fn).pack(side='left',padx=2)
        ttk.Label(self.root,textvariable=self.status,padding=5).pack(side='bottom',fill='x')
        self.parameter_frame=ttk.LabelFrame(self.root,text='Drawing parameters  |  inches',padding=6)
        self.parameter_frame.pack(side='bottom',fill='x')
        body=ttk.Frame(self.root); body.pack(fill='both',expand=True)
        side=ttk.Frame(body,padding=10,width=215); side.pack(side='left',fill='y')
        ttk.Label(side,text='TOOLS',font=('',11,'bold')).pack(anchor='w',pady=(0,6))
        families=ttk.Frame(side); families.pack(fill='x')
        # Small arrow with a distinct shaft; keep the image alive with the app.
        self.select_icon=tk.PhotoImage(master=self.root,width=18,height=20)
        rows=['#','##','###','####','#####','######','#######','########',
              '#########','##########','######','##  ###','#   ###','     ###','     ###','      ##']
        for y,row in enumerate(rows,2):
            for x,pixel in enumerate(row,2):
                if pixel=='#': self.select_icon.put('#202b36',to=(x,y))
        for i,family in enumerate(METHODS):
            opts={'image':self.select_icon,'compound':'left'} if family=='Select' else {}
            ttk.Radiobutton(families,**opts,text=family,variable=self.family,value=family,command=self.family_changed).grid(row=i//2,column=i%2,sticky='w',pady=3,padx=(0,8))
        ttk.Label(side,text='Construction method').pack(anchor='w',pady=(14,3))
        self.method_box=ttk.Combobox(side,textvariable=self.tool,values=METHODS['Select'],state='readonly',width=25)
        self.method_box.pack(fill='x'); self.method_box.bind('<<ComboboxSelected>>',lambda e:self.method_changed())
        self.direction_check=ttk.Checkbutton(side,text='Clockwise center arc',variable=self.clockwise)
        self.direction_check.pack(anchor='w',pady=(8,2))
        ttk.Checkbutton(side,text='Copy when transforming',variable=self.copy_mode).pack(anchor='w')
        ttk.Separator(side).pack(fill='x',pady=12)
        pens=ttk.Frame(side); pens.pack(fill='x')
        for i,(name,color) in enumerate(COLORS.items()):
            ttk.Radiobutton(pens,text=name,variable=self.color,value=color).grid(row=i//2,column=i%2,sticky='w',padx=(0,14))
        ttk.Separator(side).pack(fill='x',pady=10)
        ttk.Checkbutton(side,text='Object snaps / alignment',variable=self.snap).pack(anchor='w')
        ttk.Checkbutton(side,text='Show grid',variable=self.grid,command=self.draw).pack(anchor='w',pady=3)
        ttk.Checkbutton(side,text='Snap to grid',variable=self.grid_snap).pack(anchor='w')
        ttk.Button(side,text='Grid preferences...',command=self.grid_dialog).pack(fill='x',pady=8)
        ttk.Label(side,textvariable=self.layer_status,wraplength=200).pack(anchor='w',pady=6)
        ttk.Label(side,text='Shift-click: add/remove\nDrag blank: window selection\nDrag selection: move\nDouble-click: edit\nWheel: zoom; middle drag: pan\nEsc: cancel; Delete: objects\nRight-click: Select\nSpline: right-click/Enter finishes',wraplength=205).pack(anchor='w',pady=8)
        self.canvas=tk.Canvas(body,bg='white',highlightthickness=0,cursor='none')
        self.canvas.pack(fill='both',expand=True)
        aqua=self.root.tk.call('tk','windowingsystem')=='aqua'
        # Tk 8.6 Aqua swaps middle/right; Tk 8.7+ uses the standard mapping.
        legacy_aqua=aqua and int(self.root.tk.call('package','vcompare',
            self.root.tk.call('package','provide','Tk'),'8.7a0'))<0
        middle_button=3 if legacy_aqua else 2
        right_button=2 if legacy_aqua else 3
        self.root.bind(f'<Button-{right_button}>',self.right_click)
        if aqua:
            self.canvas.bind('<Control-Button-1>',self.right_click)
            self.root.bind('<Control-Button-1>',self.right_click)
        for event,fn in [('<Configure>',lambda e:self.draw()),('<Motion>',self.motion),('<Enter>',self.motion),
                         ('<ButtonPress-1>',self.click),('<B1-Motion>',self.drag_select),
                         ('<ButtonRelease-1>',self.release_select),('<Double-Button-1>',self.double_click),
                         (f'<ButtonPress-{middle_button}>',self.pan_start),(f'<B{middle_button}-Motion>',self.pan_move),
                         ('<Delete>',lambda e:self.delete()),('<BackSpace>',lambda e:self.delete()),
                         ('<Return>',lambda e:self.finish())]:
            self.canvas.bind(event,fn)
        self.canvas.bind('<Leave>',self.leave_canvas)
        self.canvas.bind('<Destroy>',lambda e:self.cancel_snap_hover())
        self.canvas.bind('<MouseWheel>',lambda e:self.zoom(e,1.15 if e.delta>0 else 1/1.15))
        if self.root.tk.call('tk','windowingsystem')!='aqua':
            self.canvas.bind('<Button-4>',lambda e:self.zoom(e,1.15))
            self.canvas.bind('<Button-5>',lambda e:self.zoom(e,1/1.15))

    def shortcut(self,event,fn):
        if event.widget.winfo_class() in ['Entry','TEntry','Text','TCombobox'] and fn in [self.undo,self.redo]: return
        fn(); return 'break'

    def right_click(self,event=None):
        if self.family.get()=='Splines' and self.points:
            self.finish()
            return 'break'
        return self.return_to_select(event)

    def return_to_select(self,event=None):
        self.pan=None
        self.family.set('Select'); self.family_changed()
        self.canvas.focus_set()
        return 'break'

    def family_changed(self):
        self.tool.set(METHODS[self.family.get()][0]); self.method_box.configure(values=METHODS[self.family.get()])
        self.method_changed()

    def method_changed(self):
        self.snap_history.clear()
        self.canvas.configure(cursor='none' if self.family.get()=='Select' else 'arrow')
        self.update_pointer()
        self.cancel()
        if self.family.get()=='Trim':
            ids=set(self.selected)|set(self.doc.point_selection)
            ids={i for i in ids if self.doc.visible(i) and self.objects[i]['type'] in cad_trim.BOUNDARIES}
            self.trim_cutters=[self.objects[i] for i in sorted(ids)]
            self.selected=ids; self.doc.point_selection={}
        self.configure_parameters()

    def configure_parameters(self):
        for child in self.parameter_frame.winfo_children(): child.destroy()
        self.params={}; self.last_parameter=None
        fields=fields_for(self.family.get(),self.tool.get())
        for i,key in enumerate(fields):
            row,col=divmod(i,4)
            cell=ttk.Frame(self.parameter_frame); cell.grid(row=row,column=col,sticky='w',padx=5,pady=3)
            label=LABELS[key]
            if self.family.get()=='Modify' and key in ['x','y']: label='Pivot '+key.upper() if self.tool.get()!='Move' else 'Ref '+key.upper()
            if self.family.get()=='Arcs' and self.tool.get()=='Center + start + end':
                label={'x':'Center X','y':'Center Y','x2':'Start X','y2':'Start Y','x3':'End X','y3':'End Y'}.get(key,label)
            elif self.family.get()=='Arcs' and self.tool.get()=='Start tangent + end':
                label={'x':'Start X','y':'Start Y','x2':'Tangent X','y2':'Tangent Y','x3':'End X','y3':'End Y'}.get(key,label)
            elif key in ('x','y') and (self.family.get() in ['Circles','Ovals'] or 'polygon' in self.tool.get()):
                label='Center '+key.upper() if self.tool.get() not in ['Diameter endpoints','Three-point circle','Two tangent lines','Opposite corners','Axis endpoints + width'] else key.upper()
            ttk.Label(cell,text=label,width=9).pack(side='left')
            var=tk.StringVar(value=f'{DEFAULTS.get(key,0):g}'); self.params[key]=var
            ent=ttk.Entry(cell,textvariable=var,width=10); ent.pack(side='left')
            ent.bind('<KeyRelease>',lambda e,k=key:self.parameter_changed(k))
            ent.bind('<Return>',lambda e:self.apply_parameters())
        actions=ttk.Frame(self.parameter_frame); actions.grid(row=(len(fields)+3)//4,column=0,columnspan=4,padx=5,pady=4,sticky='w')
        if fields:
            if self.family.get()!='Modify':
                ttk.Button(actions,text='Use entered point',command=self.enter_point).pack(side='left',padx=3)
            ttk.Button(actions,text='Apply / Create',command=self.apply_parameters).pack(side='left',padx=3)
        if self.family.get()=='Splines':
            ttk.Button(actions,text='Finish spline',command=self.finish).pack(side='left',padx=3)
        if not fields:
            hint='Select cutting boundaries before choosing Trim; click a section to remove. Right-click exits.' if self.family.get()=='Trim' else 'Select objects, then double-click to edit or choose a Modify method.'
            ttk.Label(self.parameter_frame,text=hint).grid(row=0,column=0,sticky='w')
        self.draw()

    def parameter_changed(self,key): self.last_parameter=key

    def values(self):
        vals={k:float(v.get()) for k,v in self.params.items()}
        if any(not math.isfinite(v) or abs(v)>1e7 for v in vals.values()): raise ValueError('Enter finite values within ±10,000,000.')
        return vals

    def field_point(self,index):
        values=self.values(); suffix=str(index+1) if index else ''
        return [values['x'+suffix],values['y'+suffix]]

    def set_point_fields(self,index,p):
        suffix=str(index+1) if index else ''
        for key,value in zip(['x'+suffix,'y'+suffix],p):
            if key in self.params: self.params[key].set(f'{value:.12g}')

    def update_line_fields(self,a,b):
        dx,dy=geo.sub(b,a)
        for k,v in [('dx',dx),('dy',dy),('length',math.hypot(dx,dy)),('angle',math.degrees(math.atan2(dy,dx)))]:
            if k in self.params: self.params[k].set(f'{v:.12g}')

    def world(self,x,y): return [(x-self.origin[0])/self.scale,(self.origin[1]-y)/self.scale]
    def screen(self,p): return [self.origin[0]+p[0]*self.scale,self.origin[1]-p[1]*self.scale]

    def object_bounds(self,o):
        if not hasattr(self,'_bounds_cache'): self._bounds_cache={}
        if len(self._bounds_cache)>2*len(self.objects)+32: self._bounds_cache.clear()
        cached=self._bounds_cache.get(id(o))
        if cached is None or cached[0] is not o:
            cached=(o,selection.bounds(o)); self._bounds_cache[id(o)]=cached
        return cached[1]

    def on_object(self,p,ids):
        candidates=[]; tolerance=9/self.scale
        for i in ids:
            o=self.objects[i]
            if selection.box_distance(p,self.object_bounds(o))>tolerance: continue
            q=selection.nearest_point(p,o)
            if distance(p,q)<=tolerance:
                candidates.append((q,'on line' if o['type']=='line' else 'on curve'))
        return min(candidates,key=lambda v:distance(p,v[0]),default=None)

    def tracking_exclusions(self,ids):
        history=getattr(self,'snap_history',None)
        if not history: return []
        objects=[self.objects[i] for i in ids]
        return [p for p in history.points if any(
            hit_distance(p,o)<1e-8 or any(distance(p,q)<1e-8 for q,_ in anchors(o))
            for o in objects)]

    def snap_point(self,p,exclude=None):
        tolerance=9/self.scale
        def nearest(candidates):
            best=min(candidates,key=lambda v:distance(p,v[0]),default=None)
            return (list(best[0]),best[1]) if best and distance(p,best[0])<=tolerance else None
        excluded=set(exclude or [])
        if self.family.get()=='Modify': excluded.update(self.selected)
        ids=[i for i in range(len(self.objects)) if self.doc.visible(i) and i not in excluded]
        if self.snap.get():
            if self.family.get()=='Lines' and self.tool.get() in ('Two points','Connected points') and self.points:
                try:
                    start=self.field_point(0)
                except (ValueError,KeyError,AttributeError):
                    start=None
                if start is not None:
                    tangents=[(q,'tangent') for i in ids
                              for q in geo.tangent_points(start,self.objects[i])]
                    best=nearest(tangents)
                    if best: return best
            candidates=[]
            for i in ids: candidates.extend(anchors(self.objects[i]))
            candidates.append(([0,0],'origin'))
            best=nearest(candidates)
            if best: return best
        history=getattr(self,'snap_history',None)
        if self.snap.get() and history:
            ignored=self.tracking_exclusions(excluded)
            step=self.grid_spacing/self.grid_subdivisions if self.grid_snap.get() else None
            nearby=[self.objects[i] for i in ids if selection.box_distance(p,self.object_bounds(self.objects[i]))<=tolerance]
            crossing=nearest(history.crossings(p,self.scale,nearby,step,ignored,self.object_bounds))
            if crossing: return crossing
            tracked=history.snap(p,self.scale,ignored)
            if tracked: return tracked
        grid=None
        if self.grid_snap.get():
            step=self.grid_spacing/self.grid_subdivisions
            crossings=[]
            for i in ids:
                if self.objects[i]['type']=='line': crossings.extend(line_grid_candidates(p,self.objects[i],step))
            best=nearest(crossings)
            if best: return best
            grid=grid_candidates(p,step); best=nearest(grid[:1])
            if best: return best
        if self.snap.get():
            best=self.on_object(p,ids)
            if best: return best
        if self.snap.get() and self.start is not None and (self.family.get() in ['Lines','Modify'] or getattr(self,'drag',None)):
            best=nearest(alignment_candidates(p,self.start))
            if best: return best
        if grid:
            best=nearest(grid[1:])
            if best: return best
        return p,''

    def hit(self,p,lines_only=False):
        hits=[]; tolerance=9/self.scale
        for i,o in enumerate(self.objects):
            if not self.doc.visible(i) or (lines_only and o['type']!='line'): continue
            # Control handles (including off-curve spline handles) select owners.
            d=min((distance(p,q) for _,q in selection.controls(o)),default=float('inf'))
            if not lines_only: d=min(d,min(distance(p,q) for q,_ in anchors(o)))
            if selection.box_distance(p,self.object_bounds(o))<=tolerance:
                d=min(d,distance(p,selection.nearest_point(p,o)))
            hits.append((d,i))
        best=min(hits,default=(float('inf'),None))
        return best[1] if best[0]<=tolerance else None

    def selected_handle(self,p):
        hits=[(distance(p,q),i,key,q) for i,keys in self.doc.point_selection.items()
              if self.doc.visible(i) for key,q in selection.controls(self.objects[i]) if key in keys]
        best=min(hits,key=lambda item:item[0],default=None)
        return best if best and best[0]*self.scale<=9 else None

    def drag_handle(self,p,owner):
        if self.snap.get():
            candidates=anchors(self.objects[owner])
            best=min(candidates,key=lambda v:distance(p,v[0]))
            if distance(p,best[0])*self.scale<=9: return list(best[0]),best[1]
        if self.grid_snap.get() and self.objects[owner]['type']=='line':
            candidates=line_grid_candidates(p,self.objects[owner],self.grid_spacing/self.grid_subdivisions)
            best=min(candidates,key=lambda v:distance(p,v[0]),default=None)
            if best and distance(p,best[0])*self.scale<=9: return list(best[0]),best[1]
        return (selection.nearest_point(p,self.objects[owner]),'on object') if self.snap.get() else (list(p),'')

    def cancel_snap_hover(self):
        job=getattr(self,'_snap_hover_job',None)
        if job is not None:
            self.root.after_cancel(job)
        self._snap_hover_job=None; self._snap_hover_state=None; self._snap_label_visible=False

    def track_snap_hover(self,e):
        self.snap_history.remember(self.mouse,self.marker)
        self.tracking_cursor=list(self.mouse) if self.mouse is not None else None
        state=(e.x,e.y,tuple(self.mouse) if self.mouse is not None else None,self.marker)
        if state==self._snap_hover_state: return
        self.cancel_snap_hover()
        self._snap_hover_state=state
        if self.mouse is None or not self.marker: return
        def show():
            self._snap_hover_job=None
            current=(tuple(self.mouse) if self.mouse is not None else None,self.marker)
            if self._snap_hover_state==state and current==state[2:]:
                self._snap_label_visible=True; self.draw()
        self._snap_hover_job=self.root.after(SNAP_HOVER_MS,show)

    def update_pointer(self,e=None):
        if self.family.get()!='Select':
            self.pointer_position=None; return
        if e is None:
            x,y=self.canvas.winfo_pointerxy()
            x-=self.canvas.winfo_rootx(); y-=self.canvas.winfo_rooty()
        else: x,y=e.x,e.y
        self.pointer_position=(x,y) if 0<=x<self.canvas.winfo_width() and 0<=y<self.canvas.winfo_height() else None

    def leave_canvas(self,e):
        self.pointer_position=None; self.tracking_cursor=None
        self.cancel_snap_hover(); self.draw()

    def motion(self,e):
        self.update_pointer(e)
        self.mouse,self.marker=self.snap_point(self.world(e.x,e.y)); self.track_snap_hover(e); self.draw()

    def click(self,e):
        self.update_pointer(e)
        self.cancel_snap_hover()
        self.canvas.focus_set(); raw=self.world(e.x,e.y)
        if self.family.get()=='Trim':
            self.trim_click(raw); return
        if self.family.get()=='Select':
            handle=self.selected_handle(raw); i=handle[1] if handle else self.hit(raw)
            extend=bool(e.state & 0x0001)
            self.drag=None; self.drag_preview={}; self.drag_error=''
            if i is None:
                self.box_start=raw; self.box_end=raw; self.box_extend=extend
                if not extend: self.doc.clear_selection()
            elif extend:
                self.doc.point_selection.pop(i,None)
                if i in self.selected: self.selected.remove(i)
                else: self.selected.add(i)
            else:
                # Keep a picked point subset/group for a possible drag; a plain
                # click is promoted to whole-owner selection on button release.
                if i not in self.selected and not handle: self.selected={i}
                source,label=(list(handle[3]),'control point') if handle else self.drag_handle(raw,i)
                ids=set(self.doc.editable_selection())|set(self.doc.editable_point_selection())
                self.drag={'owner':i,'raw':raw,'handle':source,'active':False,'ids':ids}
                self.mouse,self.marker=source,label
                self.track_snap_hover(e)
            self.draw(); return
        if self.family.get()=='Modify' and not self.doc.editable_selection():
            self.error('Select visible, unlocked geometry first.'); return
        p,label=self.snap_point(raw)
        self.snap_history.remember(p,label)
        self.tracking_cursor=list(p)
        before=(copy.deepcopy(self.points),copy.deepcopy(self.refs),self.start)
        try: self.pick(p,raw)
        except (ValueError,KeyError) as ex:
            self.points,self.refs,self.start=before
            self.error(str(ex))
        self.draw()

    def trim_click(self,raw):
        ids={i for i,o in enumerate(self.objects)
             if any(o is boundary for boundary in getattr(self,'trim_cutters',[])) and self.doc.visible(i)}
        if not ids:
            self.error('Select cutting boundaries, then choose Trim.'); return
        hits=[(distance(raw,selection.nearest_point(raw,o)),i)
              for i,o in enumerate(self.objects)
              if i not in ids and self.doc.visible(i) and not o.get('locked',False)
              and selection.box_distance(raw,self.object_bounds(o))<=9/self.scale]
        d,i=min(hits,default=(float('inf'),None))
        if d>9/self.scale: return
        try:
            self.doc.trim_object(i,ids,selection.nearest_point(raw,self.objects[i]))
            self.mouse=None; self.marker=''; self.refresh_layers(); self.draw()
        except ValueError as ex: self.error(str(ex))

    def update_drag(self,e):
        if self.drag is None: return
        raw=self.world(e.x,e.y)
        if distance(raw,self.drag['raw'])*self.scale>4: self.drag['active']=True
        if not self.drag['active']: return
        self.start=self.drag['handle']
        desired=geo.add(self.drag['handle'],geo.sub(raw,self.drag['raw']))
        target,label=self.snap_point(desired,exclude=self.drag['ids'])
        self.mouse,self.marker=target,label
        self.track_snap_hover(e)
        dx,dy=geo.sub(target,self.drag['handle'])
        try:
            self.drag_preview=self.doc.selection_updates(dx,dy); self.drag_error=''
        except ValueError as ex:
            self.drag_preview={}; self.drag_error=str(ex)

    def drag_select(self,e):
        self.update_pointer(e)
        if self.drag is not None:
            self.update_drag(e); self.draw()
        elif self.box_start is not None:
            self.cancel_snap_hover()
            self.box_end=self.world(e.x,e.y); self.draw()

    def release_select(self,e):
        self.update_pointer(e)
        if self.drag is not None:
            self.update_drag(e)
            if self.drag['active']:
                if self.drag_error: self.error(self.drag_error)
                else: self.doc.commit_updates(self.drag_preview)
            else:
                self.selected={self.drag['owner']}
            self.drag=None; self.drag_preview={}; self.drag_error=''; self.start=None
            self.draw(); return
        if self.box_start is None: return
        a=self.box_start; b=self.world(e.x,e.y)
        if distance(a,b)*self.scale>4:
            self.doc.select_window(a,b,extend=self.box_extend)
        self.box_start=None; self.box_end=None; self.draw()

    def double_click(self,e):
        if self.family.get()=='Select':
            self.cancel(); self.edit_dialog()

    def pick(self,p,raw=None):
        family=self.family.get(); method=self.tool.get(); raw=p if raw is None else raw
        if family=='Modify':
            self.points.append(p); self.start=self.points[0]
            if len(self.points)==1: self.set_point_fields(0,p)
            needed=3 if method in ['Rotate','Scale'] else 2
            if len(self.points)==needed:
                pivot=self.field_point(0)
                a,b=self.points[-2:]
                if method=='Move':
                    dx,dy=geo.sub(p,pivot); self.params['dx'].set(f'{dx:.12g}'); self.params['dy'].set(f'{dy:.12g}')
                elif method=='Rotate':
                    u,v=geo.sub(a,pivot),geo.sub(b,pivot); geo.unit(u); geo.unit(v)
                    self.params['angle'].set(f'{math.degrees(math.atan2(geo.cross(u,v),geo.dot(u,v))):.12g}')
                elif method=='Scale':
                    d=distance(pivot,a)
                    if d<geo.EPS: raise ValueError('Reference point must differ from the scale pivot.')
                    self.params['factor'].set(f'{distance(pivot,b)/d:.12g}')
                else:
                    geo.unit(geo.sub(p,pivot)); self.params['angle'].set(f'{math.degrees(geo.angle(pivot,p)):.12g}')
                self.apply_parameters()
            return
        if family=='Splines':
            if len(self.points)>=200: raise ValueError('Use at most 200 points per spline.')
            if self.points and distance(self.points[-1],p)<geo.EPS: raise ValueError('Choose a different next point.')
            self.points.append(p); self.start=p; self.set_point_fields(0,p); return
        # Existing entered coordinates remain authoritative for already-picked points.
        for i in range(len(self.points)):
            if 'x'+(str(i+1) if i else '') in self.params: self.points[i]=self.field_point(i)
        ref=None
        if method=='Start tangent + end' and len(self.points)==1:
            geo.unit(geo.sub(p,self.points[0]))
        needs_line=(method=='Offset from line' and not self.points) or method=='Two tangent lines'
        if needs_line:
            idx=self.hit(raw,True)
            if idx is None: raise ValueError('Click close to an existing visible line.')
            ref=copy.deepcopy(self.objects[idx]); p=geo.project(p,ref['a'],ref['b'],True)
        self.set_point_fields(len(self.points),p)
        self.points.append(p); self.refs.append(ref); self.start=self.points[0]
        if len(self.points)==1: return
        a,b=self.points[:2]
        if family=='Lines' and method!='Offset from line': self.update_line_fields(a,b)
        if method=='Center + diameter': self.params['diameter'].set(f'{2*distance(a,b):.12g}')
        if method=='Offset from line':
            n=geo.normal(geo.unit(geo.sub(self.refs[0]['b'],self.refs[0]['a'])))
            self.params['offset'].set(f'{geo.dot(geo.sub(b,self.refs[0]["a"]),n):.12g}')
        if len(self.points)==(3 if method in THREE else 2):
            self.create_object(self.points)

    def enter_point(self):
        before=(copy.deepcopy(self.points),copy.deepcopy(self.refs),self.start)
        try:
            if self.tool.get()=='Center + diameter' and self.points:
                self.apply_parameters(); return
            index=0 if self.family.get() in ['Splines','Modify'] else len(self.points)
            if 'x'+(str(index+1) if index else '') not in self.params: index=0
            self.pick(self.field_point(index)); self.draw()
        except (ValueError,KeyError) as ex:
            self.points,self.refs,self.start=before
            self.error(str(ex))

    def create_object(self,points):
        self.cancel_snap_hover()
        obj=construct(self.tool.get(),points,self.values(),self.refs,self.clockwise.get())
        obj['color']=self.color.get(); self.doc.add([obj])
        end=list(points[-1]); connected=self.tool.get()=='Connected points'
        self.points=[end] if connected else []; self.refs=[None] if connected else []
        self.start=end if connected else None; self.mouse=None; self.marker=''
        if connected: self.set_point_fields(0,end)
        self.refresh_layers(); self.draw()

    def apply_parameters(self):
        try:
            family=self.family.get(); method=self.tool.get(); v=self.values()
            if family=='Select': return
            if family=='Modify':
                self.doc.transform_selected(method,copy_objects=self.copy_mode.get(),pivot=[v['x'],v['y']],
                                            dx=v.get('dx',0),dy=v.get('dy',0),angle=v.get('angle',0),factor=v.get('factor',1))
                self.cancel(); return
            if family=='Splines':
                self.enter_point(); return
            pts=point_values(v,3 if method in THREE else 2)
            if family=='Lines' and method!='Offset from line':
                if self.last_parameter in ['length','angle']:
                    if v['length']<=0: raise ValueError('Length must be positive.')
                    pts[1]=geo.polar(pts[0],v['length'],math.radians(v['angle']))
                elif self.last_parameter in ['dx','dy']: pts[1]=geo.add(pts[0],[v['dx'],v['dy']])
                self.set_point_fields(1,pts[1]); self.update_line_fields(*pts)
            self.create_object(pts)
        except (ValueError,KeyError) as ex: self.error(str(ex))

    def finish(self):
        if self.family.get()=='Splines':
            try:
                if len(self.points)<2: raise ValueError('Pick at least two spline points.')
                self.create_object(self.points)
            except ValueError as ex: self.error(str(ex))
        elif self.tool.get()=='Connected points': self.cancel()

    def cancel(self):
        self.cancel_snap_hover()
        self.trim_cutters=[]; self.tracking_cursor=None
        self.points=[]; self.refs=[]; self.start=None; self.mouse=None; self.marker=''
        self.box_start=None; self.box_end=None
        self.drag=None; self.drag_preview={}; self.drag_error=''
        self.draw()

    def error(self,text): messagebox.showerror('BrianCAD',text,parent=self.root)

    def prompt(self):
        method=self.tool.get(); n=len(self.points)
        if self.family.get()=='Trim':
            count=len(getattr(self,'trim_cutters',[]))
            return f'{count} active cutting boundaries | Click section to remove; right-click exits' if count else 'Select cutting boundaries, then choose Trim'
        if self.family.get()=='Select':
            if getattr(self,'drag',None) and self.drag['active']:
                return self.drag_error or 'Drag selection; release to drop; Esc cancels'
            return 'Click: whole object | box: whole objects / partial handles | drag: move'
        if self.family.get()=='Modify':
            prompts={'Move':['Pick reference point','Pick destination'], 'Rotate':['Pick pivot','Pick reference direction','Pick new direction'],
                     'Scale':['Pick pivot','Pick reference length','Pick new length'], 'Mirror':['Pick first axis point','Pick second axis point']}
            return prompts[method][min(n,len(prompts[method])-1)]
        if self.family.get()=='Splines': return f'{n} points  |  pick next; Enter finishes'
        if method=='Offset from line': return 'Pick source line' if not n else 'Pick offset side/distance, or enter Offset and Apply'
        if method=='Start tangent + end': return ['Pick arc start','Pick tangent direction point','Pick arc endpoint (direction is automatic)'][min(n,2)]
        if method=='Two tangent lines': return 'Pick exact first contact on a line' if not n else 'Pick second tangent line near desired contact'
        if method=='Center + start + end': return ['Pick center','Pick arc start','Pick end direction (projected to radius)'][min(n,2)]
        if method in ['Three-point arc','Three-point circle']: return ['Pick first point','Pick second point','Pick third point'][min(n,2)]
        if method in ['Center + axis + width','Axis endpoints + width']: return ['Pick center / first axis endpoint','Pick axis endpoint','Pick minor-axis width'][min(n,2)]
        if method=='Center + diameter': return 'Pick center, or enter center and diameter' if not n else 'Pick circumference point'
        return 'Pick first point / center' if not n else 'Pick second point'

    def preview(self):
        if self.mouse is None or not self.points or self.family.get() in ['Select','Modify']: return None
        try:
            pts=self.points+[self.mouse]
            if self.tool.get()=='Start tangent + end':
                pts=[self.field_point(i) for i in range(len(self.points))]+[self.mouse]
            if self.family.get()=='Splines':
                if len(pts)<2: return None
                return construct(self.tool.get(),pts,{},self.refs)
            if len(pts)!=(3 if self.tool.get() in THREE else 2):
                return {'type':'line','a':self.points[-1],'b':self.mouse}
            vals=self.values()
            if self.tool.get()=='Center + diameter': vals['diameter']=2*distance(pts[0],self.mouse)
            if self.tool.get()=='Offset from line': return geo.offset_line(self.refs[0],p=self.mouse)
            if self.tool.get()=='Two tangent lines': return None
            return construct(self.tool.get(),pts,vals,self.refs,self.clockwise.get())
        except (ValueError,KeyError): return None

    def draw_object(self,o,color=None,dash=None):
        pts=geo.path(o); coords=[v for p in pts for v in self.screen(p)]
        pattern=dash or {'Solid':None,'Dashed':(6,4),'Dotted':(1,3)}.get(o.get('pattern','Solid'))
        width=max(1,min(5,o.get('weight',.01)*self.scale))
        opts={'fill':color or o.get('color',COLORS['Black']),'width':width}
        if pattern: opts['dash']=pattern
        self.canvas.create_line(*coords,**opts)

    def draw(self):
        if not hasattr(self,'canvas'): return
        c=self.canvas; c.delete('all'); w=c.winfo_width(); h=c.winfo_height()
        step=self.grid_spacing/self.grid_subdivisions
        major_visible=self.grid_spacing*self.scale>=8
        minor_visible=self.grid_subdivisions>1 and step*self.scale>=8
        if self.grid.get():
            lo=self.world(0,h); hi=self.world(w,0)
            for axis in (0,1):
                for spacing,major in [(step,False),(self.grid_spacing,True)]:
                    if not major and not minor_visible: continue
                    for i in grid_positions(lo[axis],hi[axis],spacing,self.scale,8):
                        if not major and i%self.grid_subdivisions==0: continue
                        q=self.screen([i*spacing,0] if axis==0 else [0,i*spacing])
                        coords=(q[0],0,q[0],h) if axis==0 else (0,q[1],w,q[1])
                        c.create_line(*coords,fill=GRID_COLOR,dash=(2,3) if major else (1,9))
        x,y=self.origin
        c.create_line(0,y,w,y,fill='#cbd2db'); c.create_line(x,0,x,h,fill='#cbd2db')
        c.create_text(x+10,y+10,text='0,0',anchor='nw',fill='#8b929a')
        for i,original in enumerate(self.objects):
            if not self.doc.visible(i): continue
            o=getattr(self,'drag_preview',{}).get(i,original)
            self.draw_object(o,color='#d08213' if i in self.selected else None)
            partial=self.doc.point_selection.get(i,set())
            if i in self.selected or partial or o.get('controls'):
                for key,p in selection.controls(o):
                    a,b=self.screen(p)
                    chosen=i in self.selected or key in partial
                    c.create_rectangle(a-4,b-4,a+4,b+4,outline='#b66b00' if chosen else '#708296',
                                       fill='#eaa23d' if chosen else 'white')
        if self.tool.get()=='Start tangent + end' and len(self.points)>=2:
            try:
                c.create_line(*self.screen(self.field_point(0)),*self.screen(self.field_point(1)),
                              fill='#9dbcd5',dash=(3,5),tags=('tangent-guide',))
            except (ValueError,KeyError): pass
        preview=self.preview()
        if preview: self.draw_object(preview,color='#708296',dash=(5,3))
        if self.family.get()=='Splines' and self.points:
            coords=[v for p in self.points for v in self.screen(p)]
            if len(coords)>=4: c.create_line(*coords,fill='#b0becb',dash=(2,4))
            for p in self.points:
                a,b=self.screen(p); c.create_rectangle(a-3,b-3,a+3,b+3,outline='#708296')
        if self.start is not None and (self.family.get() in ['Lines','Modify'] or getattr(self,'drag',None)):
            a,b=self.screen(self.start)
            c.create_line(0,b,w,b,fill='#b8cddd',dash=(3,5)); c.create_line(a,0,a,h,fill='#b8cddd',dash=(3,5))
            if self.marker in ['45°','135°']:
                slope=-1 if self.marker=='45°' else 1
                c.create_line(0,b-slope*a,w,b+slope*(w-a),fill='#9dbcd5',dash=(3,5))
        history=getattr(self,'snap_history',None)
        excluded=set(self.selected) if self.family.get()=='Modify' else set()
        if getattr(self,'drag',None): excluded.update(self.drag['ids'])
        guides=history.guides(getattr(self,'tracking_cursor',None),self.scale,self.tracking_exclusions(excluded)) if history and self.snap.get() else []
        label_counts=[0,0]
        for axis,value in guides:
            sx,sy=self.screen([value,0] if axis==0 else [0,value])
            coords=(sx,0,sx,h) if axis==0 else (0,sy,w,sy)
            c.create_line(*coords,fill='#8a929b',dash=(1,5),tags=('tracking-guide',))
            tx,ty=(sx+5,16+12*label_counts[axis]) if axis==0 else (10+52*label_counts[axis],sy-5)
            c.create_text(tx,ty,text='align x' if axis==0 else 'align y',anchor='sw',
                          fill=SNAP_LABEL_COLOR,font=self.snap_label_font,tags=('tracking-label',))
            label_counts[axis]+=1
        if self.mouse is not None and self.marker:
            a,b=self.screen(self.mouse)
            c.create_line(a-3,b-3,a+3,b+3,fill='black',width=1,tags=('snap-marker',))
            c.create_line(a-3,b+3,a+3,b-3,fill='black',width=1,tags=('snap-marker',))
            if getattr(self,'_snap_label_visible',False):
                c.create_text(a+12,b-14,text=self.marker,anchor='w',fill=SNAP_LABEL_COLOR,
                              font=self.snap_label_font,tags=('snap-label',))
        if self.box_start is not None and self.box_end is not None:
            c.create_rectangle(*self.screen(self.box_start),*self.screen(self.box_end),outline='#397cc1',dash=(4,3))
        pointer=getattr(self,'pointer_position',None)
        if self.family.get()=='Select' and pointer is not None:
            # Raw screen coordinates keep the arrow tip at the physical mouse,
            # independently of the snapped target marker.
            px,py=pointer
            shape=[(0,0),(0,16),(4,12),(8,20),(11,18),(7,10),(13,10)]
            c.create_polygon(*[v for dx,dy in shape for v in (px+dx,py+dy)],
                             fill='#202b36',outline='white',width=1,tags=('select-pointer',))
        hidden=' (dense lines hidden)' if self.grid.get() and (not major_visible or (self.grid_subdivisions>1 and not minor_visible)) else ''
        pos='' if self.mouse is None else f' | X {self.mouse[0]:.4f} Y {self.mouse[1]:.4f}'
        point_count=sum(len(keys) for keys in self.doc.point_selection.values())
        self.status.set(f'{self.tool.get()}  |  {self.prompt()} | {len(self.selected)} objects + {point_count} handles selected | grid {self.grid_spacing:g}/{self.grid_subdivisions}{hidden}{pos}')
        self.layer_status.set('Active layer: '+self.doc.active)
        self.root.title((' |  ' if self.doc.dirty else '')+'BrianCAD - '+(os.path.basename(self.path) if self.path else 'Untitled'))

    def delete(self): self.doc.delete_selected(); self.cancel(); self.refresh_layers()
    def undo(self):
        self.doc.undo()
        if self.family.get()=='Trim': self.return_to_select()
        else: self.cancel()
        self.refresh_layers()
    def redo(self):
        self.doc.redo()
        if self.family.get()=='Trim': self.return_to_select()
        else: self.cancel()
        self.refresh_layers()

    def zoom(self,e,factor):
        self.tracking_cursor=None
        self.cancel_snap_hover()
        p=self.world(e.x,e.y); self.scale=max(.01,min(100000,self.scale*factor))
        self.origin=[e.x-p[0]*self.scale,e.y+p[1]*self.scale]; self.motion(e)
    def pan_start(self,e):
        self.update_pointer(e)
        self.tracking_cursor=None
        self.cancel_snap_hover(); self.pan=[e.x,e.y]; self.draw()
    def pan_move(self,e):
        self.update_pointer(e)
        self.cancel_snap_hover()
        if self.pan:
            self.origin[0]+=e.x-self.pan[0]; self.origin[1]+=e.y-self.pan[1]
            self.pan=[e.x,e.y]; self.draw()
    def fit(self):
        self.root.update_idletasks()
        pts=[p for i,o in enumerate(self.objects) if self.doc.visible(i) for p in geo.path(o)]
        if not pts: return
        low=[min(p[k] for p in pts) for k in (0,1)]; high=[max(p[k] for p in pts) for k in (0,1)]
        w=max(100,self.canvas.winfo_width()); h=max(100,self.canvas.winfo_height())
        self.scale=min((w-80)/max(high[0]-low[0],.5),(h-80)/max(high[1]-low[1],.5))
        self.origin=[w/2-(low[0]+high[0])*self.scale/2,h/2+(low[1]+high[1])*self.scale/2]; self.draw()

    def grid_dialog(self):
        dlg=tk.Toplevel(self.root); dlg.title('Grid'); dlg.transient(self.root); dlg.resizable(False,False)
        f=ttk.Frame(dlg,padding=16); f.pack()
        spacing=tk.StringVar(value=f'{self.grid_spacing:g}'); divisions=tk.StringVar(value=str(self.grid_subdivisions))
        first=None
        for i,(label,var) in enumerate([('Grid spacing (inches)',spacing),('# of subdivisions',divisions)]):
            ttk.Label(f,text=label).grid(row=i,column=0,padx=6,pady=5)
            e=ttk.Entry(f,textvariable=var,width=14); e.grid(row=i,column=1,pady=5)
            if first is None: first=e
        def apply():
            try: major,count=grid_values(spacing.get(),divisions.get())
            except ValueError as ex: messagebox.showerror('Grid',str(ex),parent=dlg); return
            if (major,count)!=(self.grid_spacing,self.grid_subdivisions):
                self.doc.checkpoint(); self.grid_spacing,self.grid_subdivisions=major,count
            dlg.destroy(); self.draw()
        ttk.Button(f,text='Cancel',command=dlg.destroy).grid(row=2,column=0,pady=10)
        ttk.Button(f,text='OK',command=apply).grid(row=2,column=1,pady=10)
        dlg.bind('<Return>',lambda e:apply()); dlg.bind('<Escape>',lambda e:dlg.destroy())
        dlg.grab_set(); first.focus_set(); first.selection_range(0,'end')

    def refresh_layers(self):
        if self.layer_window is not None and self.layer_window.winfo_exists(): self.layer_refresh()

    def layers_dialog(self):
        if self.layer_window is not None and self.layer_window.winfo_exists(): self.layer_window.lift(); return
        dlg=tk.Toplevel(self.root); self.layer_window=dlg; dlg.title('Layers'); dlg.transient(self.root)
        f=ttk.Frame(dlg,padding=12); f.pack(fill='both',expand=True)
        tree=ttk.Treeview(f,columns=('active','name'),show='tree headings',selectmode='browse',height=13)
        tree.heading('#0',text='Eye'); tree.column('#0',width=45,stretch=False)
        self.layer_icons=[]
        for visible in (False,True):
            icon=tk.PhotoImage(master=dlg,width=18,height=14)
            for x in range(18):
                for y in range(14):
                    ellipse=((x-8.5)/8)**2+((y-6.5)/5)**2
                    eye=(.65<ellipse<1.05 or (x-8.5)**2+(y-6.5)**2<5) if visible else (abs(y-6.5)<1 and 1<x<17) or (abs(y-x*.6-1)<.8 and 1<x<17)
                    if eye: icon.put('#273543',to=(x,y))
            self.layer_icons.append(icon)
        for col,title,width in [('active','Active',55),('name','Layer',210)]:
            tree.heading(col,text=title); tree.column(col,width=width,anchor='w')
        self.layer_tree=tree
        tree.grid(row=0,column=0,rowspan=5,sticky='nsew')
        f.columnconfigure(0,weight=1); f.rowconfigure(0,weight=1)
        rename=tk.StringVar(); ttk.Label(f,text='Layer name').grid(row=5,column=0,sticky='w',pady=(8,0))
        ttk.Entry(f,textvariable=rename).grid(row=6,column=0,sticky='ew')
        def selected_name():
            items=tree.selection()
            if not items: raise ValueError('Highlight a layer first.')
            return tree.item(items[0],'values')[-1]
        def refresh():
            keep=selected_name() if tree.selection() else self.doc.active
            if keep not in [l['name'] for l in self.doc.layers]: keep=self.doc.active
            tree.delete(*tree.get_children())
            for i,l in enumerate(self.doc.layers):
                key=str(i); tree.insert('', 'end',iid=key,image=self.layer_icons[int(l['visible'])],values=('*' if l['name']==self.doc.active else '',l['name']))
                if l['name']==keep: tree.selection_set(key)
        self.layer_refresh=refresh
        def action(kind):
            try:
                name=selected_name() if kind!='new' else None
                if kind=='new': self.doc.add_layer(rename.get())
                elif kind=='rename': self.doc.rename_layer(name,rename.get())
                elif kind=='set': self.doc.set_layer(name)
                elif kind=='hide': self.doc.toggle_layer(name)
                elif kind=='delete':
                    target=next((l['name'] for l in self.doc.layers if l['name']!=name),None)
                    if target is None: raise ValueError('Keep at least one layer.')
                    if not messagebox.askyesno('Delete layer',f'Delete {name}? Its objects will move to {target}.',parent=dlg): return
                    self.doc.delete_layer(name)
                refresh(); self.cancel()
            except ValueError as ex: messagebox.showerror('Layers',str(ex),parent=dlg)
        for i,(label,kind) in enumerate([('New','new'),('Delete','delete'),('Show / Hide','hide'),('Set Layer','set'),('Rename','rename')]):
            ttk.Button(f,text=label,command=lambda k=kind:action(k)).grid(row=i,column=1,padx=(10,0),pady=4,sticky='ew')
        def highlight(e):
            if tree.selection(): rename.set(selected_name())
        def double(e):
            row=tree.identify_row(e.y)
            if row:
                tree.selection_set(row); action('hide' if tree.identify_column(e.x)=='#0' else 'set')
            return 'break'
        tree.bind('<<TreeviewSelect>>',highlight); tree.bind('<Double-1>',double)
        ttk.Label(f,text='Single-click highlights. Double-click name: active. Double-click eye: show/hide.').grid(row=7,column=0,columnspan=2,pady=8)
        refresh()

    def edit_dialog(self):
        ids=sorted(i for i in self.selected if self.doc.visible(i))
        if not ids: self.error('Select at least one object first.'); return
        if self.edit_window is not None and self.edit_window.winfo_exists(): self.edit_window.lift(); return
        index=ids[0]; original=copy.deepcopy(self.objects[index])
        dlg=tk.Toplevel(self.root); self.edit_window=dlg; dlg.title('Edit objects'); dlg.transient(self.root)
        # Modal editing keeps the captured object index stable while fields are edited.
        f=ttk.Frame(dlg,padding=14); f.pack(fill='both',expand=True)
        ttk.Label(f,text=original['type'].title()+('  |  first selected object' if len(ids)>1 else ''),font=('',12,'bold')).grid(row=0,column=0,columnspan=2,sticky='w')
        fields={}; row=1
        def field(key,label,value,choices=None):
            nonlocal row
            ttk.Label(f,text=label).grid(row=row,column=0,sticky='w',padx=(0,12),pady=3)
            var=tk.StringVar(value=str(value)); fields[key]=var
            w=ttk.Combobox(f,textvariable=var,values=choices,state='readonly',width=27) if choices else ttk.Entry(f,textvariable=var,width=30)
            w.grid(row=row,column=1,sticky='ew',pady=3); row+=1
        reverse={v:k for k,v in COLORS.items()}
        field('layer','Layer',original['layer'],[l['name'] for l in self.doc.layers])
        field('color','Color',reverse[original['color']],list(COLORS))
        field('locked','Locked',str(original['locked']),['False','True'])
        field('pattern','Pattern',original['pattern'],['Solid','Dashed','Dotted'])
        field('weight','Weight (inches)',original['weight'])
        field('controls','Show control points',str(original['controls']),['False','True'])
        kind=original['type']; geometry_fields=[]
        def number(key,label,value): geometry_fields.append(key); field(key,label,f'{value:.12g}')
        if kind=='line':
            for key,p in [('a',original['a']),('b',original['b'])]:
                for k,n in enumerate(['x','y']): number(key+n,('Start ' if key=='a' else 'End ')+n.upper(),p[k])
        elif kind in ['circle','arc','ellipse']:
            number('cx','Center X',original['center'][0]); number('cy','Center Y',original['center'][1])
            if kind=='ellipse':
                number('rx','X semi-axis',original['rx']); number('ry','Y semi-axis',original['ry']); number('angle','Rotation °',math.degrees(original['angle']))
            else: number('diameter','Diameter',original['radius']*2)
            if kind=='arc':
                number('start','Start angle °',math.degrees(original['start'])); number('sweep','Signed sweep °',math.degrees(original['sweep']))
        else:
            field('points','Points: x,y; x,y; ...','; '.join(f'{p[0]:.12g},{p[1]:.12g}' for p in original['points']))
            field('closed','Closed',str(original.get('closed',True)),['False','True'])
            if kind=='spline': field('method','Spline method',original['method'],['through','bezier'])
        self.edit_fields=fields
        total=tk.StringVar(); self.edit_length=total
        ttk.Label(f,textvariable=total).grid(row=row,column=0,columnspan=2,sticky='w',pady=8); row+=1
        def proposed():
            o=copy.deepcopy(original)
            o.update(layer=fields['layer'].get(),color=COLORS[fields['color'].get()],locked=fields['locked'].get()=='True',
                     pattern=fields['pattern'].get(),weight=float(fields['weight'].get()),controls=fields['controls'].get()=='True')
            v={k:float(fields[k].get()) for k in geometry_fields}
            if kind=='line': o['a']=[v['ax'],v['ay']]; o['b']=[v['bx'],v['by']]
            elif kind in ['circle','arc','ellipse']:
                o['center']=[v['cx'],v['cy']]
                if kind=='ellipse': o.update(rx=v['rx'],ry=v['ry'],angle=math.radians(v['angle']))
                else: o['radius']=v['diameter']/2
                if kind=='arc': o.update(start=math.radians(v['start']),sweep=math.radians(v['sweep']))
            else:
                o['points']=[[float(n.strip()) for n in p.split(',')] for p in fields['points'].get().split(';')]
                o['closed']=fields['closed'].get()=='True'
                if kind=='spline': o['method']=fields['method'].get()
            return self.doc.prepare(o)
        def refresh_length(*args):
            try:
                o=proposed(); approx=' (approx.)' if kind in ['ellipse','spline'] else ''
                text=f'Length: {geo.length(o):.6g} in{approx}'
                if len(ids)>1:
                    combined=geo.length(o)+sum(geo.length(self.objects[i]) for i in ids[1:])
                    text+=f'  |  selected total: {combined:.6g} in'
                total.set(text)
            except (ValueError,KeyError,TypeError,OverflowError): total.set('Length: - (check entered values)')
        def apply():
            try: obj=proposed()
            except (ValueError,KeyError,TypeError,OverflowError) as ex:
                messagebox.showerror('Edit objects',str(ex),parent=dlg); return
            self.doc.edit(index,obj); original.clear(); original.update(copy.deepcopy(obj))
            self.refresh_layers(); self.draw(); refresh_length()
        for var in fields.values(): var.trace_add('write',refresh_length)
        refresh_length()
        buttons=ttk.Frame(f); buttons.grid(row=row,column=0,columnspan=2,sticky='e',pady=8)
        ttk.Button(buttons,text='Close',command=dlg.destroy).pack(side='left',padx=5)
        ttk.Button(buttons,text='Apply',command=apply).pack(side='left')
        dlg.bind('<Escape>',lambda e:dlg.destroy()); dlg.grab_set()

    def discard(self): return not self.doc.dirty or messagebox.askyesno('Unsaved drawing','Discard unsaved changes?',parent=self.root)
    def new(self):
        if self.discard(): self.snap_history.clear(); self.doc=Document(); self.path=None; self.cancel(); self.refresh_layers()
    def save(self,save_as=False):
        path=None if save_as else self.path
        path=path or filedialog.asksaveasfilename(defaultextension='.draft.json',filetypes=[('BrianCAD drawing','*.json')])
        if not path: return
        temp=None
        try:
            with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=os.path.dirname(os.path.abspath(path)),delete=False) as f:
                temp=f.name; json.dump(self.doc.payload(),f,indent=2,allow_nan=False)
            os.replace(temp,path); self.path=path; self.doc.saved=self.doc.state(); self.draw()
        except (OSError,ValueError) as ex:
            if temp and os.path.exists(temp): os.unlink(temp)
            self.error(str(ex))
    def open(self):
        if not self.discard(): return
        path=filedialog.askopenfilename(filetypes=[('BrianCAD drawing','*.json')])
        if not path: return
        try:
            with open(path,encoding='utf-8') as f: doc=Document.from_payload(json.load(f))
            self.snap_history.clear(); self.doc=doc; self.path=path; self.cancel(); self.refresh_layers(); self.fit()
        except (OSError,ValueError,TypeError,KeyError,OverflowError) as ex: self.error(str(ex))
    def close(self):
        if self.discard():
            self.cancel_snap_hover(); self.root.destroy()


if __name__=='__main__':
    root=tk.Tk(); Draft(root); root.mainloop()
