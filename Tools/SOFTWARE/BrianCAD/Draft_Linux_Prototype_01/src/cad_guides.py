"""Construction directions through a shared endpoint and local intersection targets."""
import cad_geometry as g
from curve_trim import crossings
from grid_snap import line_grid_candidates

ENDPOINT_TOLERANCE=1e-6

def directions(start,lines):
    result=[]
    for line in lines:
        if line['type']!='line':continue
        if min(g.dist(start,line[k]) for k in ('a','b'))>ENDPOINT_TOLERANCE:continue
        direction=g.unit(g.sub(line['b'],line['a']))
        for vector,label in ((direction,'extension guide'),(g.normal(direction),'perpendicular guide')):
            if not any(abs(g.cross(vector,v))<1e-10 and label==old for v,old in result):
                result.append((vector,label))
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
