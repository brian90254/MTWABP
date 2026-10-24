"""Construction-method catalog and shared numeric/mouse construction functions."""
import math
import cad_geometry as g

METHODS={
    'Select':['Select'],
    'Trim':['Trim'],
    'Lines':['Two points','Connected points','Offset from line'],
    'Arcs':['Center + start + end','Three-point arc','Start tangent + end'],
    'Circles':['Center + diameter','Diameter endpoints','Three-point circle','Two tangent lines'],
    'Ovals':['Center + corner','Opposite corners','Center + axis + width','Axis endpoints + width'],
    'Polygons':['Rectangle corners','Rectangle center','Inscribed polygon','Circumscribed polygon'],
    'Splines':['Through points','Closed through points','Bezier controls'],
    'Modify':['Move','Rotate','Scale','Mirror'],
}
THREE={'Start tangent + end','Center + start + end','Three-point arc','Three-point circle','Center + axis + width','Axis endpoints + width'}
DEFAULTS={'x':0,'y':0,'x2':1,'y2':0,'x3':1,'y3':1,'dx':1,'dy':0,'length':1,'angle':0,
          'diameter':1,'offset':.25,'sides':6,'factor':1}
LABELS={'x':'X','y':'Y','x2':'End X','y2':'End Y','x3':'Third X','y3':'Third Y','dx':'dX','dy':'dY',
        'length':'Length','angle':'Angle °','diameter':'Diameter','offset':'Offset','sides':'Sides','factor':'Factor'}


def fields_for(family,method):
    if family in ('Select','Trim'): return []
    if family=='Modify': return ['x','y','dx','dy'] if method=='Move' else ['x','y','factor'] if method=='Scale' else ['x','y','angle']
    if family=='Splines': return ['x','y']
    if method=='Center + diameter': return ['x','y','diameter']
    fields=['x','y','x2','y2']
    if method in THREE: fields+=['x3','y3']
    if family=='Lines' and method!='Offset from line': fields+=['dx','dy','length','angle']
    if method=='Center + diameter': fields+=['diameter']
    if method=='Offset from line': fields+=['offset']
    if method in ('Inscribed polygon','Circumscribed polygon'): fields+=['sides']
    return fields


def point_values(v,count): return [[v.get('x'+(str(i+1) if i else ''),0),v.get('y'+(str(i+1) if i else ''),0)] for i in range(count)]


def construct(method,pts,values,refs=None,clockwise=False):
    refs=refs or []
    a,b=pts[:2]
    if method in ('Two points','Connected points'): o={'type':'line','a':a,'b':b}
    elif method=='Offset from line':
        if not refs or refs[0] is None: raise ValueError('Pick an existing line first.')
        o=g.offset_line(refs[0],offset=values['offset'])
    elif method=='Center + start + end': o=g.arc_center(a,b,pts[2],clockwise)
    elif method=='Three-point arc': o=g.arc_three(a,b,pts[2])
    elif method=='Start tangent + end':
        o=g.arc_tangent(a,g.sub(b,a),pts[2])
    elif method=='Center + diameter':
        if values['diameter']<=0: raise ValueError('Diameter must be positive.')
        o={'type':'circle','center':a,'radius':values['diameter']/2}
    elif method=='Diameter endpoints': o={'type':'circle','center':g.mul(g.add(a,b),.5),'radius':g.dist(a,b)/2}
    elif method=='Three-point circle': o=g.circle_three(a,b,pts[2])
    elif method=='Two tangent lines':
        if len(refs)<2 or any(r is None for r in refs[:2]): raise ValueError('Pick two existing tangent lines.')
        if g.dist(a,g.project(a,refs[0]['a'],refs[0]['b']))>1e-8: raise ValueError('First contact must remain on its tangent line.')
        o=g.tangent_circle(a,refs[0],refs[1],b)
    elif method=='Center + corner': o=g.ellipse_box(a,b,True)
    elif method=='Opposite corners': o=g.ellipse_box(a,b)
    elif method=='Center + axis + width': o=g.ellipse_axes(a,b,pts[2])
    elif method=='Axis endpoints + width': o=g.ellipse_axes(g.mul(g.add(a,b),.5),b,pts[2])
    elif method=='Rectangle corners': o=g.rectangle(a,b)
    elif method=='Rectangle center': o=g.rectangle(a,b,True)
    elif method in ('Inscribed polygon','Circumscribed polygon'):
        o=g.regular_polygon(a,b,values['sides'],method=='Circumscribed polygon')
    elif method in ('Through points','Closed through points','Bezier controls'):
        if method=='Closed through points' and len(pts)<3: raise ValueError('Pick at least three points for a closed spline.')
        o={'type':'spline','points':[list(p) for p in pts], 'method':'bezier' if method=='Bezier controls' else 'through',
           'closed':method=='Closed through points'}
    else: raise ValueError('Unknown construction method.')
    return g.validate_geometry(o)
