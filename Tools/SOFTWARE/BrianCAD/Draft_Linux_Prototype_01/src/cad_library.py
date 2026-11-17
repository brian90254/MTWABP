"""DXF library thumbnails and repeat placement around the file's original origin."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import cad_geometry as geo
import cad_import
from cad_document import Document
from cad_units import parse_number,format_value

LIBRARY_DIR=Path(__file__).resolve().parent.parent/'LIBRARY'


def placed(source,point,angle):
    """Return an independent document rotated about DXF 0,0 then translated."""
    result=Document();result.layers=source.layers;result.active=source.active
    result.objects=[geo.transform(geo.transform(o,'Rotate',angle=angle),'Move',dx=point[0],dy=point[1]) for o in source.objects]
    return result


class LibraryMixin:
    def library_dialog(self):
        if self.panels.show('library'):return
        content=self.panels.create('library','Library',self.close_library)
        ttk.Label(content,text='Choose a DXF, click its origin location, then press Enter to place.',wraplength=300).pack(fill='x',padx=10,pady=8)
        ttk.Button(content,text='Refresh library',command=self.refresh_library).pack(anchor='w',padx=10)
        self.library_items=ttk.Frame(content);self.library_items.pack(fill='both',expand=True,padx=10,pady=8)
        self.refresh_library()
        self.panels.bind('library','<Escape>',lambda e:(self.cancel(),'break')[1])

    def close_library(self):
        self.panels.remove('library')

    def refresh_library(self):
        for child in self.library_items.winfo_children():child.destroy()
        paths=sorted(LIBRARY_DIR.glob('*'),key=lambda p:p.name.casefold())
        paths=[p for p in paths if p.is_file() and p.suffix.lower()=='.dxf']
        if not paths:ttk.Label(self.library_items,text='Add DXF files to the project LIBRARY folder.',wraplength=290).pack();return
        for path in paths:
            box=ttk.Frame(self.library_items);box.pack(fill='x',pady=5)
            try:
                source,warnings=cad_import.read_dxf(path)
                if not source.objects:raise ValueError('No supported geometry.')
                paths_=[geo.path(o) for o in source.objects]
                points=[p for line in paths_ for p in line]
                lo=[min(p[i] for p in points) for i in (0,1)];hi=[max(p[i] for p in points) for i in (0,1)]
                scale=min(140/max(hi[0]-lo[0],1e-8),80/max(hi[1]-lo[1],1e-8))
                center=[(a+b)/2 for a,b in zip(lo,hi)]
                icon=tk.Canvas(box,width=168,height=104,background='white',highlightthickness=1,highlightbackground='#bcc8d5',cursor='hand2',takefocus=True)
                icon.pack(anchor='center')
                for obj,line in zip(source.objects,paths_):
                    coords=[v for p in line for v in (84+(p[0]-center[0])*scale,52-(p[1]-center[1])*scale)]
                    if len(coords)>=4:icon.create_line(*coords,fill=obj.get('color','#222222'))
                action=lambda e=None,s=source,n=path.stem,w=warnings:self.begin_library(s,n,w)
                icon.bind('<Button-1>',action);icon.bind('<Return>',action);icon.bind('<space>',action)
                ttk.Button(box,text=path.stem,command=action).pack(fill='x')
                if warnings:ttk.Label(box,text='Import notes: '+'; '.join(warnings),wraplength=290).pack(fill='x')
            except Exception as ex:
                ttk.Label(box,text=path.name+'\n'+str(ex),wraplength=290,foreground='#a3342a').pack(fill='x')
        self.panels.rebind('library')

    def begin_library(self,source,name,warnings=()):
        self.return_to_select()
        self._library={'source':source,'name':name,'point':[0.,0.],'angle':0.,'fixed':False}
        self.snap_history.clear();self.configure_parameters();self.canvas.focus_set();self.draw()

    def library_parameters(self):
        self.tool_heading.set('Place library: '+self._library['name'])
        for widget in (self.method_box,self.direction_check,self.copy_check):widget.pack_forget()
        self.library_fields={};self.library_entries={};self.library_unit=self.doc.display_unit
        for i,(key,label,value) in enumerate([('x','Origin X',self._library['point'][0]),('y','Origin Y',self._library['point'][1]),('angle','Angle',self._library['angle'])]):
            cell=ttk.Frame(self.parameter_frame);cell.grid(row=0,column=i,padx=5,pady=3)
            ttk.Label(cell,text=label).pack(side='left',padx=(0,5))
            var=tk.StringVar(value=format_value(value,self.library_unit,'angle' if key=='angle' else 'length'))
            entry=ttk.Entry(cell,textvariable=var,width=12);entry.pack(side='left')
            self.library_fields[key]=var;self.library_entries[key]=entry
            entry.bind('<Return>',lambda e:(self.commit_library(),'break')[1])
            entry.bind('<FocusOut>',lambda e:self.update_library_fields())
            entry.bind('<KeyRelease>',lambda e:self.update_library_fields() if e.keysym not in ('Return','Escape','Tab') else None)
        ttk.Button(self.parameter_frame,text='Place copy',command=self.commit_library).grid(row=0,column=3,padx=8)
        self.library_error=tk.StringVar()
        self.library_error_label=ttk.Label(self.parameter_frame,textvariable=self.library_error,foreground='#a3342a')
        self.library_error_label.grid(row=1,column=0,columnspan=4,sticky='w',padx=5);self.library_error_label.grid_remove()

    def update_library_fields(self,report=False):
        if not getattr(self,'_library',None):return False
        try:
            x,y=[parse_number(self.library_fields[k].get(),self.library_unit) for k in ('x','y')]
            angle=parse_number(self.library_fields['angle'].get(),self.library_unit,'angle')
            if max(abs(x),abs(y))>1e7:raise ValueError('Placement coordinates are too large.')
        except ValueError as ex:
            if report:self.show_library_error(str(ex))
            return False
        self._library.update(point=[x,y],angle=angle);self.library_error.set('');self.library_error_label.grid_remove();self.draw();return True

    def show_library_error(self,text):
        self.library_error.set(text);self.library_error_label.grid()

    def library_motion(self,point):
        if self._library['fixed']:return
        # A focused numeric field owns its value until the canvas is clicked.
        if self.root.focus_get() in self.library_entries.values():return
        self._library['point']=list(point)
        for key,value in zip(('x','y'),point):self.library_fields[key].set(format_value(value,self.library_unit))

    def library_click(self,point):
        self._library['point']=list(point)
        for key,value in zip(('x','y'),point):self.library_fields[key].set(format_value(value,self.library_unit))
        self._library['fixed']=True
        entry=self.library_entries['angle'];entry.focus_set();entry.selection_range(0,'end');self.draw()

    def commit_library(self):
        if not self.update_library_fields(report=True):return
        session=self._library
        try:cad_import.merge(self.doc,placed(session['source'],session['point'],session['angle']))
        except (ValueError,TypeError,KeyError,OverflowError) as ex:self.show_library_error(str(ex));return
        session['fixed']=False;self.snap_history.clear();self.refresh_layers();self.canvas.focus_set();self.draw()

    def render_library_preview(self):
        session=getattr(self,'_library',None)
        if not session:return
        for obj in placed(session['source'],session['point'],session['angle']).objects:
            self.draw_object(obj,color='#708296',dash=(5,3))
        x,y=self.screen(session['point'])
        self.canvas.create_line(x-6,y,x+6,y,fill='#333333',tags=('overlay',))
        self.canvas.create_line(x,y-6,x,y+6,fill='#333333',tags=('overlay',))
