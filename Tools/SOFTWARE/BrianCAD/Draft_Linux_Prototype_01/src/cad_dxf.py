"""Read-only DXF export of BrianCAD geometry, with optional ezdxf dependency."""
import copy
import math
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
import cad_geometry as g
import cad_selection as selection
from curve_trim import split
from cad_document import COLORS

MAX_NATIVE_SPLINE_DEGREE=10  # compatible with ezdxf readers, including C extensions
FLATTEN_TOLERANCE=1e-5  # inches, for Béziers above common CAD degree limits


class DXFDependencyError(ImportError): pass


def require_ezdxf():
    try: import ezdxf
    except ImportError as ex:
        requirements=Path(__file__).resolve().parent.parent/'requirements-dxf.txt'
        command=f'{shlex.quote(sys.executable)} -m pip install -r {shlex.quote(str(requirements))}'
        raise DXFDependencyError('DXF export requires the optional ezdxf package. Install it for this Python interpreter:\n\n'+command) from ex
    return ezdxf


def snapshot_drawing(document):
    selected=sorted(i for i in set(document.selected)|set(document.point_selection) if 0<=i<len(document.objects))
    return copy.deepcopy({'objects':document.objects,'layers':document.layers,'selected':selected})


def _flatten_bezier(points,tolerance=FLATTEN_TOLERANCE):
    output=[list(points[0])]; stack=[(points,0)]
    while stack:
        span,depth=stack.pop()
        flat=max(g.dist(p,g.project(p,span[0],span[-1],True)) for p in span)
        if flat<=tolerance: output.append(list(span[-1])); continue
        if depth>=32 or len(stack)+len(output)>100000:
            raise ValueError('This high-degree spline is too complex to export within the DXF approximation tolerance.')
        left,right=split(span,.5); stack.extend([(right,depth+1),(left,depth+1)])
    return output


def _layer_names(document,layers):
    from ezdxf.lldxf.validator import is_valid_layer_name
    used={layer.dxf.name.casefold() for layer in document.layers}; result={}
    for layer in layers:
        original=layer['name']
        base=re.sub(r'[<>/\\":;?*|=\x00-\x1f\x7f]','_',original).strip()[:240] or 'Layer'
        if not is_valid_layer_name(base): base='Layer'
        name=base; suffix=2
        while name.casefold() in used and not (name=='0' and original=='0'):
            name=f'{base}_{suffix}'; suffix+=1
        used.add(name.casefold()); result[original]=name
        entry=document.layers.get(name) if name in document.layers else document.layers.new(name,dxfattribs={'color':7})
        if layer['visible']: entry.on()
        else: entry.off()
    return result


def _attributes(obj,layer_map):
    from ezdxf.lldxf.const import VALID_DXF_LINEWEIGHTS
    aci={COLORS['Black']:7,COLORS['Blue']:5,COLORS['Green']:3,COLORS['Red']:1}
    width=obj.get('weight',.01)*25.4*100
    return {'layer':layer_map[obj['layer']], 'color':aci.get(obj['color'],7),
            'true_color':int(obj['color'].lstrip('#'),16),
            'linetype':{'Solid':'CONTINUOUS','Dashed':'BRIANCAD_DASHED','Dotted':'BRIANCAD_DOTTED'}[obj['pattern']],
            'lineweight':min(VALID_DXF_LINEWEIGHTS,key=lambda v:abs(v-width))}


def _add_object(msp,obj,attrs):
    """Return whether this object's curve needed a polyline approximation."""
    kind=obj['type']
    if kind=='line': msp.add_line(obj['a'],obj['b'],dxfattribs=attrs)
    elif kind=='polygon': msp.add_lwpolyline(obj['points'],format='xy',close=obj.get('closed',True),dxfattribs=attrs)
    elif kind in ('circle','arc'):
        sweep=obj.get('sweep',g.TAU)
        if kind=='circle' or abs(sweep)>=g.TAU:
            msp.add_circle(obj['center'],obj['radius'],dxfattribs=attrs)
        else:
            start=obj['start'] if sweep>0 else obj['start']+sweep
            end=obj['start']+sweep if sweep>0 else obj['start']
            msp.add_arc(obj['center'],obj['radius'],math.degrees(start)%360,math.degrees(end)%360,dxfattribs=attrs)
    elif kind=='ellipse':
        rx,ry,angle=obj['rx'],obj['ry'],obj['angle']; shift=0.
        if rx>=ry: major=[rx*math.cos(angle),rx*math.sin(angle),0]; ratio=ry/rx
        else:
            major=[-ry*math.sin(angle),ry*math.cos(angle),0]; ratio=rx/ry; shift=-math.pi/2
        sweep=obj.get('sweep',g.TAU)
        if abs(sweep)>=g.TAU: start,end=0.,g.TAU
        else:
            start=(obj.get('start',0.)+(sweep if sweep<0 else 0.)+shift)%g.TAU
            end=(start+abs(sweep))%g.TAU
        msp.add_ellipse(obj['center'],major,ratio,start,end,dxfattribs=attrs)
    elif kind=='spline':
        if obj['method']=='bezier' and len(obj['points'])-1>MAX_NATIVE_SPLINE_DEGREE:
            msp.add_lwpolyline(_flatten_bezier(obj['points']),format='xy',close=False,dxfattribs=attrs)
            return True
        for span in selection._spline_spans(obj):
            degree=len(span)-1
            msp.add_open_spline([(p[0],p[1],0) for p in span],degree=degree,
                                knots=[0.]*(degree+1)+[1.]*(degree+1),dxfattribs=attrs)
    else: raise ValueError('Unsupported DXF object type: '+str(kind))
    return False


def build_dxf(snapshot,selected_only=False):
    ezdxf=require_ezdxf()
    ids=snapshot['selected'] if selected_only else range(len(snapshot['objects']))
    objects=[snapshot['objects'][i] for i in ids]
    if not objects: raise ValueError('No selected objects to export.' if selected_only else 'The drawing is empty.')
    document=ezdxf.new(dxfversion='R2018',setup=True)
    document.units=1; document.header['$MEASUREMENT']=0; document.header['$LUNITS']=2
    document.linetypes.new('BRIANCAD_DASHED',dxfattribs={'description':'BrianCAD dashed','pattern':[.375,.25,-.125]})
    document.linetypes.new('BRIANCAD_DOTTED',dxfattribs={'description':'BrianCAD dotted','pattern':[.125,0.,-.125]})
    used={o['layer'] for o in objects}
    layers=[layer for layer in snapshot['layers'] if layer['name'] in used]
    layer_map=_layer_names(document,layers); msp=document.modelspace(); approximated=0
    for obj in objects:
        g.validate_geometry(obj)
        approximated+=int(_add_object(msp,obj,_attributes(obj,layer_map)))
    report={'objects':len(objects),'entities':len(msp),'approximated':approximated,'layer_names':layer_map}
    return document,report


def export_dxf(path,snapshot,selected_only=False):
    """Build first, then atomically replace the destination; never mutate a drawing."""
    document,report=build_dxf(snapshot,selected_only)
    path=Path(path); temp=None
    try:
        with tempfile.NamedTemporaryFile(dir=str(path.resolve().parent),suffix='.dxf',delete=False) as output:
            temp=output.name
        document.saveas(temp)
        os.replace(temp,path); temp=None
    finally:
        if temp is not None:
            try: os.unlink(temp)
            except FileNotFoundError: pass
    return report
