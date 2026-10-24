"""Drawing state, layers, validation, persistence, and atomic undo operations."""
import copy
import json
from cad_geometry import validate_geometry, transform
from cad_selection import controls, move_controls, wholly_inside, in_box

COLORS={'Black':'#202b36','Blue':'#2465d8','Green':'#198548','Red':'#c44236'}


def default_layers():
    return [{'name':n,'visible':True} for n in ['Constraints','Construction','Dimension','Layer1']]


class Document:
    def __init__(self):
        self.objects=[]; self.layers=default_layers(); self.active='Layer1'
        self.selected=set(); self.point_selection={}; self.history=[]; self.future=[]
        self.grid_spacing=1.; self.grid_subdivisions=4
        self.saved=self.state()

    def state(self):
        return copy.deepcopy({'objects':self.objects,'layers':self.layers,'active_layer':self.active,
                              'grid':{'spacing':self.grid_spacing,'subdivisions':self.grid_subdivisions}})

    @property
    def dirty(self): return self.state()!=self.saved

    def checkpoint(self):
        self.history.append(self.state()); self.future.clear()

    def restore(self,state):
        self.objects=copy.deepcopy(state['objects']); self.layers=copy.deepcopy(state['layers'])
        self.active=state['active_layer']; self.grid_spacing=state['grid']['spacing']
        self.grid_subdivisions=state['grid']['subdivisions']; self.clear_selection()

    def undo(self):
        if self.history:
            self.future.append(self.state()); self.restore(self.history.pop())

    def redo(self):
        if self.future:
            self.history.append(self.state()); self.restore(self.future.pop())

    def visible(self,index):
        return any(l['name']==self.objects[index].get('layer',self.active) and l['visible'] for l in self.layers)

    def editable_selection(self):
        return sorted(i for i in self.selected if self.visible(i) and not self.objects[i].get('locked',False))

    def clear_selection(self):
        self.selected=set(); self.point_selection={}

    def prune_selection(self):
        self.selected={i for i in self.selected if i<len(self.objects) and self.visible(i)}
        self.point_selection={i:set(keys)&{key for key,_ in controls(self.objects[i])}
                              for i,keys in self.point_selection.items()
                              if i<len(self.objects) and i not in self.selected and self.visible(i)}
        self.point_selection={i:keys for i,keys in self.point_selection.items() if keys}

    def select_window(self,a,b,extend=False):
        box=[min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])]
        if not extend: self.clear_selection()
        for i,obj in enumerate(self.objects):
            if not self.visible(i): continue
            if wholly_inside(obj,box):
                self.selected.add(i); self.point_selection.pop(i,None)
            elif i not in self.selected:
                keys={key for key,p in controls(obj) if in_box(p,box)}
                if keys: self.point_selection.setdefault(i,set()).update(keys)

    def editable_point_selection(self):
        return {i:keys for i,keys in self.point_selection.items()
                if i not in self.selected and self.visible(i) and not self.objects[i].get('locked',False)}

    def selection_updates(self,dx,dy):
        if abs(dx)<1e-12 and abs(dy)<1e-12: return {}
        updates={i:self.prepare(transform(self.objects[i],'Move',dx=dx,dy=dy))
                 for i in self.editable_selection()}
        for i,keys in self.editable_point_selection().items():
            updates[i]=self.prepare(move_controls(self.objects[i],keys,dx,dy))
        return updates

    def commit_updates(self,updates):
        pending={i:self.prepare(obj) for i,obj in updates.items()}
        if not any(obj!=self.objects[i] for i,obj in pending.items()): return False
        self.checkpoint()
        for i,obj in pending.items(): self.objects[i]=obj
        return True

    def move_selection(self,dx,dy):
        return self.commit_updates(self.selection_updates(dx,dy))

    def prepare(self,obj):
        n=copy.deepcopy(obj)
        n.setdefault('layer',self.active); n.setdefault('color',COLORS['Black'])
        n.setdefault('locked',False); n.setdefault('pattern','Solid'); n.setdefault('weight',.01)
        n.setdefault('controls',False)
        validate_geometry(n)
        if n['layer'] not in [l['name'] for l in self.layers]: raise ValueError('Unknown layer.')
        if n['color'] not in COLORS.values(): raise ValueError('Unknown pen color.')
        if n['pattern'] not in ['Solid','Dashed','Dotted']: raise ValueError('Unknown line pattern.')
        if isinstance(n['weight'],bool) or not isinstance(n['weight'],(int,float)) or not 0<n['weight']<=1:
            raise ValueError('Pen weight must be greater than zero and at most one inch.')
        if not isinstance(n['locked'],bool) or not isinstance(n['controls'],bool): raise ValueError('Invalid object flags.')
        return n

    def add(self,objects):
        pending=[self.prepare(o) for o in objects]
        if not pending: return
        # Drawing always targets a visible active layer.
        self.checkpoint()
        for l in self.layers:
            if l['name']==self.active: l['visible']=True
        start=len(self.objects); self.objects.extend(pending)
        self.selected=set(range(start,len(self.objects))); self.point_selection={}

    def chamfer_objects(self,first,second,click_first,click_second,radius):
        from cad_chamfer import chamfer
        if first==second: raise ValueError('Choose two different segments.')
        for index in (first,second):
            if not 0<=index<len(self.objects) or not self.visible(index) or self.objects[index].get('locked',False):
                raise ValueError('Choose visible, unlocked segments.')
        a,b,arc=chamfer(self.objects[first],self.objects[second],click_first,click_second,radius)
        for key in ('layer','color','pattern','weight','controls'):
            if key in self.objects[first]: arc[key]=self.objects[first][key]
        replacements={first:[self.prepare(o) for o in a],second:[self.prepare(o) for o in b]}
        arc=self.prepare(arc)
        pending=[]
        for i,obj in enumerate(self.objects): pending.extend(replacements[i] if i in replacements else [obj])
        pending.append(arc)
        self.checkpoint(); self.objects=pending
        self.selected={len(pending)-1}; self.point_selection={}
        return arc

    def trim_object(self,index,boundary_ids,click):
        from cad_trim import trim, BOUNDARIES
        ids={i for i in boundary_ids if 0<=i<len(self.objects) and self.visible(i)
             and self.objects[i]['type'] in BOUNDARIES}
        if not ids: raise ValueError('Select cutting boundaries, then choose Trim.')
        if index in ids: raise ValueError('Cutting boundaries cannot be trimmed while active.')
        if not self.visible(index) or self.objects[index].get('locked',False):
            raise ValueError('The trim target must be visible and unlocked.')
        pieces=[self.prepare(o) for o in trim(self.objects[index],
                                             [self.objects[i] for i in sorted(ids)],click)]
        self.checkpoint()
        self.objects[index:index+1]=pieces
        shift=len(pieces)-1
        def remap(i): return i if i<index else i+shift
        self.selected={remap(i) for i in self.selected if i!=index}
        self.point_selection={remap(i):keys for i,keys in self.point_selection.items() if i!=index}
        return pieces

    def edit(self,index,obj):
        n=self.prepare(obj)
        self.checkpoint(); self.objects[index]=n
        self.point_selection.pop(index,None)
        if not self.visible(index): self.selected.discard(index)

    def delete_selected(self):
        ids=set(self.editable_selection())
        if not ids: return
        self.checkpoint(); self.objects=[o for i,o in enumerate(self.objects) if i not in ids]; self.clear_selection()

    def transform_selected(self,mode,copy_objects=False,**kwargs):
        ids=self.editable_selection()
        if not ids: raise ValueError('Select at least one visible, unlocked object.')
        pending=[self.prepare(transform(self.objects[i],mode,**kwargs)) for i in ids]
        self.checkpoint()
        if copy_objects:
            start=len(self.objects); self.objects.extend(pending); self.selected=set(range(start,len(self.objects)))
        else:
            for i,o in zip(ids,pending): self.objects[i]=o
            self.selected=set(ids)

    def add_layer(self,name):
        name=name.strip()
        if not name or len(name)>100 or name in [l['name'] for l in self.layers]:
            raise ValueError('Choose a unique layer name of 1–100 characters.')
        self.checkpoint(); self.layers.append({'name':name,'visible':True})

    def rename_layer(self,old,new):
        new=new.strip()
        if old==new: return
        if not new or len(new)>100 or new in [l['name'] for l in self.layers]: raise ValueError('Choose a unique layer name of 1–100 characters.')
        if old not in [l['name'] for l in self.layers]: raise ValueError('Unknown layer.')
        self.checkpoint()
        for l in self.layers:
            if l['name']==old: l['name']=new
        for o in self.objects:
            if o['layer']==old: o['layer']=new
        if self.active==old: self.active=new

    def set_layer(self,name):
        if name not in [l['name'] for l in self.layers]: raise ValueError('Unknown layer.')
        self.checkpoint(); self.active=name
        for l in self.layers:
            if l['name']==name: l['visible']=True

    def toggle_layer(self,name):
        if name not in [l['name'] for l in self.layers]: raise ValueError('Unknown layer.')
        self.checkpoint()
        for l in self.layers:
            if l['name']==name: l['visible']=not l['visible']
        self.prune_selection()

    def delete_layer(self,name):
        if len(self.layers)==1: raise ValueError('Keep at least one layer.')
        if name not in [l['name'] for l in self.layers]: raise ValueError('Unknown layer.')
        target=next(l['name'] for l in self.layers if l['name']!=name)
        self.checkpoint()
        for o in self.objects:
            if o['layer']==name: o['layer']=target
        self.layers=[l for l in self.layers if l['name']!=name]
        if self.active==name: self.active=target
        self.prune_selection()

    def payload(self): return dict(self.state(),format='briancad-2',units='inches')

    @classmethod
    def from_payload(cls,data):
        if not isinstance(data,dict) or data.get('format') not in ['draft-prototype-1','briancad-2']:
            raise ValueError('Not a supported BrianCAD drawing.')
        d=cls()
        if data.get('units','inches')!='inches': raise ValueError('Drawing units must be inches.')
        layers=data.get('layers',default_layers())
        if not isinstance(layers,list) or not 1<=len(layers)<=1000: raise ValueError('Invalid layer list.')
        names=[]
        for l in layers:
            if not isinstance(l,dict) or not isinstance(l.get('name'),str) or not l['name'].strip() or len(l['name'])>100 or not isinstance(l.get('visible'),bool):
                raise ValueError('Invalid layer.')
            if l['name'] in names: raise ValueError('Duplicate layer name.')
            names.append(l['name'])
        d.layers=copy.deepcopy(layers); d.active=data.get('active_layer','Layer1' if 'Layer1' in names else names[0])
        if d.active not in names: raise ValueError('Active layer does not exist.')
        objs=data.get('objects')
        if not isinstance(objs,list) or len(objs)>100000: raise ValueError('Invalid object list.')
        if any(not isinstance(o,dict) for o in objs): raise ValueError('Invalid object.')
        d.objects=[d.prepare(o) for o in objs]
        grid=data.get('grid',{'spacing':1.,'subdivisions':4})
        from grid_snap import grid_values
        if not isinstance(grid,dict): raise ValueError('Invalid grid preferences.')
        d.grid_spacing,d.grid_subdivisions=grid_values(grid.get('spacing'),grid.get('subdivisions'))
        d.saved=d.state(); return d
