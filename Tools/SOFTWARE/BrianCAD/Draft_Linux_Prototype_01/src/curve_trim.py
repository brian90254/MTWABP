"""Shape-preserving spline fragments and finite curved trim intersections."""
import math
import cad_geometry as g
import cad_selection as s


def split(points,t):
    levels=[[list(p) for p in points]]
    while len(levels[-1])>1:
        levels.append([g.add(g.mul(a,1-t),g.mul(b,t)) for a,b in zip(levels[-1],levels[-1][1:])])
    return [row[0] for row in levels],[row[-1] for row in reversed(levels)]


def spline_fragments(o,lo,hi):
    spans=s._spline_spans(o); n=len(spans); result=[]
    for turn in range(math.floor(lo),math.ceil(hi)):
        for i,span in enumerate(spans):
            a=max(0.,lo*n-(turn*n+i)); b=min(1.,hi*n-(turn*n+i))
            if b-a<=1e-10: continue
            left=split(span,b)[0]
            points=split(left,a/b)[1] if a>0 else left
            if max(g.dist(points[0],p) for p in points)<g.EPS: continue
            piece=dict(o,type='spline',method='bezier',closed=False,points=points)
            result.append(g.validate_geometry(piece))
    return result


def parameter(o,p):
    kind=o['type']
    if kind=='line':
        v=g.sub(o['b'],o['a']); t=g.dot(g.sub(p,o['a']),v)/g.dot(v,v)
    elif kind=='spline':
        spans=s._spline_spans(o); candidates=[]
        for i,span in enumerate(spans):
            fn=lambda t,span=span:s._bezier_point(span,t)
            u=s._minimum_parameter(fn,p,max(32,8*len(span)))
            candidates.append((g.dist(p,fn(u)),(i+u)/len(spans)))
        return min(candidates)[1]
    else:
        angle=g.ellipse_angle(o,p) if kind=='ellipse' else g.angle(o['center'],p)
        sweep=o.get('sweep',g.TAU)
        delta=((angle-o.get('start',0.))*(1 if sweep>0 else -1))%g.TAU
        if g.TAU-delta<1e-10: delta=0.
        t=delta/abs(sweep)
    return max(0.,min(1.,t)) if -1e-9<=t<=1+1e-9 else None


def spans(o):
    kind=o['type']
    if kind=='spline': return [(p,[1.]*len(p)) for p in s._spline_spans(o)]
    if kind in ('line','polygon'):
        pts=g.path(o)
        return [([a,b],[1.,1.]) for a,b in zip(pts,pts[1:]) if g.dist(a,b)>g.EPS]
    start=o.get('start',0.); sweep=o.get('sweep',g.TAU)
    n=max(1,math.ceil(abs(sweep)/(math.pi/2)))
    full=dict(o); full.pop('start',None); full.pop('sweep',None)
    def point(a):
        return g.ellipse_point(full,a/g.TAU) if kind=='ellipse' else g.polar(o['center'],o['radius'],a)
    result=[]
    for i in range(n):
        a=start+sweep*i/n; b=start+sweep*(i+1)/n; w=math.cos((b-a)/2)
        middle=g.add(o['center'],g.mul(g.sub(point((a+b)/2),o['center']),1/w))
        result.append(([point(a),middle,point(b)],[1.,w,1.]))
    return result


def _point(points,weights,u):
    numerator=s._bezier_point([g.mul(p,w) for p,w in zip(points,weights)],u)
    denominator=s._bezier_point([[w,0] for w in weights],u)[0]
    return g.mul(numerator,1/denominator)


def _implicit(implicit,curve):
    result=[]; parts=spans(curve)
    for i,(points,weights) in enumerate(parts):
        if implicit['type']=='line':
            v=g.sub(implicit['b'],implicit['a'])
            coeffs=[g.cross(g.sub(p,implicit['a']),v)*w for p,w in zip(points,weights)]
            magnitude=max(abs(x) for x in coeffs)
        else:
            c=implicit['center']; angle=implicit.get('angle',0.); ca,sa=math.cos(angle),math.sin(angle)
            rx,ry=(implicit['rx'],implicit['ry']) if implicit['type']=='ellipse' else (implicit['radius'],implicit['radius'])
            x=[]; y=[]
            for p,w in zip(points,weights):
                dx,dy=g.sub(p,c); x.append((ca*dx+sa*dy)*w/rx); y.append((-sa*dx+ca*dy)*w/ry)
            xx=s._bernstein_product(x,x); yy=s._bernstein_product(y,y); ww=s._bernstein_product(weights,weights)
            coeffs=[a+b-c for a,b,c in zip(xx,yy,ww)]
            magnitude=max(abs(v) for v in xx+yy+ww)
        scale=max(abs(x) for x in coeffs)
        if scale<=max(1e-300,1e-12*magnitude): continue
        for u in s._bernstein_roots([x/scale for x in coeffs]):
            p=_point(points,weights,u); ta=parameter(implicit,p)
            tb=(i+u)/len(parts) if curve['type']=='spline' else parameter(curve,p)
            if ta is not None and tb is not None: result.append((ta,tb,p))
    return result


def _spline_pair(a,b):
    pa=s._spline_spans(a); pb=s._spline_spans(b); result=[]; work=0
    def box(p): return [min(q[0] for q in p),min(q[1] for q in p),max(q[0] for q in p),max(q[1] for q in p)]
    def diagonal(v): return math.hypot(v[2]-v[0],v[3]-v[1])
    for ia,aa in enumerate(pa):
        for ib,bb in enumerate(pb):
            if len(aa)==len(bb) and (all(g.dist(x,y)<1e-10 for x,y in zip(aa,bb)) or all(g.dist(x,y)<1e-10 for x,y in zip(aa,reversed(bb)))): continue
            # Collinear coincident spans do not define isolated cutting contacts.
            direction=g.sub(aa[-1],aa[0])
            if math.hypot(*direction)>g.EPS and all(abs(g.cross(g.sub(p,aa[0]),g.unit(direction)))<1e-10 for p in aa+bb): continue
            extent=max(1.,diagonal(box(aa)),diagonal(box(bb)))
            tol=1e-9*extent; leaf=math.sqrt(tol*extent)
            for u in (0.,1.):
                for v in (0.,1.):
                    q,r=s._bezier_point(aa,u),s._bezier_point(bb,v)
                    if g.dist(q,r)<tol: result.append(((ia+u)/len(pa),(ib+v)/len(pb),g.mul(g.add(q,r),.5)))
            stack=[(aa,0.,1.,bb,0.,1.)]
            da=[g.mul(g.sub(y,x),len(aa)-1) for x,y in zip(aa,aa[1:])]
            db=[g.mul(g.sub(y,x),len(bb)-1) for x,y in zip(bb,bb[1:])]
            while stack:
                work+=1
                if work>100000: raise ValueError('Overlapping or excessively complex spline boundaries cannot define a reliable trim.')
                x,lo,hi,y,low,high=stack.pop(); bx,by=box(x),box(y)
                if any(bx[k]>by[k+2]+tol or by[k]>bx[k+2]+tol for k in (0,1)): continue
                dx,dy=diagonal(bx),diagonal(by)
                if max(dx,dy)<leaf or max(hi-lo,high-low)<1e-12:
                    u,v=(lo+hi)/2,(low+high)/2
                    for _ in range(35):
                        q,r=s._bezier_point(aa,u),s._bezier_point(bb,v)
                        du,dv=s._bezier_point(da,u),s._bezier_point(db,v); det=g.cross(du,dv)
                        if abs(det)<1e-18*max(1.,math.hypot(*du)*math.hypot(*dv)): break
                        gap=g.sub(r,q)
                        un=max(0,min(1,u+g.cross(gap,dv)/det)); vn=max(0,min(1,v+g.cross(gap,du)/det))
                        if abs(un-u)+abs(vn-v)<1e-14: u,v=un,vn; break
                        u,v=un,vn
                    q,r=s._bezier_point(aa,u),s._bezier_point(bb,v)
                    if g.dist(q,r)<tol*4: result.append(((ia+u)/len(pa),(ib+v)/len(pb),g.mul(g.add(q,r),.5)))
                elif dx>=dy:
                    left,right=split(x,.5); mid=(lo+hi)/2
                    stack.extend([(left,lo,mid,y,low,high),(right,mid,hi,y,low,high)])
                else:
                    left,right=split(y,.5); mid=(low+high)/2
                    stack.extend([(x,lo,hi,left,low,mid),(x,lo,hi,right,mid,high)])
    return result


def crossings(a,b):
    if a['type']=='polygon':
        return [(0.,tb,p) for points,_ in spans(a) for _,tb,p in crossings({'type':'line','a':points[0],'b':points[1]},b)]
    if b['type']=='polygon':
        return [(ta,0.,p) for points,_ in spans(b) for ta,_,p in crossings(a,{'type':'line','a':points[0],'b':points[1]})]
    if a['type']=='spline' and a['method']=='bezier' and len(a['points'])==2:
        result=_implicit({'type':'line','a':a['points'][0],'b':a['points'][1]},b)
    elif b['type']=='spline' and b['method']=='bezier' and len(b['points'])==2:
        result=[(tb,ta,p) for ta,tb,p in _implicit({'type':'line','a':b['points'][0],'b':b['points'][1]},a)]
    elif a['type'] in ('line','circle','arc','ellipse'): result=_implicit(a,b)
    elif b['type'] in ('line','circle','arc','ellipse'): result=[(tb,ta,p) for ta,tb,p in _implicit(b,a)]
    else: result=_spline_pair(a,b)
    unique=[]
    for ta,tb,p in result:
        if not any(abs(ta-u)<1e-7 and abs(tb-v)<1e-7 for u,v,_ in unique): unique.append((ta,tb,p))
    return unique
