"""Construction directions through a shared endpoint and local intersection targets."""
import cad_geometry as g
from curve_trim import crossings
from grid_snap import line_grid_candidates

ENDPOINT_TOLERANCE=1e-6

def directions(start,objects):
    """Local tangents/normals at finite curve contacts; include both vertex edges."""
    from cad_selection import nearest_point,_spline_spans
    from cad_chamfer import evaluate,_PreparedCurve
    from curve_trim import parameter
    result=[]
    def add(vector,label):
        if g.dist([0,0],vector)<g.EPS:return
        vector=g.unit(vector)
        if not any(abs(g.cross(vector,v))<1e-10 and label==old for v,old in result):
            result.append((vector,label))
    for obj in objects:
        kind=obj['type']
        if kind in ('line','polygon'):
            pts=g.path(obj)
            for a,b in zip(pts,pts[1:]):
                if g.dist(a,b)<g.EPS or g.dist(start,g.project(start,a,b,True))>ENDPOINT_TOLERANCE:continue
                vector=g.sub(b,a)
                add(vector,'extension guide');add(g.normal(vector),'perpendicular guide')
        elif kind in ('circle','arc','ellipse','spline'):
            q=nearest_point(start,obj)
            if g.dist(start,q)>ENDPOINT_TOLERANCE:continue
            t=parameter(obj,q)
            if t is None:continue
            _,vector=evaluate(_PreparedCurve(obj),t)
            # Repeated Bézier endpoint handles can yield a zero first derivative.
            if kind=='spline' and g.dist([0,0],vector)<g.EPS and (t<1e-8 or t>1-1e-8):
                points=_spline_spans(obj)[0 if t<.5 else -1]
                if t>.5:points=list(reversed(points))
                vector=next((g.sub(p,points[0]) for p in points[1:] if g.dist(p,points[0])>=g.EPS),[0,0])
            add(vector,'tangent guide');add(g.normal(vector),'perpendicular guide')
    return result


def targets(start,guides,cursor,tolerance,objects,step=None,axes=()):
    hits=[];projections=[]
    for direction,label in guides:
        q=g.add(start,g.mul(direction,g.dot(g.sub(cursor,start),direction)))
        if g.dist(q,cursor)>tolerance:continue
        projections.append((q,label))
        delta=g.mul(direction,2*tolerance)
        segment=dict(type='line',a=g.sub(q,delta),b=g.add(q,delta))
        hits.extend((point,label+' / object intersection') for obj in objects for _,_,point in crossings(segment,obj))
        if step is not None:
            hits.extend((point,label+' / grid intersection') for point,_ in line_grid_candidates(cursor,segment,step))
        for axis,value in axes:
            if abs(direction[axis])>1e-12:
                point=g.add(q,g.mul(direction,(value-q[axis])/direction[axis]))
                hits.append((point,label+' / alignment intersection'))
    for i,(a,_) in enumerate(guides):
        if any(abs(g.cross(a,b))>1e-10 for b,_ in guides[i+1:]):
            hits.append((start,'guide intersection'));break
    return hits,projections
