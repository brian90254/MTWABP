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
        if 'sweep' in o: return [('center',list(o['center']))]+[(key,g.ellipse_point(o,t)) for key,t in [('start',0),('end',1)]]
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
    elif kind=='ellipse':
        if 'sweep' in o:
            start=g.ellipse_angle(o,new['start']); end=g.ellipse_angle(o,new['end'])
            sweep=(end-start)%g.TAU if o['sweep']>0 else -((start-end)%g.TAU)
            n.update(start=start,sweep=sweep)
        else: n.update(g.ellipse_axes(new['center'],new['axis_x'],new['axis_y']))
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
        if 'sweep' in o:
            pts=[g.ellipse_point(o,t) for t in (0,1)]
            full=dict(o); full.pop('start'); full.pop('sweep')
            for angle in [math.atan2(-o['ry']*math.sin(a),o['rx']*math.cos(a)),math.atan2(o['ry']*math.cos(a),o['rx']*math.sin(a))]:
                for v in (angle,angle+math.pi):
                    p=g.ellipse_point(full,v/g.TAU)
                    if g.ellipse_contains(o,p): pts.append(p)
            return [min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)]
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


def _minimum_parameter(fn,p,steps):
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
    return min(candidates,key=lambda v:v[0])[1]


def _minimum(fn,p,steps): return fn(_minimum_parameter(fn,p,steps))


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
    if kind=='ellipse': return _minimum(lambda t:g.ellipse_point(o,t),p,64)
    candidates=[_minimum(lambda t,span=span:_bezier_point(span,t),p,max(32,8*len(span))) for span in _spline_spans(o)]
    return min(candidates,key=lambda q:g.dist(p,q))


def axis_intersections(o,axis,value):
    """Finite intersections with an infinite horizontal/vertical guide.

    Circular and elliptical curves are analytic. Spline coordinates are solved
    in Bernstein form, including tangent roots, rather than display chords.
    Coincident spans have no distinct intersection and are omitted.
    """
    kind=o['type']; other=1-axis; points=[]
    if kind in ('line','polygon'):
        pts=[o['a'],o['b']] if kind=='line' else o['points']+([o['points'][0]] if o.get('closed',True) else [])
        for a,b in zip(pts,pts[1:]):
            delta=b[axis]-a[axis]
            if abs(delta)<1e-12: continue
            t=(value-a[axis])/delta
            if -1e-10<=t<=1+1e-10:
                points.append(g.add(a,g.mul(g.sub(b,a),max(0,min(1,t)))))
    elif kind in ('circle','arc'):
        c=o['center']; r=o['radius']; d=value-c[axis]
        h2=r*r-d*d
        if h2>=-1e-12*r*r:
            h=math.sqrt(max(0,h2))
            for sign in (-1,1):
                p=list(c); p[axis]=value; p[other]+=sign*h
                if kind=='arc':
                    delta=((g.angle(c,p)-o['start'])*(1 if o['sweep']>0 else -1))%g.TAU
                    if delta>abs(o['sweep'])+1e-10 and g.TAU-delta>1e-10: continue
                points.append(p)
    elif kind=='ellipse':
        a=o['angle']; c=o['center']
        u=[o['rx']*math.cos(a),o['rx']*math.sin(a)]
        v=[-o['ry']*math.sin(a),o['ry']*math.cos(a)]
        amplitude=math.hypot(u[axis],v[axis]); ratio=(value-c[axis])/amplitude
        if abs(ratio)<=1+1e-12:
            phase=math.atan2(v[axis],u[axis]); offset=math.acos(max(-1,min(1,ratio)))
            points=[g.add(c,g.add(g.mul(u,math.cos(t)),g.mul(v,math.sin(t)))) for t in (phase-offset,phase+offset)]
    elif kind=='spline':
        for span in _spline_spans(o):
            ts=_bernstein_roots([p[axis]-value for p in span])
            points.extend(_bezier_point(span,t) for t in ts)
    result=[]
    for p in points:
        if kind=='ellipse' and not g.ellipse_contains(o,p): continue
        p[axis]=value
        if not any(g.dist(p,q)<1e-9 for q in result): result.append(p)
    return result


def _bernstein_product(a,b):
    n,m=len(a)-1,len(b)-1
    result=[0.]*(n+m+1)
    for i,x in enumerate(a):
        for j,y in enumerate(b):
            result[i+j]+=x*y*math.comb(n,i)*math.comb(m,j)/math.comb(n+m,i+j)
    return result


def _constraint_span(start,span,weights,mode):
    # Work relative to start. V/W is the contact vector; D/W² its derivative.
    v=[[w*(p[k]-start[k]) for p,w in zip(span,weights)] for k in (0,1)]
    n=len(span)-1; dw=[n*(b-a) for a,b in zip(weights,weights[1:])]
    derivative=[]
    for values in v:
        dv=[n*(b-a) for a,b in zip(values,values[1:])]
        left=_bernstein_product(dv,weights); right=_bernstein_product(values,dw)
        derivative.append([a-b for a,b in zip(left,right)])
    if mode=='tangent':
        a=_bernstein_product(v[0],derivative[1]); b=_bernstein_product(v[1],derivative[0])
        coeffs=[x-y for x,y in zip(a,b)]
    else:
        a=_bernstein_product(v[0],derivative[0]); b=_bernstein_product(v[1],derivative[1])
        coeffs=[x+y for x,y in zip(a,b)]
    scale=max(abs(x) for x in coeffs)
    magnitude=max(abs(x) for x in a+b)
    if scale<=max(1e-300,1e-12*magnitude): return []  # No distinct contact in a continuum.
    points=[]
    for t in _bernstein_roots([x/scale for x in coeffs]):
        w=_bezier_point([[x,0] for x in weights],t)[0]
        offset=_bezier_point(list(zip(*v)),t); offset=g.mul(offset,1/w)
        d=_bezier_point(list(zip(*derivative)),t)
        if math.hypot(*d)<g.EPS or math.hypot(*offset)<g.EPS: continue
        error=abs(g.cross(g.unit(offset),g.unit(d))) if mode=='tangent' else abs(g.dot(g.unit(offset),g.unit(d)))
        if error<1e-6: points.append(g.add(start,offset))
    return points


def constraint_points(start,o,mode):
    """Nonzero line contacts tangent/perpendicular to finite existing geometry."""
    kind=o['type']; points=[]
    if mode=='tangent' and kind in ('circle','arc','ellipse'):
        return g.tangent_points(start,o)
    if kind in ('line','polygon'):
        if mode=='tangent': return []
        pts=g.path(o)
        for a,b in zip(pts,pts[1:]):
            length2=g.dot(g.sub(b,a),g.sub(b,a))
            if length2<g.EPS**2: continue
            q=g.project(start,a,b)
            if -1e-10<=g.dot(g.sub(q,a),g.sub(b,a))/length2<=1+1e-10:
                points.append(q)
    elif kind in ('circle','arc'):
        if g.dist(start,o['center'])<g.EPS: return []
        a=g.angle(o['center'],start)
        points=[g.polar(o['center'],o['radius'],a+delta) for delta in (0,math.pi)]
        points=[q for q in points if g.arc_contains(o,q)]
    elif kind=='ellipse':
        ca,sa=math.cos(o['angle']),math.sin(o['angle'])
        def world(p):
            x,y=p[0]*o['rx'],p[1]*o['ry']
            return g.add(o['center'],[ca*x-sa*y,sa*x+ca*y])
        for i in range(4):
            a=i*math.pi/2; b=a+math.pi/2
            span=[world([math.cos(a),math.sin(a)]),
                  world([math.cos(a)+math.cos(b),math.sin(a)+math.sin(b)]),
                  world([math.cos(b),math.sin(b)])]
            points.extend(_constraint_span(start,span,[1.,math.sqrt(.5),1.],mode))
    elif kind=='spline':
        for span in _spline_spans(o): points.extend(_constraint_span(start,span,[1.]*len(span),mode))
    result=[]
    for q in points:
        if kind=='ellipse' and not g.ellipse_contains(o,q): continue
        if g.dist(start,q)>g.EPS and not any(g.dist(q,p)<1e-9 for p in result): result.append(q)
    return result
