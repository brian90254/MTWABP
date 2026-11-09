"""Workspace styling, code-drawn tool icons, and optional dock/floating panels."""
import json
import math
import os
from pathlib import Path
import re
import tempfile
import tkinter as tk
from tkinter import ttk
from cad_recent import preferences_path

INK='#253447'
MUTED='#586779'
PANEL='#f4f6f9'
ACCENT='#285fba'


def setup_style(root):
    style=ttk.Style(root)
    # A built-in theme gives the same restrained styling without new dependencies.
    if 'clam' in style.theme_names():style.theme_use('clam')
    style.configure('TFrame',background=PANEL)
    style.configure('TLabel',background=PANEL,foreground=INK)
    style.configure('TLabelframe',background=PANEL)
    style.configure('TLabelframe.Label',background=PANEL,foreground=MUTED)
    style.configure('TButton',padding=(8,5),background='#e9eef5',foreground=INK,borderwidth=1,relief='flat')
    style.map('TButton',background=[('pressed','#cfddf0'),('active','#dce6f3')])
    style.configure('TCombobox',fieldbackground='white',background='#e9eef5')
    style.map('TCombobox',fieldbackground=[('readonly','white')])
    style.configure('TCheckbutton',background=PANEL,foreground=INK,padding=(0,3))
    style.configure('TRadiobutton',background=PANEL,foreground=INK)
    style.configure('TEntry',padding=4)
    style.configure('TCombobox',padding=3)
    style.configure('Heading.TLabel',font=(root.tk.call('font','actual','TkDefaultFont','-family'),11,'bold'),foreground=INK)
    style.configure('Muted.TLabel',foreground=MUTED)
    style.configure('Treeview',rowheight=26)
    style.configure('Treeview.Heading',padding=(5,6))
    style.layout('Tool.TRadiobutton',[('Radiobutton.padding',{'sticky':'nswe','children':[
        ('Radiobutton.label',{'sticky':'nswe'})]})])
    style.configure('Tool.TRadiobutton',padding=(7,6),anchor='w',background=PANEL,foreground=INK)
    style.map('Tool.TRadiobutton',background=[('selected','#dce8fb'),('active','#e8edf4')],
              foreground=[('selected','#174c9b')])
    return style


def tool_icon(root,family):
    scale=max(1,min(2,round(root.winfo_fpixels('1i')/96)))
    image=tk.PhotoImage(master=root,width=22*scale,height=22*scale)
    def line(points):
        for a,b in zip(points,points[1:]):
            steps=max(1,int(max(abs(b[0]-a[0]),abs(b[1]-a[1]))*scale*2))
            for i in range(steps+1):
                x=round((a[0]+(b[0]-a[0])*i/steps)*scale)
                y=round((a[1]+(b[1]-a[1])*i/steps)*scale)
                if 0<=x<22*scale and 0<=y<22*scale:
                    image.put(INK,to=(x,y,min(x+scale,22*scale),min(y+scale,22*scale)))
    def arc(cx,cy,rx,ry,start=0,sweep=2*math.pi):
        line([(cx+rx*math.cos(start+sweep*i/40),cy+ry*math.sin(start+sweep*i/40)) for i in range(41)])
    if family=='Select':line([(4,2),(4,17),(8,13),(12,20),(15,18),(11,11),(17,11),(4,2)])
    elif family=='Lines':line([(3,18),(18,3)]);line([(2,15),(2,19),(6,19)]);line([(15,2),(19,2),(19,6)])
    elif family=='Circles':arc(11,11,8,8)
    elif family=='Ovals':arc(11,11,9,5)
    elif family=='Arcs':arc(11,12,8,8,math.pi,math.pi*1.15);line([(2,10),(2,14),(6,14)])
    elif family=='Polygons':line([(3,7),(10,2),(18,7),(16,18),(6,18),(3,7)])
    elif family=='Splines':line([(2+i*.45,11+7*math.sin(i*math.pi/20)) for i in range(41)])
    elif family=='Dimension':
        line([(3,3),(3,18)]);line([(18,3),(18,18)]);line([(3,11),(18,11)])
        line([(6,8),(3,11),(6,14)]);line([(15,8),(18,11),(15,14)])
    elif family=='Trim':line([(2,18),(18,2)]);line([(3,5),(17,19)]);line([(3,15),(7,19)])
    elif family=='Chamfer':line([(3,20),(3,10)]);arc(11,10,8,8,math.pi,math.pi/2);line([(11,2),(20,2)])
    elif family=='Offset':line([(3,14),(11,6),(18,14)]);line([(3,20),(11,12),(18,20)])
    elif family=='Modify':
        line([(2,11),(20,11)]);line([(11,2),(11,20)])
        for p in [[(5,8),(2,11),(5,14)],[(17,8),(20,11),(17,14)],[(8,5),(11,2),(14,5)],[(8,17),(11,20),(14,17)]]:line(p)
    return image


class WorkspacePreferences:
    def __init__(self,path=None):
        self.path=Path(path) if path is not None else preferences_path().with_name('workspace.json')
        self.data={'width':400,'split':.48,'panels':{},'open':[]}
        try:
            data=json.loads(self.path.read_text())
            if isinstance(data,dict):
                if type(data.get('width')) is int:self.data['width']=max(320,min(720,data['width']))
                if isinstance(data.get('split'),(int,float)) and not isinstance(data['split'],bool) and math.isfinite(data['split']):
                    self.data['split']=max(.2,min(.8,data['split']))
                if isinstance(data.get('panels'),dict):
                    for key,value in data['panels'].items():
                        if key not in ('layers','properties') or not isinstance(value,dict):continue
                        item={'mode':'float' if value.get('mode')=='float' else 'dock'}
                        geometry=value.get('geometry')
                        if isinstance(geometry,str) and re.fullmatch(r'\d{2,4}x\d{2,4}[+-]\d{1,5}[+-]\d{1,5}',geometry):item['geometry']=geometry
                        self.data['panels'][key]=item
                if isinstance(data.get('open'),list):self.data['open']=[k for k in data['open'] if k in ('layers','properties')]
        except (OSError,ValueError,TypeError):pass

    def save(self):
        temporary=None
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile('w',dir=self.path.parent,delete=False) as f:
                temporary=f.name;json.dump(self.data,f)
            os.replace(temporary,self.path)
        except OSError:pass
        finally:
            if temporary and os.path.exists(temporary):
                try:os.unlink(temporary)
                except OSError:pass


class WorkspacePanels:
    def __init__(self,app,body,canvas_host):
        self.app=app;self.root=app.root;self.body=body;self.preferences=WorkspacePreferences()
        self.right=ttk.Panedwindow(body,orient='vertical',width=self.preferences.data['width']);self.panels={};self._jobs=set()
        self.root.bind('<Destroy>',self.destroy,add='+')
        body.add(canvas_host,weight=1)
        body.bind('<ButtonRelease-1>',lambda e:self.remember())
        body.bind('<Configure>',lambda e:self.schedule_restore())
        self.right.bind('<ButtonRelease-1>',lambda e:self.remember())

    def show(self,key):
        record=self.panels.get(key)
        if not record:return False
        if record['top'] is not None:record['top'].deiconify();record['top'].lift()
        else:
            self.ensure_dock()
            record['outer'].lift()
        return True

    def ensure_dock(self):
        if str(self.right) not in tuple(map(str,self.body.panes())):
            self.body.add(self.right,weight=0)
            self.schedule_restore()

    def schedule_restore(self):
        job=None
        def restore():
            self._jobs.discard(job);self.restore_width()
        job=self.root.after_idle(restore);self._jobs.add(job)

    def destroy(self,event):
        if event.widget is self.root:
            for job in self._jobs:
                try:self.root.after_cancel(job)
                except tk.TclError:pass
            self._jobs.clear()

    def restore_width(self):
        if not self.body.winfo_exists() or str(self.right) not in tuple(map(str,self.body.panes())):return
        width=self.body.winfo_width()
        if width>400:self.body.sashpos(0,max(200,width-self.preferences.data['width']))
        if len(self.right.panes())>1:
            self.right.sashpos(0,round(self.right.winfo_height()*self.preferences.data['split']))

    def create(self,key,title,on_close):
        saved=self.preferences.data['panels'].setdefault(key,{'mode':'dock'})
        top=None
        if saved['mode']=='float':
            top=tk.Toplevel(self.root);top.title(title);top.transient(self.root);top.minsize(320,240)
            geometry=saved.get('geometry','420x600+80+80')
            match=re.fullmatch(r'(\d+)x(\d+)([+-]\d+)([+-]\d+)',geometry)
            w,h,x,y=map(int,match.groups())
            sw,sh=self.root.winfo_screenwidth(),self.root.winfo_screenheight()
            top.geometry(f'{min(w,sw)}x{min(h,sh)}+{max(0,min(x,sw-160))}+{max(0,min(y,sh-120))}')
            top.protocol('WM_DELETE_WINDOW',on_close)
            outer=ttk.Frame(top);outer.pack(fill='both',expand=True)
        else:
            self.ensure_dock();outer=ttk.Frame(self.right);self.right.add(outer,weight=1)
        header=ttk.Frame(outer,padding=(10,7));header.pack(fill='x')
        ttk.Label(header,text=title,style='Heading.TLabel').pack(side='left')
        ttk.Button(header,text='Dock' if top else 'Float',command=lambda:self.app.toggle_panel(key)).pack(side='right')
        ttk.Button(header,text='Close',command=on_close).pack(side='right',padx=(0,4))
        scroll=ttk.Frame(outer);scroll.pack(fill='both',expand=True)
        canvas=tk.Canvas(scroll,highlightthickness=0,background=PANEL,width=380,height=260)
        bar=ttk.Scrollbar(scroll,orient='vertical',command=canvas.yview)
        bar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        canvas.configure(yscrollcommand=bar.set)
        content=ttk.Frame(canvas);window=canvas.create_window(0,0,anchor='nw',window=content)
        def size_content(event=None):
            canvas.itemconfigure(window,width=canvas.winfo_width(),
                                 height=max(canvas.winfo_height(),content.winfo_reqheight()))
            canvas.configure(scrollregion=canvas.bbox('all'))
        content.bind('<Configure>',size_content)
        canvas.bind('<Configure>',size_content)
        self.panels[key]={'outer':outer,'content':content,'top':top,'canvas':canvas,'bindings':{}}
        if top:top.bind('<Configure>',lambda e:self.capture_geometry(key) if e.widget is top else None)
        def wheel(event):
            if event.widget.winfo_class()=='TCombobox':return
            box=canvas.bbox('all')
            if not box or box[3]<=canvas.winfo_height():return
            amount=-1 if getattr(event,'num',None)==4 else 1 if getattr(event,'num',None)==5 else -int(event.delta/(1 if self.root.tk.call('tk','windowingsystem')=='aqua' else 120))
            if amount:canvas.yview_scroll(amount,'units')
            return 'break'
        for event in ('<MouseWheel>','<Button-4>','<Button-5>'):
            self.bind(key,event,wheel);canvas.bind(event,wheel)
        self.root.update_idletasks();self.restore_width();self.root.update_idletasks()
        return content

    def capture_geometry(self,key):
        record=self.panels.get(key)
        if record and record['top'] and record['top'].winfo_exists():
            self.preferences.data['panels'][key]['geometry']=record['top'].geometry()

    def bind(self,key,event,callback):
        tag=f'BrianCADPanel:{id(self)}:{key}'
        self.root.bind_class(tag,event,callback)
        self.panels[key]['bindings'][event]=callback
        self.rebind(key)

    def rebind(self,key):
        record=self.panels.get(key)
        if not record:return
        tag=f'BrianCADPanel:{id(self)}:{key}'
        def visit(widget):
            tags=widget.bindtags()
            if tag not in tags:widget.bindtags(tags[:2]+(tag,)+tags[2:])
            for child in widget.winfo_children():visit(child)
        visit(record['outer'])

    def remember(self,open_state=False):
        if str(self.right) in tuple(map(str,self.body.panes())):
            self.preferences.data['width']=max(320,min(720,self.body.winfo_width()-self.body.sashpos(0)))
            if len(self.right.panes())>1 and self.right.winfo_height()>0:
                self.preferences.data['split']=max(.2,min(.8,self.right.sashpos(0)/self.right.winfo_height()))
        for key in self.panels:self.capture_geometry(key)
        if open_state:self.preferences.data['open']=list(self.panels)
        self.preferences.save()

    def remove(self,key):
        record=self.panels.get(key)
        if not record:return
        self.remember();self.panels.pop(key)
        for event in record['bindings']:
            self.root.unbind_class(f'BrianCADPanel:{id(self)}:{key}',event)
        if record['top']:record['top'].destroy()
        else:self.right.forget(record['outer']);record['outer'].destroy()
        if not self.right.panes() and str(self.right) in tuple(map(str,self.body.panes())):self.body.forget(self.right)


class HoverHint:
    """A non-modal hint after one second of stationary hovering."""
    def __init__(self,widget,text,delay=1000):
        self.widget=widget;self.text=text;self.delay=delay;self.job=None;self.popup=None
        widget.bind('<Enter>',self.schedule,add='+')
        widget.bind('<Motion>',self.schedule,add='+')
        for event in ('<Leave>','<ButtonPress>','<Unmap>'):
            widget.bind(event,self.hide,add='+')
        widget.bind('<Destroy>',lambda e:self.hide() if e.widget is widget else None,add='+')

    def schedule(self,event=None):
        self.hide();self.job=self.widget.after(self.delay,self.show)

    def hide(self,event=None):
        if self.job is not None:
            try:self.widget.after_cancel(self.job)
            except tk.TclError:pass
            self.job=None
        if self.popup is not None:
            try:self.popup.destroy()
            except tk.TclError:pass
            self.popup=None

    def show(self):
        self.hide()
        if not self.widget.winfo_exists() or not self.widget.winfo_ismapped():return
        tip=tk.Toplevel(self.widget);self.popup=tip;tip.wm_overrideredirect(True)
        tk.Label(tip,text=self.text,background=INK,foreground='white',padx=9,pady=6).pack()
        tip.update_idletasks()
        x=min(self.widget.winfo_rootx(),tip.winfo_screenwidth()-tip.winfo_reqwidth()-8)
        y=self.widget.winfo_rooty()+self.widget.winfo_height()+5
        if y+tip.winfo_reqheight()>tip.winfo_screenheight():y=self.widget.winfo_rooty()-tip.winfo_reqheight()-5
        tip.geometry(f'+{max(0,x)}+{max(0,y)}')
