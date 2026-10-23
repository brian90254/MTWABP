"""Exact finite intersections and click-directed trimming of lines/circular curves."""
import bisect
import copy
import math
import cad_geometry as g

TARGETS={'line','circle','arc'}
BOUNDARIES=TARGETS|{'polygon'}
TOL=1e-10


def parameter(obj,p):
    """Curve parameter in [0,1], or None when outside a finite curve."""
    if obj['type']=='line':
        v=g.sub(obj['b'],obj['a']); t=g.dot(g.sub(p,obj['a']),v)/g.dot(v,v)
    else:
        sweep=obj.get('sweep',g.TAU); start=obj.get('start',0.)
        delta=((g.angle(obj['center'],p)-start)*(1 if sweep>0 else -1))%g.TAU
        if g.TAU-delta<TOL: delta=0.
        t=delta/abs(sweep)
    return max(0.,min(1.,t)) if -TOL<=t<=1+TOL else None


def intersections(a,b):
    """Finite crossings; coincident curves and tangential touches do not cut."""
    if a['type']=='polygon' or b['type']=='polygon':
        polygon,other=(a,b) if a['type']=='polygon' else (b,a)
        pts=polygon['points']
        return [p for x,y in zip(pts,pts[1:]+pts[:1])
                for p in intersections({'type':'line','a':x,'b':y},other)]
    if a['type'] not in TARGETS or b['type'] not in TARGETS: return []
    if a['type']=='line' and b['type']=='line':
        u=g.sub(a['b'],a['a']); v=g.sub(b['b'],b['a']); det=g.cross(u,v)
        if abs(det)<=1e-12*math.hypot(*u)*math.hypot(*v): return []
        t=g.cross(g.sub(b['a'],a['a']),v)/det
        pts=[g.add(a['a'],g.mul(u,t))]
    elif a['type']=='line' or b['type']=='line':
        line,circle=(a,b) if a['type']=='line' else (b,a)
        u=g.unit(g.sub(line['b'],line['a'])); w=g.sub(circle['center'],line['a'])
        along=g.dot(w,u); perpendicular=g.cross(w,u)
        h2=circle['radius']**2-perpendicular**2
        if h2<=1e-12*circle['radius']**2: return []
        h=math.sqrt(h2)
        pts=[g.add(line['a'],g.mul(u,along+s*h)) for s in (-1,1)]
    else:
        c1,c2=a['center'],b['center']; r1,r2=a['radius'],b['radius']
        d=g.dist(c1,c2)
        if d<=abs(r1-r2) or d>=r1+r2: return []
        u=g.mul(g.sub(c2,c1),1/d)
        x=(d*d+(r1-r2)*(r1+r2))/(2*d); h2=r1*r1-x*x
        if h2<=1e-12*r1*r1: return []
        base=g.add(c1,g.mul(u,x)); offset=g.mul(g.normal(u),math.sqrt(h2))
        pts=[g.add(base,offset),g.sub(base,offset)]
    return [p for p in pts if parameter(a,p) is not None and parameter(b,p) is not None]


def fragment(obj,lo,hi):
    n=copy.deepcopy(obj)
    if obj['type']=='line':
        v=g.sub(obj['b'],obj['a'])
        n['a']=g.add(obj['a'],g.mul(v,lo)); n['b']=g.add(obj['a'],g.mul(v,hi))
    else:
        sweep=obj.get('sweep',g.TAU)
        n.update(type='arc',start=obj.get('start',0.)+sweep*lo,sweep=sweep*(hi-lo))
        n.pop('handle_angle',None); n.pop('through_fraction',None)
    return g.validate_geometry(n)


def trim(obj,boundaries,click):
    """Return retained pieces, removing only the interval beneath the click."""
    if obj['type'] not in TARGETS:
        raise ValueError('Trim currently supports line, circle, and arc targets.')
    values=sorted(parameter(obj,p) for b in boundaries for p in intersections(obj,b))
    cuts=[]
    for t in values:
        if not cuts or t-cuts[-1]>TOL: cuts.append(t)
    t=parameter(obj,click)
    # Clicks are projected by the UI; also accept nearby angular/line positions.
    if t is None: raise ValueError('Click on the part of the object to remove.')
    closed=obj['type']=='circle' or (obj['type']=='arc' and abs(abs(obj['sweep'])-g.TAU)<TOL)
    if closed:
        if cuts and cuts[-1]-cuts[0]>1-TOL: cuts.pop()
        if len(cuts)<2: raise ValueError('The circle needs at least two distinct cutting crossings.')
        i=bisect.bisect_right(cuts,t)
        lo=cuts[i-1] if i else cuts[-1]-1
        hi=cuts[i] if i<len(cuts) else cuts[0]+1
        return [fragment(obj,hi,lo+1)]
    cuts=[x for x in cuts if TOL<x<1-TOL]
    if not cuts: raise ValueError('No cutting crossing on this object; nothing was trimmed.')
    ends=[0.]+cuts+[1.]; i=min(len(ends)-2,bisect.bisect_right(ends,t)-1)
    lo,hi=ends[i:i+2]
    return [fragment(obj,a,b) for a,b in [(0.,lo),(hi,1.)] if b-a>TOL]
