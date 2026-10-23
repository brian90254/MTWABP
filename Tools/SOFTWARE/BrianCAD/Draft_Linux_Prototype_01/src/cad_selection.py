"""Editable handles, exact/conservative curve bounds, and curve projections."""
import copy
import math
import cad_geometry as g


def controls(o):
    kind=o['type']
    if kind=='line': return [('a',list(o['a'])),('b',list(o['b']))]
    if kind=='circle': return [('center',list(o['center'])),('radius',g.polar(o['center'],o['radius'],o.get('handle_angle',0.)))]
    if kind=='arc':
        return [('center',list(o['center']))]+[(key,g.polar(o['center'],o['radius'],o['start']+o['sweep']*t))
                                              for key,t in [('start',0),('through',o.get('through_fraction',.5)),('end',1)]]
    if kind=='ellipse':
        return [('center',list(o['center'])),('axis_x',g.polar(o['center'],o['rx'],o['angle'])),
                ('axis_y',g.polar(o['center'],o['ry'],o['angle']+math.pi/2))]
    return [('p'+str(i),list(p)) for i,p in enumerate(o['points'])]


def move_controls(o,keys,dx,dy):
    """Move independent handles, retaining the object's analytic representation.

    Center handles translate curved objects. Arc rim handles define a three-point
    arc; ellipse axis handles preserve perpendicular axes. Constraints can make
    dependent handles move as well. Invalid/collapsed geometry raises ValueError.
    """
    old=dict(controls(o)); keys=set(keys)
    if not keys <= set(old): raise ValueError('The selected control point no longer exists.')
    if not keys: return copy.deepcopy(o)
    if keys==set(old) or 'center' in keys or (o['type']=='arc' and keys >= {'start','through','end'}):
        return g.transform(o,'Move',dx=dx,dy=dy)
    new={key:g.add(p,[dx,dy]) if key in keys else p for key,p in old.items()}
    n=copy.deepcopy(o); kind=o['type']
    if kind=='line': n.update(a=new['a'],b=new['b'])
    elif kind=='circle':
        n['radius']=g.dist(o['center'],new['radius']); n['handle_angle']=g.angle(o['center'],new['radius'])
    elif kind=='arc': n.update(g.arc_three(new['start'],new['through'],new['end']))
    elif kind=='ellipse': n.update(g.ellipse_axes(new['center'],new['axis_x'],new['axis_y']))
    else: n['points']=[new['p'+str(i)] for i in range(len(o['points']))]
    return g.validate_geometry(n)


def _bezier_point(points,t):
    work=[list(p) for p in points]
    while len(work)>1: work=[g.add(g.mul(a,1-t),g.mul(b,t)) for a,b in zip(work,work[1:])]
    return work[0]


def _spline_spans(o):
    points=o['points']
    if o['method']=='bezier': return [points]
    def at(i): return points[i%len(points)] if o.get('closed') else points[max(0,min(len(points)-1,i))]
    result=[]
    for i in range(len(points) if o.get('closed') else len(points)-1):
        a,b,c,d=(at(i+j) for j in [-1,0,1,2])
        result.append([b,g.add(b,g.mul(g.sub(c,a),1/6)),g.sub(c,g.mul(g.sub(d,b),1/6)),c])
    return result


def _bernstein_roots(coeffs,lo=0.,hi=1.,depth=0):
    """Isolate derivative roots by Bernstein convex-hull subdivision."""
    tol=1e-13*max(1,max(abs(v) for v in coeffs))
    if max(abs(v) for v in coeffs)<=tol: return []
    endpoints=([lo] if abs(coeffs[0])<=tol else [])+([hi] if abs(coeffs[-1])<=tol else [])
    if min(coeffs)>=-tol or max(coeffs)<=tol: return endpoints
    if depth>=40: return [(lo+hi)/2]
    levels=[list(coeffs)]
    while len(levels[-1])>1: levels.append([(a+b)/2 for a,b in zip(levels[-1],levels[-1][1:])])
    left=[row[0] for row in levels]; right=[row[-1] for row in reversed(levels)]
    mid=(lo+hi)/2
    return endpoints+_bernstein_roots(left,lo,mid,depth+1)+_bernstein_roots(right,mid,hi,depth+1)


def bounds(o):
    kind=o['type']
    if kind=='circle':
        c=o['center']; r=o['radius']; return [c[0]-r,c[1]-r,c[0]+r,c[1]+r]
    if kind=='ellipse':
        c=o['center']; a=o['angle']
        ex=math.hypot(o['rx']*math.cos(a),o['ry']*math.sin(a))
        ey=math.hypot(o['rx']*math.sin(a),o['ry']*math.cos(a))
        return [c[0]-ex,c[1]-ey,c[0]+ex,c[1]+ey]
    if kind=='arc':
        pts=[g.polar(o['center'],o['radius'],o['start']+v) for v in (0,o['sweep'])]
        for a in [0,math.pi/2,math.pi,3*math.pi/2]:
            u=(a-o['start'])%g.TAU if o['sweep']>0 else (o['start']-a)%g.TAU
            if u<=abs(o['sweep'])+1e-12: pts.append(g.polar(o['center'],o['radius'],a))
    elif kind=='spline':
        pts=[]
        for span in _spline_spans(o):
            ts=[0.,1.]
            for axis in (0,1):
                coeffs=[(len(span)-1)*(b[axis]-a[axis]) for a,b in zip(span,span[1:])]
                ts+=_bernstein_roots(coeffs)
            pts.extend(_bezier_point(span,t) for t in ts)
    else: pts=[o['a'],o['b']] if kind=='line' else o['points']
    return [min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)]


def in_box(p,box,tol=1e-10):
    return box[0]-tol<=p[0]<=box[2]+tol and box[1]-tol<=p[1]<=box[3]+tol


def wholly_inside(o,box):
    b=bounds(o)
    return in_box(b[:2],box) and in_box(b[2:],box)


def box_distance(p,box):
    return math.hypot(max(box[0]-p[0],0,p[0]-box[2]),max(box[1]-p[1],0,p[1]-box[3]))


def _minimum(fn,p,steps):
    """Bracket local minima, then refine parameter-space distances (no chord snaps)."""
    def score(t):
        q=fn(t); return (q[0]-p[0])**2+(q[1]-p[1])**2
    values=[score(i/steps) for i in range(steps+1)]
    candidates=[(values[0],0.),(values[-1],1.)]
    ratio=(math.sqrt(5)-1)/2
    for i in range(1,steps):
        if values[i]>values[i-1] or values[i]>values[i+1]: continue
        a,b=(i-1)/steps,(i+1)/steps
        x=b-ratio*(b-a); y=a+ratio*(b-a); fx,fy=score(x),score(y)
        for _ in range(46):
            if fx<fy: b,y,fy=y,x,fx; x=b-ratio*(b-a); fx=score(x)
            else: a,x,fx=x,y,fy; y=a+ratio*(b-a); fy=score(y)
        t=(a+b)/2; candidates.append((score(t),t))
    return fn(min(candidates,key=lambda v:v[0])[1])


def nearest_point(p,o):
    kind=o['type']
    if kind=='line': return g.project(p,o['a'],o['b'],True)
    if kind in ['circle','arc']:
        a=g.angle(o['center'],p)
        q=g.polar(o['center'],o['radius'],a)
        if kind=='circle': return q
        u=(a-o['start'])%g.TAU if o['sweep']>0 else (o['start']-a)%g.TAU
        if u<=abs(o['sweep']): return q
        return min([g.polar(o['center'],o['radius'],o['start']+v) for v in (0,o['sweep'])],key=lambda v:g.dist(p,v))
    if kind=='polygon':
        pts=g.path(o)
        return min([g.project(p,a,b,True) for a,b in zip(pts,pts[1:])],key=lambda q:g.dist(p,q))
    if kind=='ellipse':
        def fn(t):
            a=g.TAU*t; ca,sa=math.cos(o['angle']),math.sin(o['angle'])
            x,y=o['rx']*math.cos(a),o['ry']*math.sin(a)
            return g.add(o['center'],[ca*x-sa*y,sa*x+ca*y])
        return _minimum(fn,p,64)
    candidates=[_minimum(lambda t,span=span:_bezier_point(span,t),p,max(32,8*len(span))) for span in _spline_spans(o)]
    return min(candidates,key=lambda q:g.dist(p,q))
