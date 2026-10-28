"""Shared property schemas and sparse object edits for the selection inspector."""
import copy
import math
from cad_document import COLORS, rgb_color


BASE={'layer':('Layer','choice'),'color':('Color','choice'),'locked':('Locked','choice'),
      'pattern':('Pattern','choice'),'weight':('Line width (inches)','number'),
      'controls':('Show control points','choice')}


def schema(o):
    result=dict(BASE); kind=o['type']
    if kind=='line':
        result.update({k:(label,'number') for k,label in [('ax','Start X'),('ay','Start Y'),('bx','End X'),('by','End Y')]})
    elif kind in ('circle','arc','ellipse'):
        result.update(cx=('Center X','number'),cy=('Center Y','number'))
        if kind=='ellipse':
            result.update(rx=('X semi-axis','number'),ry=('Y semi-axis','number'),angle=('Rotation °','number'))
        else: result['diameter']=('Diameter','number')
        if kind=='arc' or (kind=='ellipse' and 'sweep' in o):
            result.update(start=('Start angle °','number'),sweep=('Signed sweep °','number'))
    else:
        result.update(points=('Points: x,y; x,y; ...','points'),closed=('Closed','choice'))
        if kind=='spline': result['method']=('Spline method','choice')
    return result


def values(o):
    result={k:o[k] for k in BASE}
    result['color']=next((name for name,color in COLORS.items() if color==o['color']),o['color'])
    for key in ('locked','controls'): result[key]=str(result[key])
    kind=o['type']
    if kind=='line':
        for key in ('a','b'):
            for axis,letter in enumerate(('x','y')): result[key+letter]=o[key][axis]
    elif kind in ('circle','arc','ellipse'):
        result.update(cx=o['center'][0],cy=o['center'][1])
        if kind=='ellipse': result.update(rx=o['rx'],ry=o['ry'],angle=math.degrees(o['angle']))
        else: result['diameter']=2*o['radius']
        if 'sweep' in o: result.update(start=math.degrees(o['start']),sweep=math.degrees(o['sweep']))
    else:
        result.update(points=copy.deepcopy(o['points']),closed=str(o.get('closed',True)))
        if kind=='spline': result['method']=o['method']
    return result


def display(value,kind):
    if kind=='number': return f'{value:.12g}'
    if kind=='points': return '; '.join(f'{p[0]:.12g},{p[1]:.12g}' for p in value)
    return str(value)


def choices(key,layers):
    return {'layer':list(layers),'color':list(COLORS),'locked':['False','True'],
            'controls':['False','True'],'closed':['False','True'],
            'weight':['0.005','0.01','0.02','0.03','0.05','0.1'],
            'pattern':['Solid','Dashed','Dotted'],'method':['through','bezier']}.get(key)


def common(objects):
    if not objects: return {}
    result=schema(objects[0])
    return {key:spec for key,spec in result.items() if all(schema(o).get(key)==spec for o in objects[1:])}


def apply_changes(original,changes):
    """Blank/untouched fields leave every object's individual value intact."""
    o=copy.deepcopy(original); specs=schema(o)
    for key,text in changes.items():
        if key not in specs: raise ValueError('This property is not shared by the current selection.')
        text=text.strip()
        if not text: continue
        if key=='color':
            o['color']=COLORS[text] if text in COLORS else rgb_color(text)
        elif key in ('locked','controls','closed'):
            if text not in ('False','True'): raise ValueError('Choose True or False.')
            o[key]=text=='True'
        elif specs[key][1]=='number':
            value=float(text)
            if not math.isfinite(value): raise ValueError('Enter finite numeric values.')
            if key in ('ax','ay','bx','by'): o[key[0]][0 if key[1]=='x' else 1]=value
            elif key in ('cx','cy'): o['center'][0 if key=='cx' else 1]=value
            elif key=='diameter': o['radius']=value/2
            elif key in ('angle','start','sweep'): o[key]=math.radians(value)
            else: o[key]=value
        elif key=='points': o['points']=[[float(n.strip()) for n in p.split(',')] for p in text.split(';')]
        else: o[key]=text
    return o
