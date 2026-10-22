"""Analytic 2D constructions and sampled display paths, in drawing inches."""
import copy
import math

TAU = 2 * math.pi
EPS = 1e-10


def add(a,b): return [a[0]+b[0],a[1]+b[1]]
def sub(a,b): return [a[0]-b[0],a[1]-b[1]]
def mul(a,k): return [a[0]*k,a[1]*k]
def dot(a,b): return a[0]*b[0]+a[1]*b[1]
def cross(a,b): return a[0]*b[1]-a[1]*b[0]
def dist(a,b): return math.hypot(*sub(a,b))
def unit(v):
    n=math.hypot(*v)
    if n < EPS: raise ValueError('Points must be distinct.')
    return mul(v,1/n)
def normal(v): return [-v[1],v[0]]
def polar(c,r,a): return add(c,[r*math.cos(a),r*math.sin(a)])
def angle(c,p): return math.atan2(p[1]-c[1],p[0]-c[0])


def project(p,a,b,segment=False):
    v=sub(b,a); d=dot(v,v)
    if d<EPS**2: return list(a)
    t=dot(sub(p,a),v)/d
    if segment: t=max(0,min(1,t))
    return add(a,mul(v,t))


def circle_three(a,b,c):
    # Work relative to a, avoiding loss of precision far from the origin.
    u,v=sub(b,a),sub(c,a); d=2*cross(u,v)
    if abs(d)<EPS*max(dot(u,u),dot(v,v),EPS):
        raise ValueError('Three points must be distinct and not collinear.')
    center=add(a,[(dot(u,u)*v[1]-dot(v,v)*u[1])/d,
                  (u[0]*dot(v,v)-v[0]*dot(u,u))/d])
    return {'type':'circle','center':center,'radius':dist(center,a)}


def arc_center(c,start,end,clockwise=False):
    r=dist(c,start)
    if r<EPS or dist(c,end)<EPS: raise ValueError('Arc points must differ from its center.')
    a=angle(c,start); sweep=(angle(c,end)-a)%TAU
    if sweep<EPS or TAU-sweep<EPS: raise ValueError('Use distinct start and end directions for an arc.')
    if clockwise: sweep-=TAU
    return {'type':'arc','center':list(c),'radius':r,'start':a,'sweep':sweep}


def arc_three(a,b,c):
    o=circle_three(a,b,c); start=angle(o['center'],a)
    end=(angle(o['center'],c)-start)%TAU
    mid=(angle(o['center'],b)-start)%TAU
    return dict(o,type='arc',start=start,sweep=end if mid<end else end-TAU)


def arc_tangent(start,direction,end):
    n=normal(unit(direction)); chord=sub(end,start)
    den=2*dot(chord,n)
    if abs(den)<EPS*max(1,math.hypot(*chord)):
        raise ValueError('The endpoint cannot lie on the start tangent line.')
    signed=dot(chord,chord)/den
    c=add(start,mul(n,signed))
    return arc_center(c,start,end,clockwise=signed<0)


def tangent_circle(contact,first_line,second_line,hint):
    """Circle tangent at first contact and to the second supporting line.

    The second picked point selects the nearby solution, rather than specifying
    a second exact contact (arbitrary pairs generally have no common circle).
    """
    v=unit(sub(first_line['b'],first_line['a'])); n=normal(v)
    n2=normal(unit(sub(second_line['b'],second_line['a'])))
    signed_distance=dot(sub(contact,second_line['a']),n2)
    candidates=[]
    for sign in (-1,1):
        den=dot(n,n2)-sign
        if abs(den)<EPS: continue
        r=-signed_distance/den
        if abs(r)<EPS: continue
        c=add(contact,mul(n,r)); other=project(c,second_line['a'],second_line['b'])
        candidates.append((dist(other,hint),{'type':'circle','center':c,'radius':abs(r)}))
    if not candidates: raise ValueError('These tangent lines/contact do not define a unique circle.')
    return min(candidates,key=lambda item:item[0])[1]


def offset_line(line,p=None,offset=None):
    n=normal(unit(sub(line['b'],line['a'])))
    if offset is None: offset=dot(sub(p,line['a']),n)
    if abs(offset)<EPS: raise ValueError('Offset must be nonzero.')
    delta=mul(n,offset)
    return {'type':'line','a':add(line['a'],delta),'b':add(line['b'],delta)}


def ellipse_box(a,b,centered=False):
    c=list(a) if centered else mul(add(a,b),.5)
    rx=abs(b[0]-a[0])*(1 if centered else .5)
    ry=abs(b[1]-a[1])*(1 if centered else .5)
    if min(rx,ry)<EPS: raise ValueError('Ellipse width and height must be positive.')
    return {'type':'ellipse','center':c,'rx':rx,'ry':ry,'angle':0.}


def ellipse_axes(c,major,minor):
    v=sub(major,c); rx=math.hypot(*v)
    ry=abs(dot(sub(minor,c),normal(unit(v))))
    if ry<EPS: raise ValueError('Minor-axis point cannot lie on the major axis.')
    return {'type':'ellipse','center':list(c),'rx':rx,'ry':ry,'angle':math.atan2(v[1],v[0])}


def rectangle(a,b,centered=False):
    if centered: a,b=sub(mul(a,2),b),list(b)
    if abs(b[0]-a[0])<EPS or abs(b[1]-a[1])<EPS: raise ValueError('Rectangle width and height must be nonzero.')
    return {'type':'polygon','points':[list(a),[b[0],a[1]],list(b),[a[0],b[1]]],'closed':True}


def regular_polygon(c,p,sides,circumscribed=False):
    if isinstance(sides,bool) or int(sides)!=sides or not 3<=sides<=200:
        raise ValueError('Number of sides must be a whole number from 3 to 200.')
    r=dist(c,p); a=angle(c,p)
    if r<EPS: raise ValueError('Polygon radius must be positive.')
    if circumscribed: r/=math.cos(math.pi/sides); a+=math.pi/sides
    return {'type':'polygon','points':[polar(c,r,a+TAU*i/sides) for i in range(int(sides))],'closed':True}


def spline_point(o,t):
    pts=o['points']
    if o['method']=='bezier':
        work=[list(p) for p in pts]
        while len(work)>1: work=[add(mul(a,1-t),mul(b,t)) for a,b in zip(work,work[1:])]
        return work[0]
    # Uniform Catmull-Rom interpolation with repeated endpoints; through all picks.
    segments=len(pts) if o.get('closed') else len(pts)-1
    u=min(t*segments,segments-1e-12); i=int(u); f=u-i
    def get(j): return pts[j%len(pts)] if o.get('closed') else pts[max(0,min(len(pts)-1,j))]
    a,b,c,d=(get(i+j) for j in (-1,0,1,2))
    return [.5*((2*b[k])+(-a[k]+c[k])*f+(2*a[k]-5*b[k]+4*c[k]-d[k])*f*f+
                (-a[k]+3*b[k]-3*c[k]+d[k])*f*f*f) for k in (0,1)]


def path(o,samples=128):
    kind=o['type']
    if kind=='line': return [o['a'],o['b']]
    if kind=='polygon': return o['points']+([o['points'][0]] if o.get('closed',True) else [])
    if kind=='spline':
        count=max(samples,32*len(o['points']))
        return [spline_point(o,i/count) for i in range(count+1)]
    if kind in ('circle','arc'):
        sweep=o.get('sweep',TAU); start=o.get('start',0.)
        count=max(16,math.ceil(samples*abs(sweep)/TAU))
        return [polar(o['center'],o['radius'],start+sweep*i/count) for i in range(count+1)]
    c=o['center']; a=o['angle']; u=[math.cos(a),math.sin(a)]; v=normal(u)
    return [add(c,add(mul(u,o['rx']*math.cos(TAU*i/samples)),mul(v,o['ry']*math.sin(TAU*i/samples)))) for i in range(samples+1)]


def anchors(o):
    kind=o['type']
    if kind=='line':
        return [(o['a'],'endpoint'),(o['b'],'endpoint'),(mul(add(o['a'],o['b']),.5),'midpoint')]
    if kind=='circle': return [(o['center'],'center')]+[(polar(o['center'],o['radius'],i*math.pi/2),'quadrant') for i in range(4)]
    if kind=='arc':
        return [(o['center'],'center')]+[(polar(o['center'],o['radius'],o['start']+o['sweep']*t),label) for t,label in [(0,'endpoint'),(.5,'midpoint'),(1,'endpoint')]]
    if kind=='ellipse':
        pts=path(o,4)
        return [(o['center'],'center')]+[(p,'axis endpoint') for p in pts[:-1]]
    if kind=='polygon': return [(p,'vertex') for p in o['points']]
    return [(p,'control point' if o['method']=='bezier' else 'fit point') for p in o['points']]


def hit_distance(p,o):
    if o['type']=='circle': return abs(dist(p,o['center'])-o['radius'])
    if o['type']=='arc':
        a=(angle(o['center'],p)-o['start'])%TAU
        inside=a<=o['sweep'] if o['sweep']>0 else ((o['start']-angle(o['center'],p))%TAU<=-o['sweep'])
        if inside: return abs(dist(p,o['center'])-o['radius'])
        return min(dist(p,polar(o['center'],o['radius'],o['start']+x)) for x in [0,o['sweep']])
    pts=path(o)
    return min(dist(p,project(p,a,b,True)) for a,b in zip(pts,pts[1:]))


def length(o):
    if o['type']=='line': return dist(o['a'],o['b'])
    if o['type'] in ('circle','arc'): return o['radius']*abs(o.get('sweep',TAU))
    pts=path(o,1024)
    return sum(dist(a,b) for a,b in zip(pts,pts[1:]))


def transform(o,mode,pivot=(0,0),dx=0,dy=0,angle=0,factor=1):
    """Uniform scale, rotation, translation, or reflection about a pivot line."""
    if mode=='Scale' and factor<=0: raise ValueError('Scale factor must be positive.')
    a=math.radians(angle)
    def point(p):
        if mode=='Move': return add(p,[dx,dy])
        x,y=sub(p,pivot)
        if mode=='Scale': x,y=x*factor,y*factor
        elif mode=='Rotate': x,y=x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)
        elif mode=='Mirror':
            x,y=x*math.cos(2*a)+y*math.sin(2*a),x*math.sin(2*a)-y*math.cos(2*a)
        return add(pivot,[x,y])
    n=copy.deepcopy(o)
    for k in ('a','b','center'):
        if k in o: n[k]=point(o[k])
    if 'points' in o: n['points']=[point(p) for p in o['points']]
    if mode=='Scale':
        for k in ('radius','rx','ry'):
            if k in n: n[k]*=factor
    if o['type']=='arc':
        if mode=='Rotate': n['start']+=a
        elif mode=='Mirror': n['start']=2*a-o['start']; n['sweep']=-o['sweep']
    if o['type']=='ellipse':
        if mode=='Rotate': n['angle']+=a
        elif mode=='Mirror': n['angle']=2*a-o['angle']
    return n


def validate_geometry(o):
    def number(v):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>1e9:
            raise ValueError('Coordinates and dimensions must be finite and within ±1,000,000,000.')
    def point(v):
        if not isinstance(v,(list,tuple)) or len(v)!=2: raise ValueError('Expected an X/Y point.')
        for x in v: number(x)
    kind=o.get('type')
    if kind=='line':
        point(o.get('a')); point(o.get('b'))
        if dist(o['a'],o['b'])<EPS: raise ValueError('Line endpoints must be distinct.')
    elif kind in ('circle','arc','ellipse'):
        point(o.get('center'))
        for key in (('rx','ry') if kind=='ellipse' else ('radius',)):
            number(o.get(key))
            if o[key]<EPS: raise ValueError('Radii must be positive.')
        if kind=='ellipse': number(o.get('angle'))
        if kind=='arc':
            number(o.get('start')); number(o.get('sweep'))
            if not EPS<=abs(o['sweep'])<=TAU+EPS: raise ValueError('Arc sweep must be between 0 and 360 degrees, excluding zero.')
    elif kind in ('polygon','spline'):
        pts=o.get('points')
        if not isinstance(pts,list) or not (3 if kind=='polygon' else 2)<=len(pts)<=200:
            raise ValueError('Use 3–200 polygon vertices or 2–200 spline points.')
        for p in pts: point(p)
        if any(dist(a,b)<EPS for a,b in zip(pts,pts[1:])): raise ValueError('Consecutive points must be distinct.')
        if kind=='spline':
            if o.get('method') not in ('through','bezier'): raise ValueError('Unknown spline method.')
            if o['method']=='bezier' and len(pts)>32: raise ValueError('Use at most 32 Bézier control points.')
            if o.get('closed') and len(pts)<3: raise ValueError('Closed splines require at least three points.')
        if not isinstance(o.get('closed',False),bool): raise ValueError('Closed must be true or false.')
    else: raise ValueError('Unsupported object type.')
    return o
