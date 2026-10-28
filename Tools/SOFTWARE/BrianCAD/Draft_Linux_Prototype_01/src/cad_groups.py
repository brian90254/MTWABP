"""Flat persistent group identities and endpoint-based closed-boundary recognition."""
import copy
import math
import uuid
import cad_geometry as g

TOLERANCE=1e-6


def new_id(): return uuid.uuid4().hex


def remap(objects):
    """Copies/imports get independent identities, retaining membership within the copy."""
    mapping={};result=copy.deepcopy(objects)
    for obj in result:
        if obj.get('group'):
            original=obj['group']
            if original not in mapping:mapping[original]=new_id()
            obj['group']=mapping[original]
    return result


def endpoints(o):
    kind=o['type']
    if kind=='line':return o['a'],o['b']
    if kind=='polygon':return o['points'][0],o['points'][0] if o.get('closed',True) else o['points'][-1]
    if kind=='circle':return g.polar(o['center'],o['radius'],0),g.polar(o['center'],o['radius'],0)
    if kind=='arc':return tuple(g.polar(o['center'],o['radius'],o['start']+o['sweep']*t) for t in (0,1))
    if kind=='ellipse':return g.ellipse_point(o,0),g.ellipse_point(o,1)
    return g.spline_point(o,0),g.spline_point(o,1)


def is_closed(objects):
    """One endpoint-connected, unbranched loop; closed does not imply no crossings."""
    if not objects:return False
    pairs=[endpoints(o) for o in objects]
    if len(pairs)==1:return g.dist(*pairs[0])<=TOLERANCE
    if any(g.dist(a,b)<=TOLERANCE for a,b in pairs):return False
    nodes=[];adj=[];buckets={}
    for edge,pair in enumerate(pairs):
        for point in pair:
            cell=tuple(math.floor(v/TOLERANCE) for v in point)
            matches=[i for dx in (-1,0,1) for dy in (-1,0,1) for i in buckets.get((cell[0]+dx,cell[1]+dy),[])
                     if g.dist(point,nodes[i])<=TOLERANCE]
            if len(matches)>1:return False
            if matches:i=matches[0]
            else:
                i=len(nodes);nodes.append(point);adj.append([]);buckets.setdefault(cell,[]).append(i)
            adj[i].append(edge)
    if any(len(edges)!=2 for edges in adj):return False
    edge_nodes={}
    for i,edges in enumerate(adj):
        for edge in edges:edge_nodes.setdefault(edge,[]).append(i)
    seen={0};stack=[0]
    while stack:
        for node in edge_nodes[stack.pop()]:
            for edge in adj[node]:
                if edge not in seen:seen.add(edge);stack.append(edge)
    return len(seen)==len(objects)
