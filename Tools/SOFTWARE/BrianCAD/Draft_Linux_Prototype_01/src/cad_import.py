"""Parse imports before atomically merging geometry into an existing drawing."""
from collections import Counter
import copy
import json
import math
from pathlib import Path
from cad_document import Document, COLORS
from cad_dxf import require_ezdxf
import cad_geometry as g

TOLERANCE=1e-5  # inches for general DXF B-splines


def merge(document,source):
    """One undo step; preserve current filename, grid, active layer and saved state."""
    if not source.objects: return 0
    candidate=Document.from_payload(document.payload())
    used={o['layer'] for o in source.objects}
    names={l['name'] for l in candidate.layers}
    candidate.layers.extend(copy.deepcopy(l) for l in source.layers if l['name'] in used and l['name'] not in names)
    if len(candidate.layers)>1000: raise ValueError('Import would exceed 1000 layers.')
    pending=[candidate.prepare(o) for o in source.objects]
    if len(candidate.objects)+len(pending)>100000: raise ValueError('Import would exceed 100000 objects.')
    document.checkpoint(); start=len(document.objects)
    document.layers=candidate.layers; document.objects.extend(pending)
    document.selected={i for i in range(start,len(document.objects)) if document.visible(i)}
    document.point_selection={}
    return len(pending)


def read_drawing(path):
    if Path(path).suffix.lower()=='.dxf': return read_dxf(path)
    with open(path,encoding='utf-8') as f: source=Document.from_payload(json.load(f))
    return source,[]


def _pen(entity,layer,block_pen=None):
    from ezdxf.colors import aci2rgb
    aci=entity.dxf.get('color',256); rgb=entity.rgb; indexed=rgb is None
    if rgb is None:
        if aci==0 and block_pen: color=block_pen['color']
        elif aci in (0,7): color=COLORS['Black']
        else:
            if aci==256:
                aci=abs(layer.dxf.color); rgb=layer.rgb; indexed=rgb is None
            if rgb is None and aci==7: color=COLORS['Black']
            else: rgb=rgb or aci2rgb(aci)
    if rgb is not None:
        exact='#{:02x}{:02x}{:02x}'.format(*rgb)
        standard={1:'Red',2:'Yellow',3:'Green',4:'Cyan',5:'Blue',6:'Magenta',7:'Black'}
        if indexed and aci in standard: color=COLORS[standard[aci]]
        else: color=exact
    pattern=entity.dxf.get('linetype','BYLAYER').upper()
    if pattern=='BYLAYER': pattern=layer.dxf.linetype.upper()
    if pattern=='BYBLOCK' and block_pen: pattern=block_pen['pattern'].upper()
    pattern='Dotted' if 'DOT' in pattern else 'Dashed' if 'DASH' in pattern else 'Solid'
    weight=entity.dxf.get('lineweight',-1)
    if weight==-1: weight=layer.dxf.lineweight
    if weight==-2 and block_pen: return dict(color=color,pattern=pattern,weight=block_pen['weight'])
    return dict(color=color,pattern=pattern,weight=min(1,weight/2540) if weight>0 else .01)


def _geometry(e,scale):
    def xy(p):
        if abs(p.z*scale)>1e-7: raise ValueError('non-XY geometry')
        return [p.x*scale,p.y*scale]
    kind=e.dxftype()
    if kind=='LINE': return [{'type':'line','a':xy(e.dxf.start),'b':xy(e.dxf.end)}],False
    if kind in ('CIRCLE','ARC','ELLIPSE'):
        normal=e.dxf.extrusion
        if abs(normal.x)>1e-9 or abs(normal.y)>1e-9: raise ValueError('non-XY geometry')
    if kind in ('CIRCLE','ARC'):
        center=xy(e.ocs().to_wcs(e.dxf.center)); radius=e.dxf.radius*scale
        if kind=='CIRCLE': return [{'type':'circle','center':center,'radius':radius}],False
        start=g.angle(center,xy(e.start_point)); sweep=math.radians((e.dxf.end_angle-e.dxf.start_angle)%360)
        if not sweep: raise ValueError('zero-sweep arc')
        return [{'type':'arc','center':center,'radius':radius,'start':start,'sweep':sweep*(1 if normal.z>0 else -1)}],False
    if kind=='ELLIPSE':
        major=e.dxf.major_axis; center=xy(e.dxf.center); xy(major)
        start=e.dxf.start_param; sweep=(e.dxf.end_param-start)%g.TAU or g.TAU
        sign=1 if normal.z>0 else -1
        return [dict(type='ellipse',center=center,rx=major.magnitude*scale,ry=major.magnitude*scale*e.dxf.ratio,
                     angle=math.atan2(major.y,major.x),start=sign*start,sweep=sign*sweep)],False
    if kind in ('LWPOLYLINE','POLYLINE'):
        if kind=='POLYLINE' and not (e.is_2d_polyline or e.is_3d_polyline): raise ValueError('mesh polyline')
        if e.has_arc:
            objects=[]
            for part in e.virtual_entities(): objects.extend(_geometry(part,scale)[0])
            return objects,False
        if kind=='LWPOLYLINE': vertices=e.vertices_in_wcs()
        elif e.is_2d_polyline:
            vertices=(e.ocs().to_wcs((p.x,p.y,e.dxf.elevation.z)) for p in e.points())
        else: vertices=e.points()
        pts=[xy(p) for p in vertices]
        closed=e.closed if kind=='LWPOLYLINE' else e.is_closed
        if closed and len(pts)>1 and g.dist(pts[0],pts[-1])<g.EPS: pts.pop()
        if 3<=len(pts)<=200: return [dict(type='polygon',points=pts,closed=bool(closed))],False
        pairs=list(zip(pts,pts[1:]))
        if closed and len(pts)>1: pairs.append((pts[-1],pts[0]))
        return [dict(type='line',a=a,b=b) for a,b in pairs if g.dist(a,b)>=g.EPS],False
    if kind=='SPLINE':
        tool=e.construction_tool(); controls=list(tool.control_points); knots=list(tool.knots())
        degree=tool.degree
        if not tool.is_rational and len(controls)==degree+1 and degree<32 and knots==[knots[0]]*(degree+1)+[knots[-1]]*(degree+1):
            return [dict(type='spline',method='bezier',points=[xy(p) for p in controls],closed=False)],False
        pts=[]
        for p in tool.flattening(TOLERANCE/scale):
            q=xy(p)
            if not pts or g.dist(pts[-1],q)>=g.EPS: pts.append(q)
            if len(pts)>100001: raise ValueError('spline too complex')
        return [dict(type='line',a=a,b=b) for a,b in zip(pts,pts[1:])],True
    raise ValueError('unsupported entity')


def read_dxf(path):
    ezdxf=require_ezdxf()
    from ezdxf import units
    drawing=ezdxf.readfile(path); warnings=[]; skipped=Counter(); approximated=0
    code=drawing.units
    if code==0: scale=1.; warnings.append('DXF has no declared units; coordinates were interpreted as inches.')
    else: scale=units.conversion_factor(code,1)
    source=Document(); source.objects=[]; source.layers=[]; layer_names=set()
    def visit(entity,inherited_layer=None,block_pen=None,depth=0):
        nonlocal approximated
        if depth>32: skipped['INSERT (nesting limit)']+=1; return
        name=entity.dxf.get('layer','0')
        if name=='0' and inherited_layer is not None: name=inherited_layer
        try:
            layer=drawing.layers.get(name)
            pen=_pen(entity,layer,block_pen)
            if entity.dxftype()=='INSERT':
                if entity.mcount>1:
                    for instance in entity.multi_insert(): visit(instance,inherited_layer,block_pen,depth+1)
                else:
                    for part in entity.virtual_entities(skipped_entity_callback=lambda e,reason:skipped.update([e.dxftype()])):
                        visit(part,name,pen,depth+1)
                return
            objects,approx=_geometry(entity,scale)
            if not objects: return
            if name not in layer_names:
                if not name.strip() or len(name)>255: raise ValueError('unsupported layer name')
                source.layers.append(dict(name=name,visible=not layer.is_off() and not layer.is_frozen())); layer_names.add(name)
            prepared=[]
            for obj in objects: prepared.append(source.prepare(dict(obj,layer=name,**pen)))
            source.objects.extend(prepared); approximated+=int(approx)
            if len(source.objects)>100000: raise OverflowError('DXF exceeds 100000 imported objects.')
        except (ValueError,TypeError,AttributeError,IndexError,ZeroDivisionError,KeyError,ezdxf.DXFError) as ex:
            skipped[entity.dxftype()+' ('+str(ex)+')']+=1
    for entity in drawing.modelspace(): visit(entity)
    used={o['layer'] for o in source.objects}; source.layers=[l for l in source.layers if l['name'] in used]
    if source.layers: source.active=source.layers[0]['name']
    if skipped: warnings.append('Skipped entities: '+', '.join(f'{n} × {kind}' for kind,n in sorted(skipped.items())))
    if approximated: warnings.append(f'{approximated} general spline(s) converted to line segments (tolerance {TOLERANCE:g} inch).')
    return source,warnings
