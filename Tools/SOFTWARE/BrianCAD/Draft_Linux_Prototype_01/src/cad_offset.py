"""Exact primitive offsets and topology-aware offsets of sampled connected curves."""
import copy
import math
from pathlib import Path
import shlex
import sys
import cad_geometry as g
from cad_chamfer import evaluate,_PreparedCurve
from cad_selection import nearest_point

TOLERANCE=1e-4  # inches: source-curve chord sampling criterion
JOIN_TOLERANCE=1e-6
SUPPORTED={'line','circle','arc','ellipse','spline','polygon'}


def require_shapely():
    try:
        import shapely
        if not hasattr(shapely,'offset_curve'): raise ImportError('Shapely 2 is required')
    except ImportError as ex:
        path=Path(__file__).resolve().parent.parent/'requirements-offset.txt'
        cmd=f'{shlex.quote(sys.executable)} -m pip install -r {shlex.quote(str(path))}'
        raise ValueError('Connected/general curve offsets require the optional Shapely package. Install with:\n'+cmd) from ex
    return shapely


def _closed(o):
    return (o['type']=='circle' or o['type']=='polygon' and o.get('closed',True) or o['type']=='spline' and o.get('closed',False) and (o.get('method')!='bezier' or g.dist(o['points'][0],o['points'][-1])<=JOIN_TOLERANCE)
            or o['type'] in ('arc','ellipse') and abs(o.get('sweep',g.TAU))>=g.TAU-1e-10)


def sample(o):
    if o['type']=='polygon': return [list(p) for p in o['points']]+([list(o['points'][0])] if _closed(o) else [])
    if o['type']=='line': return [list(o['a']),list(o['b'])]
    prepared=_PreparedCurve(o);points=[]
    # Start with multiple spans to detect loops and S shapes; refine at quarter points.
    parts=len(prepared.parts) if prepared.parts else 1
    count=max(16,parts*4)
    def refine(a,b,pa,pb,depth):
        mids=[evaluate(prepared,a+(b-a)*f)[0] for f in (.25,.5,.75)]
        error=max(g.dist(p,g.project(p,pa,pb,True)) for p in mids)
        if error<=TOLERANCE:
            points.append(list(pb));return
        if depth>=24 or len(points)>20000: raise ValueError('Curve is too complex to offset at the sampling tolerance.')
        m=(a+b)/2;refine(a,m,pa,mids[1],depth+1);refine(m,b,mids[1],pb,depth+1)
    points.append(list(evaluate(prepared,0)[0]))
    for i in range(count):
        a=i/count;b=(i+1)/count
        refine(a,b,evaluate(prepared,a)[0],evaluate(prepared,b)[0],0)
        if len(points)>20000: raise ValueError('Curve is too complex to offset.')
    if _closed(o): points[-1]=list(points[0])
    return points


def connected_path(objects):
    paths=[sample(o) for o in objects]
    if len(paths)==1:return paths[0]
    if any(_closed(o) for o in objects):raise ValueError('Select a single closed curve, or one connected open/closed chain.')
    # Build an endpoint graph. Branches and ambiguous coincident endpoints are rejected.
    nodes=[];ends=[];adj=[];buckets={}
    for index,path in enumerate(paths):
        ids=[]
        for point in (path[0],path[-1]):
            cell=tuple(math.floor(v/JOIN_TOLERANCE) for v in point)
            matches=[i for dx in (-1,0,1) for dy in (-1,0,1)
                     for i in buckets.get((cell[0]+dx,cell[1]+dy),[])
                     if g.dist(point,nodes[i])<=JOIN_TOLERANCE]
            if len(matches)>1:raise ValueError('Ambiguous chain endpoints.')
            if matches:node=matches[0]
            else:
                node=len(nodes);nodes.append(point);adj.append([]);buckets.setdefault(cell,[]).append(node)
            ids.append(node);adj[node].append(index)
        ends.append(ids)
    if any(len(items)>2 for items in adj):raise ValueError('Offset requires an unbranched chain.')
    terminals=[i for i,items in enumerate(adj) if len(items)==1]
    if len(terminals) not in (0,2):raise ValueError('Select one connected chain.')
    current=terminals[0] if terminals else ends[0][0];used=set();result=[]
    while len(used)<len(paths):
        choices=[i for i in adj[current] if i not in used]
        if not choices:raise ValueError('Selected curves are disconnected.')
        i=choices[0];path=paths[i]
        if ends[i][0]!=current:path=list(reversed(path));current=ends[i][0]
        else:current=ends[i][1]
        if result:result.extend(path[1:])
        else:result.extend(path)
        used.add(i)
    if not terminals:result[-1]=list(result[0])
    return result


def _style(o):
    return {key:copy.deepcopy(o[key]) for key in ('layer','color','pattern','weight') if key in o}


def _polylines(shape,style):
    if shape.is_empty:return []
    if shape.geom_type in ('MultiLineString','GeometryCollection'):
        return [o for part in shape.geoms for o in _polylines(part,style)]
    if shape.geom_type not in ('LineString','LinearRing'):raise ValueError('Offset returned an unsupported shape.')
    points=[]
    for q in shape.coords:
        p=list(q[:2])
        if not points or g.dist(points[-1],p)>g.EPS:points.append(p)
    closed=len(points)>2 and g.dist(points[0],points[-1])<g.EPS
    if closed:points.pop()
    if len(points)<2:return []
    if 3<=len(points)<=200:return [dict(type='polygon',points=points,closed=closed,**style)]
    pairs=list(zip(points,points[1:]))
    if closed:pairs.append((points[-1],points[0]))
    return [dict(type='line',a=a,b=b,**style) for a,b in pairs if g.dist(a,b)>g.EPS]


def offset(objects,distance,reference):
    """Return new geometry plus an approximation notice, without changing sources."""
    if not objects:raise ValueError('Select a curve or connected chain before choosing Offset, or click a curve first.')
    if not math.isfinite(distance) or not 1e-6<=distance<=1e7:raise ValueError('Offset distance must be between 0.000001 and 10,000,000 inches.')
    if len(reference)!=2 or not all(math.isfinite(v) and abs(v)<=1e7 for v in reference):raise ValueError('Enter a finite direction X and Y.')
    if any(o.get('type') not in SUPPORTED for o in objects):raise ValueError('Unsupported offset geometry.')
    style=_style(objects[0]);o=objects[0];kind=o['type']
    if len(objects)==1 and kind in ('line','circle','arc'):
        if kind=='line':
            d=g.unit(g.sub(o['b'],o['a']));side=g.cross(d,g.sub(reference,o['a']))
            if abs(side)<JOIN_TOLERANCE:raise ValueError('Choose a direction point off the source curve.')
            shift=g.mul(g.normal(d),math.copysign(distance,side));result=dict(type='line',a=g.add(o['a'],shift),b=g.add(o['b'],shift),**style)
        else:
            if kind=='circle' or _closed(o):side=g.dist(reference,o['center'])-o['radius']
            else:
                q=nearest_point(reference,o);radial=g.unit(g.sub(q,o['center']));side=g.dot(g.sub(reference,q),radial)
            if abs(side)<JOIN_TOLERANCE:raise ValueError('Choose a direction point off the source curve.')
            radius=o['radius']+math.copysign(distance,side)
            if radius<g.EPS:raise ValueError('Offset collapses this circle or arc.')
            result=dict(type=kind,center=list(o['center']),radius=radius,**style)
            if kind=='arc':result.update(start=o['start'],sweep=o['sweep'])
        return [g.validate_geometry(result)],False
    shapely=require_shapely();path=connected_path(objects)
    from shapely.geometry import LineString,Point,Polygon
    line=LineString(path);point=Point(reference)
    if not line.is_simple:raise ValueError('Self-intersecting source chains cannot be offset.')
    if line.distance(point)<JOIN_TOLERANCE:raise ValueError('Choose a direction point off the source curve.')
    closed=g.dist(path[0],path[-1])<=JOIN_TOLERANCE
    if closed:
        polygon=Polygon(path)
        if not polygon.is_valid:raise ValueError('The closed source boundary is not valid.')
        signed=-distance if polygon.contains(point) else distance
        area=polygon.buffer(signed,join_style=2,mitre_limit=5.)
        result=_polylines(area.boundary,style)
    else:
        # Determine the side at the closest segment, independently of chain ordering.
        candidates=[]
        for a,b in zip(path,path[1:]):
            if g.dist(a,b)<g.EPS:continue
            q=g.project(reference,a,b,True);d=g.unit(g.sub(b,a));side=g.cross(d,g.sub(reference,q))
            candidates.append((g.dist(reference,q),side))
        side=min(candidates)[1]
        if abs(side)<JOIN_TOLERANCE:raise ValueError('Direction is ambiguous at an endpoint; choose a point beside the curve.')
        result=_polylines(shapely.offset_curve(line,math.copysign(distance,side),join_style=2,mitre_limit=5.),style)
    if not result:raise ValueError('The requested offset collapses the curve. Try a smaller distance.')
    if len(result)>100000:raise ValueError('Offset result is too complex.')
    for obj in result:g.validate_geometry(obj)
    return result,any(o['type'] not in ('line','polygon') for o in objects)
