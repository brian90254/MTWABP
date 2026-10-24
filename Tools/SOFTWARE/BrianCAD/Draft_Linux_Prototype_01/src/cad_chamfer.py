"""Radius-defined tangent corner arcs (fillets), called Chamfer in the toolbox."""
import math
import cad_geometry as g
import cad_selection as s
from cad_trim import fragments
from curve_trim import crossings, parameter

SUPPORTED={'line','circle','arc','ellipse','spline'}


class _PreparedCurve(dict):
    def __init__(self,source):
        super().__init__(source)
        self.parts=s._spline_spans(source) if source['type']=='spline' else None


def evaluate(o,t):
    kind=o['type']
    if kind=='line':
        d=g.sub(o['b'],o['a']); return g.add(o['a'],g.mul(d,t)),d
    if kind=='spline':
        spans=getattr(o,'parts',None) or s._spline_spans(o); u=min(max(t,0)*len(spans),len(spans)-1e-14); i=int(u); u-=i
        span=spans[i]; d=[g.mul(g.sub(b,a),len(span)-1) for a,b in zip(span,span[1:])]
        return s._bezier_point(span,u),g.mul(s._bezier_point(d,u),len(spans))
    sweep=o.get('sweep',g.TAU); a=o.get('start',0.)+sweep*t
    if kind=='ellipse':
        ca,sa=math.cos(o['angle']),math.sin(o['angle'])
        x,y=-o['rx']*math.sin(a)*sweep,o['ry']*math.cos(a)*sweep
        return g.ellipse_point(o,t),[ca*x-sa*y,sa*x+ca*y]
    return g.polar(o['center'],o['radius'],a),g.mul([-math.sin(a),math.cos(a)],o['radius']*sweep)


def _offset(o,t,r,sign):
    p,d=evaluate(o,t)
    if math.hypot(*d)<g.EPS: return None
    return g.add(p,g.mul(g.normal(g.unit(d)),r*sign))


def _offset_derivative(o,t,r,sign):
    a,b=max(0,t-1e-5),min(1,t+1e-5)
    p,q=_offset(o,a,r,sign),_offset(o,b,r,sign)
    return g.mul(g.sub(q,p),1/(b-a)) if p is not None and q is not None else None


def _refine(a,b,r,sa,sb,u,v):
    tolerance=1e-10*max(1e-3,r)
    for _ in range(60):
        x,y=_offset(a,u,r,sa),_offset(b,v,r,sb)
        if x is None or y is None: return None
        gap=g.sub(y,x); error=math.hypot(*gap)
        if error<tolerance: return u,v,g.mul(g.add(x,y),.5)
        du,dv=_offset_derivative(a,u,r,sa),_offset_derivative(b,v,r,sb)
        if du is None or dv is None: return None
        det=g.cross(du,dv)
        if abs(det)<1e-14*max(1.,math.hypot(*du)*math.hypot(*dv)): return None
        step_u=g.cross(gap,dv)/det; step_v=g.cross(gap,du)/det
        improved=False
        for k in range(10):
            f=2.**(-k); un=max(0,min(1,u+f*step_u)); vn=max(0,min(1,v+f*step_v))
            xn,yn=_offset(a,un,r,sa),_offset(b,vn,r,sb)
            if xn is not None and yn is not None and g.dist(xn,yn)<error:
                u,v=un,vn; improved=True; break
        if not improved: return None
    return None


def _centers(a,b,r,picks):
    a,b=_PreparedCurve(a),_PreparedCurve(b)
    def count(o): return max(32,min(256,16*len(o.parts))) if o['type']=='spline' else (1 if o['type']=='line' else 96)
    na,nb=count(a),count(b); results=[]
    for sa in (-1,1):
        aa=[_offset(a,i/na,r,sa) for i in range(na+1)]
        for sb in (-1,1):
            bb=[_offset(b,i/nb,r,sb) for i in range(nb+1)]
            seeds=[picks]
            for i,(x,y) in enumerate(zip(aa,aa[1:])):
                if x is None or y is None: continue
                dx=g.sub(y,x)
                for j,(p,q) in enumerate(zip(bb,bb[1:])):
                    if p is None or q is None: continue
                    if any(max(x[k],y[k])+1e-10<min(p[k],q[k]) or max(p[k],q[k])+1e-10<min(x[k],y[k]) for k in (0,1)): continue
                    dy=g.sub(q,p); det=g.cross(dx,dy)
                    if abs(det)<1e-16*max(1.,math.hypot(*dx)*math.hypot(*dy)): continue
                    gap=g.sub(p,x); u=g.cross(gap,dy)/det; v=g.cross(gap,dx)/det
                    if -1e-9<=u<=1+1e-9 and -1e-9<=v<=1+1e-9: seeds.append(((i+u)/na,(j+v)/nb))
            # Coarse nearest seeds also catch tangencies between the two offsets.
            coarse_a=sorted(set([round(i*na/12) for i in range(13)]))
            coarse_b=sorted(set([round(i*nb/12) for i in range(13)]))
            nearest=sorted((g.dist(aa[i],bb[j]),i/na,j/nb) for i in coarse_a for j in coarse_b if aa[i] is not None and bb[j] is not None)
            seeds.extend((u,v) for _,u,v in nearest[:8])
            for u,v in seeds:
                found=_refine(a,b,r,sa,sb,u,v)
                if found and not any(g.dist(found[2],old[2])<1e-7*max(1,r) and abs(found[0]-old[0])<1e-6 and abs(found[1]-old[1])<1e-6 for old in results): results.append(found)
    return results


def _closed(o):
    return o['type']=='circle' or (o['type'] in ('arc','ellipse') and abs(abs(o.get('sweep',g.TAU))-g.TAU)<1e-9) or (o['type']=='spline' and o.get('closed',False))


def _retain(o,t,direction,pick,corners):
    if _closed(o):
        distances=[((c-t)*direction)%1 for c in corners]
        distances=[d for d in distances if d>1e-7]
        if not distances: return None
        length=min(distances)
        if ((pick-t)*direction)%1>length+1e-6: return None
        return fragments(o,t,t+length) if direction>0 else fragments(o,t-length,t)
    if (pick-t)*direction < -1e-6: return None
    lo,hi=(t,1.) if direction>0 else (0.,t)
    if hi-lo<1e-9: return None
    pieces=fragments(o,lo,hi)
    return pieces or None


def chamfer(a,b,click_a,click_b,radius):
    """Retained source pieces and a tangent minor arc, chosen by clicks on keep sides."""
    if a['type'] not in SUPPORTED or b['type'] not in SUPPORTED: raise ValueError('Choose two line or curve segments.')
    if isinstance(radius,bool) or not isinstance(radius,(int,float)) or not math.isfinite(radius) or not 1e-6<=radius<=1e7: raise ValueError('Radius must be between 0.000001 and 10,000,000 inches.')
    ta,tb=parameter(a,click_a),parameter(b,click_b)
    if ta is None or tb is None: raise ValueError('Click directly on the two segments.')
    original=crossings(a,b) if _closed(a) or _closed(b) else []
    candidates=[]
    for u,v,center in _centers(a,b,radius,(ta,tb)):
        p,dp=evaluate(a,u); q,dq=evaluate(b,v)
        if g.dist(p,q)<1e-8*max(1,radius): continue
        start=g.angle(center,p); sweep=(g.angle(center,q)-start+math.pi)%g.TAU-math.pi
        sweeps=[sweep,-sweep] if abs(abs(sweep)-math.pi)<1e-7 else [sweep]
        for turn in sweeps:
            if abs(turn)<1e-8: continue
            direction=1 if turn>0 else -1
            tangent_a=g.mul(g.normal(g.sub(p,center)),direction)
            tangent_b=g.mul(g.normal(g.sub(q,center)),direction)
            da=1 if g.dot(dp,tangent_a)<0 else -1
            db=1 if g.dot(dq,tangent_b)>0 else -1
            try:
                kept_a=_retain(a,u,da,ta,[x for x,_,_ in original])
                kept_b=_retain(b,v,db,tb,[y for _,y,_ in original])
            except ValueError:
                continue
            if not kept_a or not kept_b: continue
            arc={'type':'arc','center':center,'radius':radius,'start':start,'sweep':turn}
            # Refinement must satisfy the requested radius and true tangent directions.
            if max(abs(g.dist(p,center)-radius),abs(g.dist(q,center)-radius))>1e-7*max(1,radius): continue
            if abs(g.dot(g.unit(dp),g.unit(g.sub(p,center))))>1e-6 or abs(g.dot(g.unit(dq),g.unit(g.sub(q,center))))>1e-6: continue
            score=g.dist(p,click_a)+g.dist(q,click_b)
            candidates.append((score,kept_a,kept_b,g.validate_geometry(arc)))
    if not candidates: raise ValueError('No tangent arc of this radius fits the selected segments and keep sides. Try a smaller radius or click farther along the sides to keep; closed curves need an existing corner intersection.')
    _,kept_a,kept_b,arc=min(candidates,key=lambda value:value[0])
    return kept_a,kept_b,arc
