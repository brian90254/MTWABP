#!/usr/bin/env python3
"""BrianCAD: a Vellum-inspired 2D desktop drafting application."""
import copy
from collections import OrderedDict
from types import SimpleNamespace
import json
import math
import os
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, font as tkfont
import cad_geometry as geo
import cad_selection as selection
import cad_trim
import cad_guides
from curve_trim import crossings
import cad_dimensions
import cad_chamfer
import cad_groups
import cad_offset
import cad_properties
import cad_dxf
import cad_import
import cad_clipboard
from cad_recent import RecentFiles
from cad_units import UNITS, parse_number, format_value, display_value, field_kind
from snap_tracking import SnapHistory
from cad_geometry import dist as distance, anchors, hit_distance
from cad_document import Document, COLORS, layer_sort_key
from cad_tools import METHODS, THREE, DEFAULTS, LABELS, fields_for, point_values, construct
from grid_snap import grid_values, grid_positions, grid_candidates, line_grid_candidates, alignment_candidates


SNAP_HOVER_MS=600
GRID_COLOR='#bcc8d5'
DISPLAY_PATH_POINT_LIMIT=250000
SNAP_LABEL_COLOR='#626a73'

def validate(data):
    """Compatibility entry point for the first prototype's object-only validator."""
    return Document.from_payload(data).objects


class CanvasLayer:
    """Assign ownership tags so redraws can retain the static canvas scene."""
    def __init__(self,canvas,tag): self.canvas=canvas; self.tag=tag
    def __getattr__(self,name):
        method=getattr(self.canvas,name)
        if not name.startswith('create_'): return method
        def create(*args,**kwargs):
            kwargs['tags']=(self.tag,)+tuple(kwargs.get('tags',()))
            return method(*args,**kwargs)
        return create


class Draft:
    def __init__(self,root):
        self.root=root; self.doc=Document(); self.path=None;self._tool_defaults={};self._tool_methods={}
        self.recent_files=RecentFiles();self._zoom_window=False;self._view_box_start=None;self._view_box_end=None
        self.scale=90.; self.origin=[470.,320.]; self.pan=None
        self.points=[]; self.refs=[]; self.start=None; self.mouse=None; self.marker=''
        self.snap_history=SnapHistory(); self.tracking_cursor=None
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
        for key,action in [('z',self.undo),('y',self.redo),('s',self.save),('o',self.open),('g',self.group_selected),('n',self.new),('c',self.copy_objects),('v',self.paste_objects)]:
            root.bind('<Control-'+key+'>',lambda e,f=action:self.shortcut(e,f))
            if root.tk.call('tk','windowingsystem')=='aqua':
                root.bind('<Command-'+key+'>',lambda e,f=action:self.shortcut(e,f))
        root.bind('<Control-Shift-S>',lambda e:self.shortcut(e,lambda:self.save(True)))
        if root.tk.call('tk','windowingsystem')=='aqua':
            root.bind('<Command-Shift-S>',lambda e:self.shortcut(e,lambda:self.save(True)))
        root.bind('<Control-Shift-G>',lambda e:self.shortcut(e,self.ungroup_selected))
        if root.tk.call('tk','windowingsystem')=='aqua':
            root.bind('<Command-Shift-G>',lambda e:self.shortcut(e,self.ungroup_selected))
        root.bind('<Escape>',self.escape)
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

    def build_menus(self):
        self.menu_bar=tk.Menu(self.root,tearoff=False);self.menus={}
        prefix='Cmd' if self.root.tk.call('tk','windowingsystem')=='aqua' else 'Ctrl'
        for name in ('File','Edit','Objects','View'):
            menu=tk.Menu(self.menu_bar,tearoff=False);self.menus[name]=menu
            self.menu_bar.add_cascade(label=name,menu=menu)
        file=self.menus['File']
        file.add_command(label='New',accelerator=prefix+'+N',command=self.new)
        file.add_command(label='Open...',accelerator=prefix+'+O',command=self.open)
        self.recent_menu=tk.Menu(file,tearoff=False,postcommand=self.refresh_recent_menu)
        file.add_cascade(label='Open Recent...',menu=self.recent_menu)
        file.add_separator()
        file.add_command(label='Save',accelerator=prefix+'+S',command=self.save)
        file.add_command(label='Save As...',accelerator=prefix+'+Shift+S',command=lambda:self.save(True))
        file.add_separator()
        file.add_command(label='Import...',command=self.import_drawing)
        file.add_command(label='Export...',command=self.export_dxf_dialog)
        edit=self.menus['Edit']
        edit.add_command(label='Undo',accelerator=prefix+'+Z',command=self.undo)
        edit.add_command(label='Redo',accelerator=prefix+'+Y',command=self.redo)
        edit.add_separator()
        edit.add_command(label='Copy',accelerator=prefix+'+C',command=self.copy_objects)
        edit.add_command(label='Paste',accelerator=prefix+'+V',command=self.paste_objects)
        edit.add_separator()
        edit.add_command(label='Edit Objects...',command=self.edit_dialog)
        edit.add_command(label='Flip Horizontal',command=lambda:self.flip_selection(True))
        edit.add_command(label='Flip Vertical',command=lambda:self.flip_selection(False))
        edit.add_command(label='Polar Duplicate...',command=self.polar_dialog)
        edit.add_command(label='Units...',command=self.units_dialog)
        objects=self.menus['Objects']
        objects.add_command(label='Group',accelerator=prefix+'+G',command=self.group_selected)
        objects.add_command(label='Ungroup',accelerator=prefix+'+Shift+G',command=self.ungroup_selected)
        objects.add_command(label='Divide...',command=self.divide_dialog)
        objects.add_separator()
        objects.add_command(label='Layers...',command=self.layers_dialog)
        view=self.menus['View']
        view.add_command(label='Fit',command=self.fit)
        view.add_command(label='Zoom In',command=lambda:self.zoom_center(1.25))
        view.add_command(label='Zoom Out',command=lambda:self.zoom_center(.8))
        view.add_command(label='Window',command=self.begin_window_zoom)
        self.root.configure(menu=self.menu_bar);self.refresh_recent_menu()

    def refresh_recent_menu(self):
        self.recent_menu.delete(0,'end')
        if not self.recent_files.paths:
            self.recent_menu.add_command(label='No recent drawings',state='disabled');return
        for path in self.recent_files.paths:
            self.recent_menu.add_command(label=path,command=lambda p=path:self.open(p))
        self.recent_menu.add_separator()
        self.recent_menu.add_command(label='Clear Recent',command=self.clear_recent)

    def clear_recent(self):self.recent_files.clear();self.refresh_recent_menu()

    def remember_drawing(self,path):self.recent_files.remember(path);self.refresh_recent_menu()

    def build_ui(self):
        self.build_menus()
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
            ttk.Radiobutton(pens,text=name,variable=self.color,value=color,command=self.choose_pen_color).grid(row=i//2,column=i%2,sticky='w',padx=(0,14))
        ttk.Separator(side).pack(fill='x',pady=10)
        ttk.Checkbutton(side,text='Object snaps / alignment',variable=self.snap).pack(anchor='w')
        ttk.Checkbutton(side,text='Show grid',variable=self.grid,command=self.draw).pack(anchor='w',pady=3)
        ttk.Checkbutton(side,text='Snap to grid',variable=self.grid_snap).pack(anchor='w')
        ttk.Button(side,text='Grid preferences...',command=self.grid_dialog).pack(fill='x',pady=8)
        ttk.Label(side,textvariable=self.layer_status,wraplength=200).pack(anchor='w',pady=6)
        ttk.Label(side,text='Shift-click: add/remove\nDrag blank: window selection\nDrag selection: move\nDouble-click: edit\nWheel: zoom; middle drag: pan\nEsc: cancel; Delete: objects\nRight-click: Select\nSpline: right-click/Enter finishes',wraplength=205).pack(anchor='w',pady=8)
        self.canvas=tk.Canvas(body,bg='white',highlightthickness=0,cursor='arrow')
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
        if event.widget.winfo_class() in ['Entry','TEntry','Text','TCombobox'] and fn in [self.undo,self.redo,self.copy_objects,self.paste_objects]: return
        fn(); return 'break'

    def escape(self,event=None):
        if getattr(self,'polar_window',None):return self.close_polar()
        if getattr(self,'_zoom_window',False):self.cancel_window_zoom();return 'break'
        return self.return_to_select() if self.family.get()=='Trim' else self.cancel()

    def right_click(self,event=None):
        if getattr(self,'polar_window',None):return self.close_polar()
        if getattr(self,'_zoom_window',False):self.cancel_window_zoom();return 'break'
        if getattr(self,'_paste',None):self.cancel();return 'break'
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
        family=self.family.get();methods=METHODS[family]
        method=getattr(self,'_tool_methods',{}).get(family,methods[0])
        self.tool.set(method if method in methods else methods[0]);self.method_box.configure(values=methods)
        self.method_changed()

    def method_changed(self):
        if not hasattr(self,'_tool_methods'):self._tool_methods={}
        if self.tool.get() in METHODS[self.family.get()]:self._tool_methods[self.family.get()]=self.tool.get()
        self.snap_history.clear()
        self.canvas.configure(cursor='arrow')
        self.cancel()
        if self.family.get()=='Trim':
            ids=set(self.selected)|set(self.doc.point_selection)
            ids={i for i in ids if self.doc.visible(i) and self.objects[i]['type'] in cad_trim.BOUNDARIES}
            self.trim_cutters=[self.objects[i] for i in sorted(ids)]
            self.selected=ids; self.doc.point_selection={}
        if self.family.get()=='Offset':
            ids=sorted(set(self.doc.editable_selection())|set(self.doc.editable_point_selection()))
            self.offset_sources=[self.objects[i] for i in ids]
            self.selected=set(ids);self.doc.point_selection={}
        self.configure_parameters()

    def configure_parameters(self):
        for child in self.parameter_frame.winfo_children(): child.destroy()
        self.params={}; self.parameter_entries={}; self.last_parameter=None;self._parameter_unit=self.doc.display_unit
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
            if self.family.get()=='Offset': label={'offset':'Distance','x':'Direction X','y':'Direction Y'}[key]
            ttk.Label(cell,text=label,width=12 if self.family.get()=='Offset' else 9).pack(side='left')
            var=tk.StringVar(value=format_value(getattr(self,'_tool_defaults',{}).get((self.family.get(),self.tool.get(),key),DEFAULTS.get(key,0)),self.doc.display_unit,field_kind(key))); self.params[key]=var
            ent=ttk.Entry(cell,textvariable=var,width=10); ent.pack(side='left')
            ent.bind('<KeyRelease>',lambda e,k=key:self.parameter_changed(k))
            self.parameter_entries[key]=ent
            ent.bind('<FocusOut>',lambda e,k=key:self.commit_parameter_field(k))
            ent.bind('<Return>',lambda e,k=key:self.parameter_return(k))
        saved=getattr(self,'_tool_defaults',{})
        family,method=self.family.get(),self.tool.get()
        if family=='Lines' and method in ('Two points','Connected points') and (family,method,'dx') in saved:
            a=self.field_point(0);b=geo.add(a,[saved[(family,method,'dx')],saved[(family,method,'dy')]])
            self.set_point_fields(1,b);self.update_line_fields(a,b)
        actions=ttk.Frame(self.parameter_frame); actions.grid(row=(len(fields)+3)//4,column=0,columnspan=4,padx=5,pady=4,sticky='w')
        if self.family.get()=='Offset':
            ttk.Button(actions,text='Preview offset',command=self.preview_offset).pack(side='left',padx=3)
            ttk.Button(actions,text='Apply offset',command=self.apply_offset).pack(side='left',padx=3)
            ttk.Label(actions,text='Click a curve if none selected; click a side point for direction.').pack(side='left',padx=6)
        elif self.family.get()=='Chamfer':
            ttk.Label(actions,text='Click two segments on the sides to keep. Right-click: Select.').pack(side='left')
        elif fields:
            if self.family.get()!='Modify':
                ttk.Button(actions,text='Use entered point',command=self.enter_point).pack(side='left',padx=3)
            ttk.Button(actions,text='Apply / Create',command=self.apply_parameters).pack(side='left',padx=3)
        if self.family.get()=='Splines':
            ttk.Button(actions,text='Finish spline',command=self.finish).pack(side='left',padx=3)
        if not fields:
            hint='Pick two snap points, or an on-line/on-curve snap to measure a whole object.' if self.family.get()=='Dimension' else 'Select cutting boundaries before choosing Trim; click a section to remove. Right-click exits.' if self.family.get()=='Trim' else 'Select objects, then double-click to edit or choose a Modify method.'
            ttk.Label(self.parameter_frame,text=hint).grid(row=0,column=0,sticky='w')
        self.draw()

    def focus_parameter(self,key):
        entry=getattr(self,'parameter_entries',{}).get(key)
        if entry is not None:
            entry.focus_set()
            entry.selection_range(0,'end')

    def commit_parameter_field(self,key):
        self.normalize_parameter(key)
        if key in ('x','y') and self.points and self.family.get()=='Lines' and self.tool.get() in ('Two points','Connected points'):
            try:
                value=parse_number(self.params[key].get(),self.doc.display_unit)
            except ValueError:return
            self.points[0]=list(self.points[0])
            self.points[0][key=='y']=value
            self.start=self.points[0]
            self._line_guides=(None,[])
            self.draw()

    def parameter_return(self,key):
        recent=getattr(self,'_recent_mouse_line',None)
        if key=='length' and recent is not None:
            index,original=recent
            if index>=len(self.objects) or self.objects[index] is not original or not self.doc.visible(index) or original.get('locked',False):
                self._recent_mouse_line=None
                self.error('The line is no longer available to resize.')
                return 'break'
            try:
                length=parse_number(self.params['length'].get(),self.doc.display_unit)
                if length<=0:raise ValueError('Length must be positive.')
                end=geo.add(original['a'],geo.mul(geo.unit(geo.sub(original['b'],original['a'])),length))
                self.doc.commit_updates({index:dict(original,b=end)})
            except ValueError as ex:
                self.error(str(ex));return 'break'
            self._recent_mouse_line=(index,self.objects[index])
            if self.tool.get()=='Connected points':
                self.points=[end];self.start=end;self.set_point_fields(0,end)
            else:self.set_point_fields(0,original['a'])
            self.set_point_fields(1,end);self.update_line_fields(original['a'],end)
            self.remember_parameters(self.values())
            self.focus_parameter('length');self.draw()
        else:self.apply_parameters()
        return 'break'

    def parameter_changed(self,key):
        self.last_parameter=key
        if self.family.get()=='Offset': self.offset_preview=[];self.draw()

    def remember_parameters(self,values,obj=None):
        if not hasattr(self,'_tool_defaults'):self._tool_defaults={}
        family,method=self.family.get(),self.tool.get()
        for key in ('diameter','radius','offset','sides','length','angle','factor','dx','dy'):
            if key in values:self._tool_defaults[(family,method,key)]=values[key]
        if family=='Circles' and obj is not None and obj['type']=='circle':
            self._tool_defaults[(family,'Center + diameter','diameter')]=2*obj['radius']
        if family=='Polygons' and 'sides' in values:
            for mode in ('Inscribed polygon','Circumscribed polygon'):
                self._tool_defaults[(family,mode,'sides')]=values['sides']

    def values(self):
        vals={k:parse_number(v.get(),self.doc.display_unit,field_kind(k)) for k,v in self.params.items()}
        if any(not math.isfinite(v) or abs(v)>1e7 for v in vals.values()): raise ValueError('Enter finite values within ±10,000,000.')
        return vals

    def field_point(self,index):
        values=self.values(); suffix=str(index+1) if index else ''
        return [values['x'+suffix],values['y'+suffix]]

    def set_point_fields(self,index,p):
        suffix=str(index+1) if index else ''
        for key,value in zip(['x'+suffix,'y'+suffix],p):
            if key in self.params: self.params[key].set(format_value(value,self.doc.display_unit,field_kind(key)))

    def update_line_fields(self,a,b):
        dx,dy=geo.sub(b,a)
        for k,v in [('dx',dx),('dy',dy),('length',math.hypot(dx,dy)),('angle',math.degrees(math.atan2(dy,dx)))]:
            if k in self.params: self.params[k].set(format_value(v,self.doc.display_unit,field_kind(k)))

    def world(self,x,y): return [(x-self.origin[0])/self.scale,(self.origin[1]-y)/self.scale]
    def screen(self,p): return [self.origin[0]+p[0]*self.scale,self.origin[1]-p[1]*self.scale]

    def visible_ids(self):
        layers={l['name'] for l in self.doc.layers if l['visible']}
        return [i for i,o in enumerate(self.objects) if o.get('layer',self.doc.active) in layers]

    def object_anchors(self,o):
        if not hasattr(self,'_anchor_cache'): self._anchor_cache={}
        if len(self._anchor_cache)>2*len(self.objects)+32: self._anchor_cache.clear()
        cached=self._anchor_cache.get(id(o))
        if cached is None or cached[0]!=o:
            cached=(copy.deepcopy(o),anchors(o)); self._anchor_cache[id(o)]=cached
        return cached[1]

    def object_bounds(self,o):
        if not hasattr(self,'_bounds_cache'): self._bounds_cache={}
        if len(self._bounds_cache)>2*len(self.objects)+32: self._bounds_cache.clear()
        cached=self._bounds_cache.get(id(o))
        unit=self.doc.display_unit if o['type']=='dimension' else None
        if cached is None or cached[0]!=o or cached[1]!=unit:
            cached=(copy.deepcopy(o),unit,selection.bounds(o,self.doc.display_unit)); self._bounds_cache[id(o)]=cached
        return cached[2]

    def nearest_point(self,p,o):
        return selection.nearest_point(p,o,self.doc.display_unit)

    def on_object(self,p,ids):
        candidates=[]; tolerance=9/self.scale
        for i in ids:
            o=self.objects[i]
            if selection.box_distance(p,self.object_bounds(o))>tolerance: continue
            q=self.nearest_point(p,o)
            if distance(p,q)<=tolerance:
                candidates.append((q,'on line' if o['type']=='line' else 'on curve'))
        return min(candidates,key=lambda v:distance(p,v[0]),default=None)

    def line_constraint_candidates(self,start,obj):
        if not hasattr(self,'_constraint_cache'): self._constraint_cache={}
        if len(self._constraint_cache)>2*len(self.objects)+32: self._constraint_cache.clear()
        key=(id(obj),tuple(start))
        cached=self._constraint_cache.get(key)
        if cached is None or cached[0] is not obj:
            points=[(q,mode) for mode in ('tangent','perpendicular')
                    for q in selection.constraint_points(start,obj,mode)]
            cached=(obj,points); self._constraint_cache[key]=cached
        return cached[1]

    def tracking_exclusions(self,ids):
        history=getattr(self,'snap_history',None)
        if not history: return []
        objects=[self.objects[i] for i in ids]
        return [p for p in history.points if any(
            hit_distance(p,o)<1e-8 or any(distance(p,q)<1e-8 for q,_ in anchors(o))
            for o in objects)]

    def line_guide_start(self):
        drag=getattr(self,'drag',None)
        if drag and drag['active']:
            points=self.doc.editable_point_selection()
            i=drag['owner'];keys=points.get(i,set())
            if len(drag['ids'])==1 and len(keys)==1 and self.objects[i]['type']=='line':
                return self.objects[i]['b' if 'a' in keys else 'a'], self.objects[i]
        if self.family.get()=='Lines' and self.tool.get() not in ('Two points','Connected points'):return None,None
        if self.family.get() in ('Lines','Arcs','Circles','Ovals','Polygons','Splines') and self.points:
            if self.family.get()=='Splines':return self.points[-1],None
            try:return self.field_point(0),None
            except (ValueError,KeyError,AttributeError):return self.points[0],None
        return None,None

    def intersection_points(self,a,b):
        cache=getattr(self,'_intersection_cache',None)
        if cache is None:cache=self._intersection_cache=OrderedDict()
        key=(id(a),id(b))
        record=cache.get(key)
        if record is None or record[:2]!=(a,b):
            record=(copy.deepcopy(a),copy.deepcopy(b),[p for _,_,p in crossings(a,b)])
            cache[key]=record
        cache.move_to_end(key)
        if len(cache)>2048:cache.popitem(last=False)
        return record[2]

    def snap_point(self,p,exclude=None):
        tolerance=9/self.scale
        def nearest(candidates):
            best=min(candidates,key=lambda v:distance(p,v[0]),default=None)
            return (list(best[0]),best[1]) if best and distance(p,best[0])<=tolerance else None
        excluded=set(exclude or [])
        if self.family.get()=='Modify': excluded.update(set(self.doc.editable_selection())|set(self.doc.editable_point_selection()))
        ids=[i for i in self.visible_ids() if i not in excluded]
        self._line_guides=(None,[])
        guide_projections=[]
        if self.snap.get():
            nearby=[self.objects[i] for i in ids if selection.box_distance(p,self.object_bounds(self.objects[i]))<=tolerance]
            start,original=self.line_guide_start()
            if start is not None:
                sources=[self.objects[i] for i in ids
                         if selection.box_distance(start,self.object_bounds(self.objects[i]))<=cad_guides.ENDPOINT_TOLERANCE]
                if original is not None:sources.append(original)
                cached=getattr(self,'_guide_direction_cache',None)
                if cached is None or cached[0]!=start or cached[1]!=sources:
                    cached=(list(start),copy.deepcopy(sources),cad_guides.directions(start,sources))
                    self._guide_direction_cache=cached
                guides=cached[2]
                self._line_guides=(start,guides)
                step=self.grid_spacing/self.grid_subdivisions if self.grid_snap.get() else None
                history=getattr(self,'snap_history',None)
                axes=history.guides(p,self.scale,self.tracking_exclusions(excluded)) if history else []
                guide_hits,guide_projections=cad_guides.targets(start,guides,p,tolerance,nearby,step,axes)
                best=nearest(guide_hits)
                if best:return best
                if self.family.get()=='Lines' or getattr(self,'drag',None):
                    best=nearest(candidate for obj in nearby for candidate in self.line_constraint_candidates(start,obj))
                    if best:return best
            best=nearest((q,'intersection') for i,a in enumerate(nearby) for b in nearby[i+1:]
                         for q in self.intersection_points(a,b))
            if best:return best
            candidates=[]
            for i in ids: candidates.extend(self.object_anchors(self.objects[i]))
            candidates.append(([0,0],'origin'))
            best=nearest(candidates)
            if best: return best
        if guide_projections and self.start is not None:
            guide_projections.extend(alignment_candidates(p,self.start))
        best=nearest(guide_projections)
        if best:return best
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
                if self.objects[i]['type']=='line' and selection.box_distance(p,self.object_bounds(self.objects[i]))<=tolerance:
                    crossings.extend(line_grid_candidates(p,self.objects[i],step))
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
                d=min(d,distance(p,self.nearest_point(p,o)))
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
        return (self.nearest_point(p,self.objects[owner]),'on object') if self.snap.get() else (list(p),'')

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

    def leave_canvas(self,e):
        self.tracking_cursor=None
        self.cancel_snap_hover(); self.draw()

    def motion(self,e):
        if getattr(self,'_zoom_window',False):return
        self.mouse,self.marker=self.snap_point(self.world(e.x,e.y))
        if getattr(self,'_paste',None):
            self._paste['point']=list(self.mouse);self.marker=self.marker or 'paste anchor'
        self.track_snap_hover(e);self.draw()

    def click(self,e):
        self._recent_mouse_line=None
        self.cancel_snap_hover()
        self.canvas.focus_set(); raw=self.world(e.x,e.y)
        if getattr(self,'polar_window',None):
            point,_=self.snap_point(raw)
            for var,value in zip(self.polar_fields,point):var.set(format_value(value,self.polar_unit))
            return
        if getattr(self,'_zoom_window',False):
            self._view_box_start=raw;self._view_box_end=raw;self.draw();return
        if getattr(self,'_paste',None):
            try:
                point,label=self.snap_point(raw);cad_clipboard.place(self.doc,self._paste['snapshot'],point)
            except (ValueError,TypeError,KeyError,OverflowError) as ex:self.error(str(ex));return
            self.snap_history.clear();self.cancel();self.refresh_layers();return
        if self.family.get()=='Dimension':
            self.dimension_click(raw);return
        if self.family.get()=='Offset':
            self.offset_click(raw,e.state); return
        if self.family.get()=='Chamfer':
            self.chamfer_click(raw); return
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
                members=self.doc.group_members({i})
                for member in members:self.doc.point_selection.pop(member,None)
                if i in self.selected:self.selected.difference_update(members)
                else:self.selected.update(members)
            else:
                # Keep a picked point subset/group for a possible drag; a plain
                # click is promoted to whole-owner selection on button release.
                if i not in self.selected and not handle: self.selected=self.doc.group_members({i})
                source,label=(list(handle[3]),'control point') if handle else self.drag_handle(raw,i)
                ids=set(self.doc.editable_selection())|set(self.doc.editable_point_selection())
                self.drag={'owner':i,'raw':raw,'handle':source,'active':False,'ids':ids}
                self.mouse,self.marker=source,label
                self.track_snap_hover(e)
            self.draw(); return
        if self.family.get()=='Modify' and not (self.doc.editable_selection() or self.doc.editable_point_selection()):
            self.error('Select visible, unlocked geometry or control points first.'); return
        p,label=self.snap_point(raw)
        self.snap_history.remember(p,label)
        self.tracking_cursor=list(p)
        before=(copy.deepcopy(self.points),copy.deepcopy(self.refs),self.start)
        count=len(self.objects)
        try:
            self.pick(p,raw)
            if self.family.get()=='Lines' and self.tool.get() in ('Two points','Connected points'):
                if len(self.objects)>count:
                    self._recent_mouse_line=(len(self.objects)-1,self.objects[-1])
                    self.focus_parameter('length')
                elif len(self.points)==1:self.focus_parameter('x')
            elif self.tool.get()=='Center + diameter' and len(self.points)==1:
                self.focus_parameter('diameter')
        except (ValueError,KeyError) as ex:
            self.points,self.refs,self.start=before
            self.error(str(ex))
        self.draw()

    def dimension_click(self,raw):
        try:
            p,label=self.snap_point(raw)
            self.snap_history.remember(p,label)
            height=12/self.scale;spacing=32/self.scale
            if label in ('on line','on curve'):
                candidates=[self.objects[i] for i in self.visible_ids()
                            if self.objects[i]['type']!='dimension' and selection.box_distance(p,self.object_bounds(self.objects[i]))<=9/self.scale]
                obj=min(candidates,key=lambda o:distance(p,self.nearest_point(p,o)),default=None)
                if obj is None:raise ValueError('Pick a line, circle or arc.')
                dimensions=cad_dimensions.on_object(obj,p,spacing,height)
            else:
                if not label:raise ValueError('Pick a control or snap point.')
                if not self.points:
                    self.points=[list(p)];self.start=list(p);self.draw();return
                dimensions=cad_dimensions.between(self.points[0],p,spacing,height)
            self.doc.add_dimensions(dimensions)
            self.points=[];self.start=None;self.refresh_layers();self.draw()
        except (ValueError,KeyError) as ex:self.error(str(ex))

    def offset_indices(self):
        sources=getattr(self,'offset_sources',[])
        ids=[];lookup={id(o):i for i,o in enumerate(self.objects)}
        for source in sources:
            index=lookup.get(id(source))
            if index is None or not self.doc.visible(index) or source.get('locked',False):
                raise ValueError('An offset source changed or is hidden/locked. Select sources and activate Offset again.')
            ids.append(index)
        return ids

    def offset_click(self,raw,state=0):
        try:
            if not getattr(self,'offset_sources',[]) or state & 0x0001:
                i=self.hit(raw)
                if i is None: raise ValueError('Click a source curve first, or preselect a connected chain.')
                if self.objects[i].get('locked',False): raise ValueError('Choose an unlocked source.')
                if not any(o is self.objects[i] for o in getattr(self,'offset_sources',[])):
                    self.offset_sources=getattr(self,'offset_sources',[])+[self.objects[i]]
                self.selected=set(self.offset_indices());self.doc.point_selection={};self.offset_preview=[];self.draw();return
            point,label=self.snap_point(raw,exclude=self.offset_indices())
            self.set_point_fields(0,point);self.mouse=point;self.marker=label
            self.preview_offset()
        except (ValueError,KeyError) as ex:self.error(str(ex))

    def preview_offset(self):
        try:
            ids=self.offset_indices();v=self.values()
            self.offset_preview,self.offset_approximate=cad_offset.offset([self.objects[i] for i in ids],v['offset'],[v['x'],v['y']])
            self.draw()
        except Exception as ex:
            self.offset_preview=[];self.draw();self.error(str(ex))

    def apply_offset(self):
        try:
            ids=self.offset_indices();v=self.values()
            approximate=self.doc.offset_objects(ids,v['offset'],[v['x'],v['y']])
            self.remember_parameters(v)
            self.offset_preview=[];self.refresh_layers();self.draw()
            if approximate:
                messagebox.showinfo('Offset curves','Created a polyline approximation. Source curves were sampled with a 0.0001 inch chord criterion.',parent=self.root)
        except Exception as ex:self.error(str(ex))

    def chamfer_click(self,raw):
        try:
            radius=self.values()['radius']
            if not 1e-6<=radius<=1e7: raise ValueError('Enter a positive radius between 0.000001 and 10,000,000 inches.')
            hits=[(distance(raw,self.nearest_point(raw,o)),i)
                  for i,o in enumerate(self.objects) if self.doc.visible(i) and not o.get('locked',False)
                  and o['type'] in cad_chamfer.SUPPORTED
                  and selection.box_distance(raw,self.object_bounds(o))<=9/self.scale]
            d,index=min(hits,default=(float('inf'),None))
            if d>9/self.scale: return
            first=getattr(self,'chamfer_first',None)
            if first is None:
                self.chamfer_first=(self.objects[index],self.nearest_point(raw,self.objects[index]))
                self.selected={index}; self.doc.point_selection={}; self.draw(); return
            first_index=next((i for i,o in enumerate(self.objects) if o is first[0]),None)
            if first_index is None: self.chamfer_first=None; raise ValueError('The first segment changed. Choose it again.')
            if first_index==index: raise ValueError('Choose a different second segment.')
            self.doc.chamfer_objects(first_index,index,first[1],self.nearest_point(raw,self.objects[index]),radius)
            self.remember_parameters({'radius':radius})
            self.chamfer_first=None; self.mouse=None; self.marker=''; self.tracking_cursor=None
            self.refresh_layers(); self.draw()
        except (ValueError,KeyError) as ex: self.error(str(ex))

    def trim_click(self,raw):
        ids={i for i,o in enumerate(self.objects)
             if any(o is boundary for boundary in getattr(self,'trim_cutters',[])) and self.doc.visible(i)}
        if not ids:
            self.error('Select cutting boundaries, then choose Trim.'); return
        hits=[(distance(raw,self.nearest_point(raw,o)),i)
              for i,o in enumerate(self.objects)
              if i not in ids and self.doc.visible(i) and not o.get('locked',False)
              and selection.box_distance(raw,self.object_bounds(o))<=9/self.scale]
        d,i=min(hits,default=(float('inf'),None))
        if d>9/self.scale: return
        try:
            self.doc.trim_object(i,ids,self.nearest_point(raw,self.objects[i]))
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
        if getattr(self,'_zoom_window',False):
            if self._view_box_start is not None:self._view_box_end=self.world(e.x,e.y);self.draw()
            return
        if self.drag is not None:
            self.update_drag(e); self.draw()
        elif self.box_start is not None:
            self.cancel_snap_hover()
            self.box_end=self.world(e.x,e.y); self.draw()

    def release_select(self,e):
        if getattr(self,'_zoom_window',False):
            if self._view_box_start is None:return
            a=self._view_box_start;b=self.world(e.x,e.y)
            self._view_box_start=None;self._view_box_end=None
            if abs(a[0]-b[0])*self.scale>=4 and abs(a[1]-b[1])*self.scale>=4:
                self.cancel_window_zoom(draw=False);self.zoom_to_box(a,b)
            else:self.draw()
            return
        if self.drag is not None:
            self.update_drag(e)
            if self.drag['active']:
                if self.drag_error: self.error(self.drag_error)
                else: self.doc.commit_updates(self.drag_preview)
            else:
                self.selected=self.doc.group_members({self.drag['owner']})
            self.drag=None; self.drag_preview={}; self.drag_error=''; self.start=None
            self.draw(); return
        if self.box_start is None: return
        a=self.box_start; b=self.world(e.x,e.y)
        if distance(a,b)*self.scale>4:
            self.doc.select_window(a,b,extend=self.box_extend)
        self.box_start=None; self.box_end=None; self.draw()

    def double_click(self,e):
        if getattr(self,'polar_window',None):return
        if getattr(self,'_zoom_window',False) or getattr(self,'_paste',None):return
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
                    dx,dy=geo.sub(p,pivot); self.params['dx'].set(format_value(dx,self.doc.display_unit)); self.params['dy'].set(format_value(dy,self.doc.display_unit))
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
        if method=='Center + diameter': self.params['diameter'].set(format_value(2*distance(a,b),self.doc.display_unit))
        if method=='Offset from line':
            n=geo.normal(geo.unit(geo.sub(self.refs[0]['b'],self.refs[0]['a'])))
            self.params['offset'].set(format_value(geo.dot(geo.sub(b,self.refs[0]["a"]),n),self.doc.display_unit))
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

    def choose_pen_color(self):
        self.doc.set_layer_color(self.color.get())
        self.draw()

    def create_object(self,points):
        self._recent_mouse_line=None
        self.cancel_snap_hover()
        values=self.values();obj=construct(self.tool.get(),points,values,self.refs,self.clockwise.get())
        obj['color']=self.doc.layer_color(); self.doc.add([obj])
        self.remember_parameters(values,obj)
        end=list(points[-1]); connected=self.tool.get()=='Connected points'
        self.points=[end] if connected else []; self.refs=[None] if connected else []
        self.start=end if connected else None; self.mouse=None; self.marker=''
        if connected: self.set_point_fields(0,end)
        self.refresh_layers(); self.draw()

    def apply_parameters(self):
        for key in self.params:self.normalize_parameter(key)
        if self.family.get()=='Offset': self.apply_offset(); return
        if self.family.get()=='Chamfer':
            try:
                if not 1e-6<=self.values()['radius']<=1e7: raise ValueError('Enter a positive radius between 0.000001 and 10,000,000 inches.')
            except ValueError as ex: self.error(str(ex))
            return
        try:
            family=self.family.get(); method=self.tool.get(); v=self.values()
            if family=='Select': return
            if family=='Modify':
                self.doc.transform_selected(method,copy_objects=self.copy_mode.get(),pivot=[v['x'],v['y']],
                                            dx=v.get('dx',0),dy=v.get('dy',0),angle=v.get('angle',0),factor=v.get('factor',1))
                self.remember_parameters(v)
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
        self._recent_mouse_line=None
        self._line_guides=(None,[])
        self.close_polar()
        self._paste=None
        if hasattr(self,'canvas'):self.canvas.delete('paste-preview')
        self.cancel_window_zoom(draw=False)
        self.cancel_snap_hover()
        self.offset_sources=[];self.offset_preview=[]
        self.trim_cutters=[]; self.chamfer_first=None; self.tracking_cursor=None
        self.points=[]; self.refs=[]; self.start=None; self.mouse=None; self.marker=''
        self.box_start=None; self.box_end=None
        self.drag=None; self.drag_preview={}; self.drag_error=''
        self.draw()

    def error(self,text): messagebox.showerror('BrianCAD',text,parent=self.root)

    def prompt(self):
        if getattr(self,'_zoom_window',False):return 'Zoom window: drag an area; Esc/right-click cancels'
        if getattr(self,'_paste',None):return 'Paste: anchor follows cursor | click to place | Esc/right-click cancels'
        method=self.tool.get(); n=len(self.points)
        if self.family.get()=='Dimension':
            return 'Pick second snap point' if self.points else 'Pick two snap points, or an on-line/on-curve snap for a whole-object measurement'
        if self.family.get()=='Offset':
            return f'{len(getattr(self,"offset_sources",[]))} source curves | Set distance and direction X/Y; click side point; Apply offset'
        if self.family.get()=='Chamfer':
            return 'Pick second segment on the side to keep' if getattr(self,'chamfer_first',None) else 'Set Radius; pick first segment on the side to keep'
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
        if self.family.get()=='Dimension':
            return {'type':'line','a':self.points[0],'b':self.mouse} if self.points and self.mouse and distance(self.points[0],self.mouse)>geo.EPS else None
        if self.family.get()=='Offset': return None
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

    def object_path(self,o):
        if not hasattr(self,'_path_cache'):
            self._path_cache=OrderedDict();self._path_cache_points=0
        key=id(o);cached=self._path_cache.get(key)
        if cached is None or cached[0]!=o:
            if cached is not None:self._path_cache_points-=len(cached[1])
            cached=(copy.deepcopy(o),geo.path(o));self._path_cache[key]=cached
            self._path_cache_points+=len(cached[1])
        self._path_cache.move_to_end(key)
        while self._path_cache and (len(self._path_cache)>2*len(self.objects)+32 or self._path_cache_points>DISPLAY_PATH_POINT_LIMIT):
            _,removed=self._path_cache.popitem(last=False);self._path_cache_points-=len(removed[1])
        return cached[1]

    def render_geometry(self,visible):
        c=self.canvas
        records=getattr(self,'_rendered_objects',{})
        view=(self.scale,tuple(self.origin));previous=getattr(self,'_geometry_view',None)
        moved=previous is not None and previous!=view
        resized=previous is not None and previous[0]!=self.scale
        if moved and records:
            factor=self.scale/previous[0]
            c.scale('geometry',0,0,factor,factor)
            c.move('geometry',self.origin[0]-previous[1][0]*factor,self.origin[1]-previous[1][1]*factor)
        keep=set(visible);changed=False
        for i in list(records):
            if i not in keep:
                c.delete(*records.pop(i)[1]);changed=True
        for i in visible:
            obj=getattr(self,'drag_preview',{}).get(i,self.objects[i])
            chosen=i in self.selected;partial=self.doc.point_selection.get(i,set())
            state=(obj,chosen,partial,self.doc.display_unit if obj['type']=='dimension' else None);old=records.get(i)
            if old is None or old[0]!=state or (resized and obj['type']=='dimension'):
                if old is not None:c.delete(*old[1])
                tag=f'entity:{i}';weight=float(obj.get('weight',.01));width_tag='stroke:'+str(weight)
                item=self.draw_object(obj,color='#d08213' if chosen else None,tags=('geometry',tag,width_tag))
                items=item if isinstance(item,list) else [item];handles=[]
                if chosen or partial or obj.get('controls'):
                    for key,p in selection.controls(obj):
                        x,y=self.screen(p);selected=chosen or key in partial
                        item=c.create_rectangle(x-4,y-4,x+4,y+4,outline='#b66b00' if selected else '#708296',
                                                fill='#eaa23d' if selected else 'white',tags=('geometry',tag))
                        items.append(item);handles.append((item,list(p)))
                records[i]=(copy.deepcopy(state),items,handles,weight);changed=True
            elif moved:
                # Canvas.scale scales rectangle extents too: restore 8-pixel handles.
                for item,p in old[2]:
                    x,y=self.screen(p);c.coords(item,x-4,y-4,x+4,y+4)
        if moved:
            for weight in {record[3] for record in records.values()}:
                c.itemconfigure('stroke:'+str(weight),width=max(1,min(5,weight*self.scale)))
        if changed:
            # Recreated/new objects must retain the document's stacking order.
            for i in visible:c.tag_raise(f'entity:{i}')
        self._rendered_objects=records;self._geometry_view=view

    def draw_object(self,o,color=None,dash=None,tags=('overlay',)):
        if o['type']=='dimension':
            stroke=color or o.get('color',COLORS['Blue'])
            width=max(1,min(5,o.get('weight',.01)*self.scale))
            pattern=dash or {'Dashed':(6,4),'Dotted':(1,3)}.get(o.get('pattern'))
            items=[]
            for path in cad_dimensions.layout(o,self.doc.display_unit):
                opts=dict(fill=stroke,width=width,tags=tags)
                if pattern:opts['dash']=pattern
                items.append(self.canvas.create_line(*[v for p in path for v in self.screen(p)],**opts))
            # Keep text off stroke-width tags; Canvas text's width means wrapping.
            text_tags=tuple(t for t in tags if not t.startswith(('stroke:','paste-stroke:')))
            items.append(self.canvas.create_text(*self.screen(o['label']),text=cad_dimensions.text(o,self.doc.display_unit),
                fill=stroke,font=(self.snap_label_font.cget('family'),-max(2,min(4096,round(o['text_height']*self.scale)))),tags=text_tags))
            return items
        pts=self.object_path(o); coords=[v for p in pts for v in self.screen(p)]
        pattern=dash or {'Solid':None,'Dashed':(6,4),'Dotted':(1,3)}.get(o.get('pattern','Solid'))
        width=max(1,min(5,o.get('weight',.01)*self.scale))
        opts={'fill':color or o.get('color',COLORS['Black']),'width':width,'tags':tags}
        if pattern: opts['dash']=pattern
        return self.canvas.create_line(*coords,**opts)

    def draw(self):
        if not hasattr(self,'canvas'): return
        self.sync_units()
        if hasattr(self,'color'):
            color=self.doc.layer_color()
            if self.color.get()!=color:self.color.set(color)
        w=self.canvas.winfo_width(); h=self.canvas.winfo_height()
        self.canvas.delete('overlay')
        grid_key=(w,h,tuple(self.origin),self.scale,self.grid.get(),self.grid_spacing,self.grid_subdivisions)
        if grid_key!=getattr(self,'_grid_render_key',None):
            self.canvas.delete('background'); c=CanvasLayer(self.canvas,'background')
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
            self._grid_render_key=grid_key
        major_visible=self.grid_spacing*self.scale>=8
        minor_visible=self.grid_subdivisions>1 and self.grid_spacing/self.grid_subdivisions*self.scale>=8
        low=self.world(-10,h+10); high=self.world(w+10,-10)
        def in_view(i):
            o=getattr(self,'drag_preview',{}).get(i,self.objects[i])
            if i in self.selected or self.doc.point_selection.get(i) or o.get('controls'): return True
            box=self.object_bounds(o)
            return box[2]>=low[0] and box[0]<=high[0] and box[3]>=low[1] and box[1]<=high[1]
        visible=[i for i in self.visible_ids() if in_view(i)]
        self.render_geometry(visible)
        self.canvas.tag_lower('background')
        self.render_paste_preview()
        c=CanvasLayer(self.canvas,'overlay')
        if self.tool.get()=='Start tangent + end' and len(self.points)>=2:
            try:
                c.create_line(*self.screen(self.field_point(0)),*self.screen(self.field_point(1)),
                              fill='#9dbcd5',dash=(3,5),tags=('tangent-guide',))
            except (ValueError,KeyError): pass
        for obj in getattr(self,'offset_preview',[]): self.draw_object(obj,color='#708296',dash=(5,3))
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
        guide_start,guide_vectors=getattr(self,'_line_guides',(None,[]))
        if guide_start is not None and self.snap.get() and self.line_guide_start()[0] is not None:
            extent=max(distance(guide_start,self.world(x,y)) for x,y in ((0,0),(w,0),(0,h),(w,h)))
            for vector,label in guide_vectors:
                delta=geo.mul(vector,extent)
                c.create_line(*self.screen(geo.sub(guide_start,delta)),*self.screen(geo.add(guide_start,delta)),
                              fill='#7693a7' if label in ('extension guide','tangent guide') else '#a38bb1',dash=(2,5),tags=('line-guide',))
        history=getattr(self,'snap_history',None)
        excluded=(set(self.doc.editable_selection())|set(self.doc.editable_point_selection())) if self.family.get()=='Modify' else set()
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
        if getattr(self,'_view_box_start',None) is not None and self._view_box_end is not None:
            c.create_rectangle(*self.screen(self._view_box_start),*self.screen(self._view_box_end),
                               outline='#397cc1',dash=(4,3),tags=('zoom-window',))
        hidden=' (dense lines hidden)' if self.grid.get() and (not major_visible or (self.grid_subdivisions>1 and not minor_visible)) else ''
        pos='' if self.mouse is None else f' | X {display_value(self.mouse[0],self.doc.display_unit):.4f} Y {display_value(self.mouse[1],self.doc.display_unit):.4f} {self.doc.display_unit}'
        point_count=sum(len(keys) for keys in self.doc.point_selection.values())
        self.status.set(f'{self.tool.get()}  |  {self.prompt()} | {len(self.selected)} objects + {point_count} handles selected | grid {format_value(self.grid_spacing,self.doc.display_unit)}/{self.grid_subdivisions} {self.doc.display_unit}{hidden}{pos}')
        self.layer_status.set('Active layer: '+self.doc.active)
        self.root.title((' |  ' if self.doc.dirty else '')+'BrianCAD - '+(os.path.basename(self.path) if self.path else 'Untitled'))
        if getattr(self,'edit_window',None) is not None: self.refresh_edit()

    def text_clipboard(self,action):
        widget=self.root.focus_get()
        if widget is not None and widget.winfo_class() in ('Entry','TEntry','Text','TCombobox'):
            widget.event_generate('<<'+action+'>>');return True
        return False

    def copy_objects(self):
        if self.text_clipboard('Copy'):return
        try:
            data=cad_clipboard.snapshot(self.doc,set(self.selected)|set(self.doc.point_selection),self.mouse)
            text=cad_clipboard.encode(data);self.root.clipboard_clear();self.root.clipboard_append(text)
        except (ValueError,TypeError,KeyError,tk.TclError) as ex:self.error(str(ex))

    def paste_objects(self):
        if self.text_clipboard('Paste'):return
        try:data=cad_clipboard.decode(self.root.clipboard_get())
        except (ValueError,tk.TclError) as ex:self.error(str(ex));return
        point=list(self.mouse) if self.mouse is not None else self.world(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2)
        self.return_to_select()
        self._paste={'snapshot':data,'point':point,'rendered':False}
        self.mouse=point;self.marker='paste anchor';self.draw()

    def render_paste_preview(self):
        session=getattr(self,'_paste',None)
        if not session:return
        c=self.canvas;point=session['point'];view=(self.scale,tuple(self.origin))
        if (session['rendered'] and (session['view'][0]!=self.scale or session.get('unit')!=self.doc.display_unit)
                and any(o['type']=='dimension' for o in session['snapshot']['drawing']['objects'])):
            c.delete('paste-preview');session['rendered']=False
        session['unit']=self.doc.display_unit
        if not session['rendered']:
            objects=session['snapshot']['drawing']['objects'];session['weights']={float(o['weight']) for o in objects}
            for obj in objects:
                self.draw_object(obj,color='#708296',dash=(5,3),tags=('paste-preview','paste-stroke:'+str(float(obj['weight']))))
            dx,dy=geo.sub(point,session['snapshot']['anchor']);c.move('paste-preview',dx*self.scale,-dy*self.scale)
            session['rendered']=True
        else:
            old_scale,old_origin=session['view'];factor=self.scale/old_scale
            if factor!=1:c.scale('paste-preview',0,0,factor,factor)
            dx,dy=geo.sub(point,session['last_point'])
            c.move('paste-preview',self.origin[0]-old_origin[0]*factor+dx*self.scale,
                   self.origin[1]-old_origin[1]*factor-dy*self.scale)
            if factor!=1:
                for weight in session['weights']:c.itemconfigure('paste-stroke:'+str(weight),width=max(1,min(5,weight*self.scale)))
        session['view']=view;session['last_point']=list(point);c.tag_raise('paste-preview')

    def flip_selection(self,horizontal):
        try:
            ids=self.doc.editable_selection()
            if not ids:raise ValueError('Select at least one visible, unlocked object.')
            boxes=[self.object_bounds(self.objects[i]) for i in ids]
            pivot=[(min(b[k] for b in boxes)+max(b[k+2] for b in boxes))/2 for k in (0,1)]
            self.doc.transform_selected('Mirror',pivot=pivot,angle=90 if horizontal else 0)
            self.cancel()
        except ValueError as ex:self.error(str(ex))

    def close_polar(self,event=None):
        dlg=getattr(self,'polar_window',None)
        self.polar_window=None
        if dlg is not None and dlg.winfo_exists():dlg.destroy()
        return 'break'

    def polar_dialog(self):
        existing=getattr(self,'polar_window',None)
        if existing is not None and existing.winfo_exists():existing.lift();return
        ids=self.doc.editable_selection()
        if not ids:self.error('Select at least one visible, unlocked object.');return
        self.cancel()
        document=self.doc;originals=[self.objects[i] for i in ids];unit=document.display_unit
        dlg=tk.Toplevel(self.root);self.polar_window=dlg;dlg.title('Polar Duplicate');dlg.transient(self.root);dlg.resizable(False,False)
        frame=ttk.Frame(dlg,padding=14);frame.pack()
        self.polar_fields=[tk.StringVar(value=v) for v in ('0','0','4')]
        self.polar_unit=unit
        for row,(label,var) in enumerate(zip((f'Center X ({unit})',f'Center Y ({unit})','Total (including original)'),self.polar_fields)):
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',padx=(0,8),pady=3)
            ttk.Entry(frame,textvariable=var,width=14).grid(row=row,column=1)
        ttk.Label(frame,text='Click the drawing to pick the center. Copies are spaced over 360°.',wraplength=300).grid(row=3,columnspan=2,pady=8)
        def apply(event=None):
            try:
                if self.doc is not document or self.doc.editable_selection()!=ids or any(self.objects[i] is not o for i,o in zip(ids,originals)):
                    raise ValueError('The source selection changed. Reopen Polar Duplicate.')
                center=[parse_number(v.get(),unit) for v in self.polar_fields[:2]]
                self.doc.polar_duplicate(center,self.polar_fields[2].get())
            except ValueError as ex:
                messagebox.showerror('Polar Duplicate',str(ex),parent=dlg);return 'break'
            self.cancel();return 'break'
        ttk.Button(frame,text='Cancel',command=self.close_polar).grid(row=4,column=0)
        ttk.Button(frame,text='Apply',command=apply).grid(row=4,column=1)
        dlg.protocol('WM_DELETE_WINDOW',self.close_polar)
        dlg.bind('<Escape>',self.close_polar);dlg.bind('<Return>',apply)

    def divide_dialog(self):
        existing=getattr(self,'divide_window',None)
        if existing is not None and existing.winfo_exists():existing.lift();return
        ids=self.doc.group_members(set(self.selected)|set(self.doc.point_selection))
        if not ids:self.error('Select at least one object to divide.');return
        originals={i:self.objects[i] for i in ids};document=self.doc
        dlg=tk.Toplevel(self.root);self.divide_window=dlg;dlg.title('Divide objects');dlg.transient(self.root);dlg.resizable(False,False)
        frame=ttk.Frame(dlg,padding=14);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=f'Divide each of {len(ids)} selected objects independently.').grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,8))
        ttk.Label(frame,text='Number of segments').grid(row=1,column=0,sticky='w',padx=(0,10))
        count=tk.StringVar(value='2');self.divide_count=count
        entry=ttk.Entry(frame,textvariable=count,width=12);entry.grid(row=1,column=1,sticky='ew')
        ttk.Label(frame,text='Equal lengths along each object. Curves remain curved.\nMulti-span spline sections select as independent groups.',wraplength=370).grid(row=2,column=0,columnspan=2,sticky='w',pady=10)
        def close(event=None):dlg.destroy();return 'break'
        def apply(event=None):
            try:
                if self.doc is not document or any(i>=len(self.objects) or self.objects[i] is not o for i,o in originals.items()):
                    raise ValueError('The selected objects changed. Close Divide and select them again.')
                self.doc.divide_objects(ids,count.get())
            except (ValueError,TypeError,KeyError,OverflowError) as ex:
                messagebox.showerror('Divide objects',str(ex),parent=dlg);return 'break'
            dlg.destroy();self.snap_history.clear();self.cancel();self.refresh_layers();return 'break'
        ttk.Button(frame,text='Cancel',command=close).grid(row=3,column=0,pady=(4,0))
        ttk.Button(frame,text='Apply',command=apply).grid(row=3,column=1,pady=(4,0))
        dlg.bind('<Return>',apply);dlg.bind('<Escape>',close);dlg.protocol('WM_DELETE_WINDOW',close)
        dlg.grab_set();entry.focus_set();entry.selection_range(0,'end')

    def group_selected(self):
        try:self.doc.group_selection();self.cancel()
        except ValueError as ex:self.error(str(ex))

    def ungroup_selected(self):
        try:self.doc.ungroup_selection();self.cancel()
        except ValueError as ex:self.error(str(ex))

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

    def zoom_center(self,factor):
        self.zoom(SimpleNamespace(x=self.canvas.winfo_width()/2,y=self.canvas.winfo_height()/2),factor)

    def begin_window_zoom(self):
        self.cancel_snap_hover();self._zoom_window=True
        self._view_box_start=None;self._view_box_end=None
        self.drag=None;self.drag_preview={};self.box_start=None;self.box_end=None
        self.mouse=None;self.marker='';self.tracking_cursor=None
        self.canvas.configure(cursor='crosshair');self.canvas.focus_set();self.draw()

    def cancel_window_zoom(self,draw=True):
        active=getattr(self,'_zoom_window',False)
        self._zoom_window=False;self._view_box_start=None;self._view_box_end=None
        if active:
            self.canvas.configure(cursor='arrow')
            if draw:self.draw()

    def zoom_to_box(self,a,b):
        low=[min(a[k],b[k]) for k in (0,1)];high=[max(a[k],b[k]) for k in (0,1)]
        w=self.canvas.winfo_width();h=self.canvas.winfo_height()
        self.scale=max(.01,min(100000,(w-40)/max(high[0]-low[0],1e-9),(h-40)/max(high[1]-low[1],1e-9)))
        self.origin=[w/2-(low[0]+high[0])*self.scale/2,h/2+(low[1]+high[1])*self.scale/2];self.draw()

    def zoom(self,e,factor):
        self.cancel_window_zoom(draw=False)
        self.tracking_cursor=None
        self.cancel_snap_hover()
        p=self.world(e.x,e.y); self.scale=max(.01,min(100000,self.scale*factor))
        self.origin=[e.x-p[0]*self.scale,e.y+p[1]*self.scale]; self.motion(e)
    def pan_start(self,e):
        self.cancel_window_zoom(draw=False)
        self.tracking_cursor=None
        self.cancel_snap_hover(); self.pan=[e.x,e.y]; self.draw()
    def pan_move(self,e):
        self.cancel_snap_hover()
        if self.pan:
            self.origin[0]+=e.x-self.pan[0]; self.origin[1]+=e.y-self.pan[1]
            self.pan=[e.x,e.y]; self.draw()
    def fit(self):
        self.cancel_window_zoom(draw=False)
        self.root.update_idletasks()
        boxes=[self.object_bounds(self.objects[i]) for i in self.visible_ids()]
        if not boxes: return
        low=[min(box[k] for box in boxes) for k in (0,1)];high=[max(box[k+2] for box in boxes) for k in (0,1)]
        w=max(100,self.canvas.winfo_width()); h=max(100,self.canvas.winfo_height())
        self.scale=min((w-80)/max(high[0]-low[0],.5),(h-80)/max(high[1]-low[1],.5))
        self.origin=[w/2-(low[0]+high[0])*self.scale/2,h/2+(low[1]+high[1])*self.scale/2]; self.draw()

    def normalize_parameter(self,key):
        try:
            unit=self.doc.display_unit
            self.params[key].set(format_value(parse_number(self.params[key].get(),unit,field_kind(key)),unit,field_kind(key)))
        except (ValueError,KeyError):pass  # Incomplete input is reported on Apply, not on each keystroke.

    def sync_units(self):
        unit=self.doc.display_unit;old=getattr(self,'_parameter_unit',unit)
        if old!=unit:
            for key,var in self.params.items():
                try:var.set(format_value(parse_number(var.get(),old,field_kind(key)),unit,field_kind(key)))
                except ValueError:pass
        self._parameter_unit=unit
        if hasattr(self,'parameter_frame'):self.parameter_frame.configure(text=f'Drawing parameters | {UNITS[unit][0].lower()} ({unit})')

    def change_units(self,unit):
        old=self.doc.display_unit
        if unit==old:return
        parameters={key:format_value(parse_number(var.get(),old,field_kind(key)),unit,field_kind(key)) for key,var in self.params.items()}
        pending={}
        if getattr(self,'edit_window',None) is not None and self.edit_window.winfo_exists() and self.edit_matches():
            for key in self._edit_dirty:
                text=self.edit_fields[key].get()
                if text.strip() and self._edit_originals:
                    obj=cad_properties.apply_changes(self._edit_originals[0],{key:text},old)
                    pending[key]=cad_properties.display(cad_properties.values(obj,unit)[key],cad_properties.schema(obj)[key][1])
                else:pending[key]=text
        self.doc.set_display_unit(unit)
        for key,text in parameters.items():self.params[key].set(text)
        self._parameter_unit=unit
        if getattr(self,'edit_window',None) is not None and self.edit_window.winfo_exists():
            self.refresh_edit()
            for key,text in pending.items():
                if key in self.edit_fields:self.edit_fields[key].set(text)
        self.draw()

    def units_dialog(self):
        existing=getattr(self,'units_window',None)
        if existing is not None and existing.winfo_exists():existing.lift();return
        dlg=tk.Toplevel(self.root);self.units_window=dlg;dlg.title('Drawing units');dlg.transient(self.root);dlg.resizable(False,False)
        frame=ttk.Frame(dlg,padding=14);frame.pack(fill='both',expand=True)
        choices={f'{label} ({key})':key for key,(label,scale) in UNITS.items()}
        choice=tk.StringVar(value=next(label for label,key in choices.items() if key==self.doc.display_unit));self.unit_choice=choice
        ttk.Label(frame,text='Drawing units').grid(row=0,column=0,padx=(0,10))
        ttk.Combobox(frame,textvariable=choice,values=list(choices),state='readonly',width=25).grid(row=0,column=1)
        ttk.Label(frame,text='Changes displayed measurements and bare-number input.\nGeometry and major/minor grid keep their physical size.').grid(row=1,column=0,columnspan=2,pady=12)
        def close(e=None):dlg.destroy();return 'break'
        def apply(e=None):
            try:self.change_units(choices[choice.get()])
            except (ValueError,KeyError) as ex:messagebox.showerror('Drawing units',str(ex),parent=dlg);return 'break'
            return close()
        ttk.Button(frame,text='Cancel',command=close).grid(row=2,column=0)
        ttk.Button(frame,text='Apply',command=apply).grid(row=2,column=1)
        dlg.bind('<Return>',apply);dlg.bind('<Escape>',close);dlg.grab_set()

    def grid_dialog(self):
        dlg=tk.Toplevel(self.root); dlg.title('Grid'); dlg.transient(self.root); dlg.resizable(False,False)
        f=ttk.Frame(dlg,padding=16); f.pack()
        dialog_unit=self.doc.display_unit
        spacing=tk.StringVar(value=format_value(self.grid_spacing,dialog_unit)); divisions=tk.StringVar(value=str(self.grid_subdivisions))
        first=None
        for i,(label,var) in enumerate([(f'Grid spacing ({dialog_unit})',spacing),('# of subdivisions',divisions)]):
            ttk.Label(f,text=label).grid(row=i,column=0,padx=6,pady=5)
            e=ttk.Entry(f,textvariable=var,width=14); e.grid(row=i,column=1,pady=5)
            if first is None: first=e
        def apply():
            try: major,count=grid_values(parse_number(spacing.get(),dialog_unit),parse_number(divisions.get(),kind='scalar'))
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
        tree.grid(row=0,column=0,rowspan=6,sticky='nsew')
        f.columnconfigure(0,weight=1); f.rowconfigure(0,weight=1)
        rename=tk.StringVar(); ttk.Label(f,text='Layer name').grid(row=6,column=0,sticky='w',pady=(8,0))
        ttk.Entry(f,textvariable=rename).grid(row=7,column=0,sticky='ew')
        def selected_name():
            items=tree.selection()
            if not items: raise ValueError('Highlight a layer first.')
            return tree.item(items[0],'values')[-1]
        sort_reverse=None
        def refresh():
            keep=selected_name() if tree.selection() else self.doc.active
            if keep not in [l['name'] for l in self.doc.layers]: keep=self.doc.active
            tree.delete(*tree.get_children())
            rows=list(enumerate(self.doc.layers))
            if sort_reverse is not None:rows.sort(key=lambda item:layer_sort_key(item[1]['name']),reverse=sort_reverse)
            for i,l in rows:
                key=str(i); tree.insert('', 'end',iid=key,image=self.layer_icons[int(l['visible'])],values=('*' if l['name']==self.doc.active else '',l['name']))
                if l['name']==keep: tree.selection_set(key)
        self.layer_refresh=refresh
        def action(kind):
            try:
                name=selected_name() if kind!='new' else None
                if kind=='new': self.doc.add_layer(rename.get())
                elif kind=='duplicate':
                    target=self.doc.duplicate_layer(name);refresh()
                    row=str(next(i for i,l in enumerate(self.doc.layers) if l['name']==target))
                    tree.selection_set(row);tree.see(row);self.cancel();return
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
        for i,(label,kind) in enumerate([('New','new'),('Delete','delete'),('Show / Hide','hide'),('Set Layer','set'),('Rename','rename'),('Duplicate Layer','duplicate')]):
            ttk.Button(f,text=label,command=lambda k=kind:action(k)).grid(row=i,column=1,padx=(10,0),pady=4,sticky='ew')
        def highlight(e):
            if tree.selection(): rename.set(selected_name())
        def double(e):
            nonlocal sort_reverse
            column=tree.identify_column(e.x)
            if tree.identify_region(e.x,e.y)=='heading':
                if column=='#2':
                    current=[tree.item(row,'values')[-1] for row in tree.get_children()]
                    sort_reverse=current==sorted(current,key=layer_sort_key)
                    refresh()
                elif column=='#0':
                    self.doc.toggle_other_layers();refresh();self.cancel()
                return 'break'
            row=tree.identify_row(e.y)
            if row:
                tree.selection_set(row); action('hide' if tree.identify_column(e.x)=='#0' else 'set')
            return 'break'
        tree.bind('<<TreeviewSelect>>',highlight); tree.bind('<Double-1>',double)
        ttk.Label(f,text='Double-click row name: active; row eye: show/hide.\nDouble-click Layer header: sort/reverse; Eye header: isolate active/show all.').grid(row=8,column=0,columnspan=2,pady=8)
        refresh()

    def edit_dialog(self):
        if self.edit_window is not None and self.edit_window.winfo_exists():
            self.refresh_edit(); self.edit_window.lift(); return
        dlg=tk.Toplevel(self.root); self.edit_window=dlg; dlg.title('Edit objects'); dlg.transient(self.root)
        self.edit_frame=ttk.Frame(dlg,padding=14); self.edit_frame.pack(fill='both',expand=True)
        buttons=ttk.Frame(dlg,padding=(14,0,14,14)); buttons.pack(fill='x')
        ttk.Button(buttons,text='Close',command=self.close_edit).pack(side='right',padx=5)
        self.edit_apply=ttk.Button(buttons,text='Apply',command=self.apply_edit); self.edit_apply.pack(side='right')
        dlg.protocol('WM_DELETE_WINDOW',self.close_edit)
        dlg.bind('<Escape>',lambda e:(self.close_edit(),'break')[1])
        dlg.bind('<Return>',lambda e:self.apply_edit())
        self._edit_doc=None; self.refresh_edit()

    def close_edit(self):
        if self.edit_window is not None and self.edit_window.winfo_exists(): self.edit_window.destroy()
        self.edit_window=None; self._edit_doc=None; self._edit_originals=[]
        self.edit_fields={}; self.edit_widgets={}; self._edit_dirty=set()

    def edit_selection(self):
        return sorted(self.doc.group_members(i for i in set(self.selected)|set(self.doc.point_selection)
                      if 0<=i<len(self.objects) and self.doc.visible(i)))

    def edit_matches(self):
        ids=self.edit_selection()
        return (getattr(self,'_edit_doc',None) is self.doc and ids==self._edit_ids and getattr(self,'_edit_unit','in')==self.doc.display_unit
                and all(self.objects[i]==o for i,o in zip(ids,self._edit_originals)))

    def refresh_edit(self):
        if self.edit_window is None or not self.edit_window.winfo_exists(): return
        if self.edit_matches():
            layers=tuple(l['name'] for l in self.doc.layers)
            if layers!=self._edit_layers:
                self._edit_layers=layers
                if 'layer' in self.edit_widgets: self.edit_widgets['layer'].configure(values=('',)+layers)
            return
        self._edit_doc=self.doc; self._edit_ids=self.edit_selection();self._edit_unit=self.doc.display_unit
        self._edit_layers=tuple(l['name'] for l in self.doc.layers)
        self._edit_originals=[copy.deepcopy(self.objects[i]) for i in self._edit_ids]
        self._edit_dirty=set(); self.edit_fields={}; self.edit_widgets={}; self._edit_initial={}
        for widget in self.edit_frame.winfo_children(): widget.destroy()
        originals=self._edit_originals; shared=cad_properties.common(originals)
        title=('No objects selected' if not originals else originals[0]['type'].title() if len(originals)==1
               else f'{len(originals)} objects | mixed values are blank')
        group_ids={o.get('group') for o in originals}
        if originals and len(group_ids)==1 and None not in group_ids:
            title+=' | '+('closed group' if cad_groups.is_closed(originals) else 'open/disconnected group')
        ttk.Label(self.edit_frame,text=title,font=('',12,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,6))
        properties=[cad_properties.values(o,self.doc.display_unit) for o in originals]
        for row,(key,(label,kind)) in enumerate(shared.items(),1):
            vals=[v[key] for v in properties]
            text=cad_properties.display(vals[0],kind) if all(v==vals[0] for v in vals) else ''
            self._edit_initial[key]=text
            if key=='weight':label=f'Line width ({self.doc.display_unit})'
            ttk.Label(self.edit_frame,text=label).grid(row=row,column=0,sticky='w',padx=(0,12),pady=3)
            var=tk.StringVar(value=text); self.edit_fields[key]=var
            options=cad_properties.choices(key,self._edit_layers)
            if key=='weight':options=[format_value(float(value),self.doc.display_unit) for value in options]
            if key=='color': options+=sorted({v['color'] for v in properties if v['color'] not in options})
            widget=(ttk.Combobox(self.edit_frame,textvariable=var,values=['']+options,state='normal' if key in ('color','weight') else 'readonly',width=27)
                    if options is not None else ttk.Entry(self.edit_frame,textvariable=var,width=30))
            widget.grid(row=row,column=1,sticky='ew',pady=3); self.edit_widgets[key]=widget
            if kind in ('number','points'):widget.bind('<FocusOut>',lambda e,k=key:self.normalize_edit_field(k))
            var.trace_add('write',lambda *args,k=key:self.edit_changed(k))
        self.edit_length=tk.StringVar()
        ttk.Label(self.edit_frame,textvariable=self.edit_length).grid(row=len(shared)+1,column=0,columnspan=2,sticky='w',pady=8)
        if not originals:
            ttk.Label(self.edit_frame,text='Select objects on the canvas to edit their shared properties.').grid(row=2,column=0,columnspan=2,sticky='w')
        self.edit_apply.configure(state='normal' if originals else 'disabled')
        self.refresh_edit_length()

    def normalize_edit_field(self,key):
        try:
            text=self.edit_fields[key].get()
            if not text.strip() or not self._edit_originals:return
            kind=cad_properties.schema(self._edit_originals[0])[key][1]
            if kind=='number':value=format_value(parse_number(text,self.doc.display_unit,field_kind(key)),self.doc.display_unit,field_kind(key))
            else:
                obj=cad_properties.apply_changes(self._edit_originals[0],{key:text},self.doc.display_unit)
                value=cad_properties.display(cad_properties.values(obj,self.doc.display_unit)[key],kind)
            self.edit_fields[key].set(value)
        except (ValueError,KeyError,TypeError):pass

    def edit_changed(self,key):
        if self.edit_fields[key].get()!=self._edit_initial[key]: self._edit_dirty.add(key)
        else: self._edit_dirty.discard(key)
        self.refresh_edit_length()

    def proposed_edits(self):
        changes={key:self.edit_fields[key].get() for key in self._edit_dirty if self.edit_fields[key].get().strip()}
        return {i:self.doc.prepare(cad_properties.apply_changes(o,changes,self.doc.display_unit))
                for i,o in zip(self._edit_ids,self._edit_originals)}

    def refresh_edit_length(self):
        try:
            proposed=list(self.proposed_edits().values())
            dimensions=[o for o in proposed if o['type']=='dimension']
            if dimensions and len(dimensions)==len(proposed):
                self.edit_length.set(' | '.join(cad_dimensions.text(o,self.doc.display_unit) for o in dimensions[:4])+
                    (f' | +{len(dimensions)-4} more' if len(dimensions)>4 else ''))
                return
            approx=' (approx.)' if any(o['type'] in ('ellipse','spline') for o in proposed) else ''
            prefix='Length' if len(proposed)==1 else 'Selected total length'
            self.edit_length.set(f'{prefix}: {display_value(sum(geo.length(o) for o in proposed),self.doc.display_unit):.6g} {self.doc.display_unit}{approx}')
        except (ValueError,KeyError,TypeError,OverflowError):
            self.edit_length.set('Length: - (check entered values)')

    def apply_edit(self):
        if not self.edit_matches(): self.refresh_edit(); return
        try:
            updates=self.proposed_edits()
            self.doc.commit_updates(updates)
        except (ValueError,KeyError,TypeError,OverflowError) as ex:
            messagebox.showerror('Edit objects',str(ex),parent=self.edit_window); return
        self.doc.prune_selection(); self._edit_doc=None
        self.refresh_layers(); self.draw()

    def import_drawing(self):
        path=filedialog.askopenfilename(parent=self.root,title='Import into current drawing',
            filetypes=[('DXF or BrianCAD drawing','*.dxf *.json'),('DXF drawing','*.dxf'),('BrianCAD drawing','*.json')])
        if not path: return
        try:
            source,warnings=cad_import.read_drawing(path)
            count=cad_import.merge(self.doc,source)
        except Exception as ex:
            self.error('Could not import drawing:\n'+str(ex)); return
        if count:
            self.snap_history.clear(); self.cancel(); self.refresh_layers(); self.fit()
        messagebox.showinfo('Import drawing',f'Imported {count} objects into the current drawing.'+
                            ('\n\n'+'\n'.join(warnings) if warnings else ''),parent=self.root)

    def export_dxf_dialog(self):
        snapshot=cad_dxf.snapshot_drawing(self.doc)
        if not snapshot['objects']: self.error('The drawing is empty.'); return
        dlg=tk.Toplevel(self.root); dlg.title('Export DXF'); dlg.transient(self.root)
        self.export_window=dlg
        frame=ttk.Frame(dlg,padding=14); frame.pack(fill='both',expand=True)
        scope=tk.StringVar(value='all'); self.export_scope=scope
        ttk.Radiobutton(frame,text=f"Whole drawing ({len(snapshot['objects'])} objects)",
                        variable=scope,value='all').pack(anchor='w',pady=4)
        ttk.Radiobutton(frame,text=f"Selected objects ({len(snapshot['selected'])} objects)",variable=scope,
                        value='selected',state='normal' if snapshot['selected'] else 'disabled').pack(anchor='w',pady=4)
        ttk.Label(frame,text='Units: inches. Whole drawing includes hidden layers.').pack(anchor='w',pady=(8,2))
        ttk.Label(frame,text='Control-point selections export their entire objects.').pack(anchor='w',pady=(0,8))
        buttons=ttk.Frame(frame); buttons.pack(fill='x')
        def export():
            try: cad_dxf.require_ezdxf()
            except cad_dxf.DXFDependencyError as ex:
                messagebox.showerror('Export DXF',str(ex),parent=dlg); return
            stem=os.path.basename(self.path) if self.path else 'drawing'
            stem=stem[:-11] if stem.endswith('.draft.json') else os.path.splitext(stem)[0] if '.' in stem else stem
            path=filedialog.asksaveasfilename(parent=dlg,title='Export DXF',initialfile=stem+'.dxf',
                    defaultextension='.dxf',filetypes=[('DXF drawing','*.dxf')])
            if not path: return
            try: report=cad_dxf.export_dxf(path,snapshot,selected_only=scope.get()=='selected')
            except Exception as ex:
                messagebox.showerror('Export DXF','Could not export DXF:\n'+str(ex),parent=dlg); return
            dlg.destroy()
            text=f"Exported {report['objects']} objects to:\n{path}"
            if report['approximated']: text+=f"\n\n{report['approximated']} high-degree spline(s) exported as polylines (0.00001 inch tolerance)."
            messagebox.showinfo('Export DXF',text,parent=self.root)
        ttk.Button(buttons,text='Cancel',command=dlg.destroy).pack(side='right',padx=4)
        ttk.Button(buttons,text='Export...',command=export).pack(side='right',padx=4)
        dlg.bind('<Escape>',lambda e:dlg.destroy()); dlg.bind('<Return>',lambda e:export())
        dlg.grab_set()

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
            os.replace(temp,path); self.path=path; self.doc.saved=self.doc.state(); self.remember_drawing(path); self.draw()
        except (OSError,ValueError) as ex:
            if temp and os.path.exists(temp): os.unlink(temp)
            self.error(str(ex))
    def open(self,path=None):
        if not self.discard(): return
        path=path or filedialog.askopenfilename(filetypes=[('BrianCAD drawing','*.json')])
        if not path: return
        try:
            with open(path,encoding='utf-8') as f: doc=Document.from_payload(json.load(f))
            self.snap_history.clear(); self.doc=doc; self.path=path; self.cancel(); self.refresh_layers(); self.fit();self.remember_drawing(path)
        except (OSError,ValueError,TypeError,KeyError,OverflowError) as ex: self.error(str(ex))
    def close(self):
        if self.discard():
            self.cancel_snap_hover(); self.root.destroy()


if __name__=='__main__':
    root=tk.Tk(); Draft(root); root.mainloop()
