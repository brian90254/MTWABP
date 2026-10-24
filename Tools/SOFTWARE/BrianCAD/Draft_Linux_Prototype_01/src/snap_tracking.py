"""Transient recent object snap locations and coordinate alignment guides and snaps."""
import math
from cad_selection import axis_intersections, bounds

OBJECT_SNAPS={'endpoint','midpoint','center','quadrant','radius handle','through point',
              'axis endpoint','vertex','control point','fit point','tangent','perpendicular',
              'intersection'}


class SnapHistory:
    def __init__(self): self.points=[]

    def clear(self): self.points.clear()

    def remember(self,point,label):
        if point is None or label not in OBJECT_SNAPS: return
        # Revisiting a point makes it most recent, without using another slot.
        self.points=[p for p in self.points if math.dist(p,point)>1e-9]
        self.points.insert(0,list(point))
        del self.points[4:]

    def snap(self,cursor,scale,exclude=()):
        """Nearest remembered coordinate per axis, within the guide tolerance."""
        target=list(cursor); axes=[]
        points=[p for p in self.points if not any(math.dist(p,q)<1e-9 for q in exclude)]
        for axis in (0,1):
            best=min(points,key=lambda p:abs(p[axis]-cursor[axis]),default=None)
            if best is not None and abs(best[axis]-cursor[axis])*scale<=6:
                target[axis]=best[axis]; axes.append('align x' if axis==0 else 'align y')
        return (target,' + '.join(axes)) if axes else None

    def crossings(self,cursor,scale,objects=(),step=None,exclude=(),bounds_fn=bounds):
        """Point targets where each active guide meets geometry/grid/another guide."""
        guides=self.guides(cursor,scale,exclude); result=[]; tolerance=9/scale
        if not guides: return result
        object_boxes=[(obj,bounds_fn(obj)) for obj in objects]
        for axis,value in guides:
            label='align x' if axis==0 else 'align y'
            for obj,box in object_boxes:
                if not box[axis]-1e-10<=value<=box[axis+2]+1e-10: continue
                if not box[1-axis]-tolerance<=cursor[1-axis]<=box[3-axis]+tolerance: continue
                result.extend((q,label+' / object intersection') for q in axis_intersections(obj,axis,value))
        for x in [v for axis,v in guides if axis==0]:
            for y in [v for axis,v in guides if axis==1]:
                result.append(([x,y],'align x + align y'))
        if step is not None:
            for axis,value in guides:
                q=list(cursor); q[axis]=value; q[1-axis]=round(cursor[1-axis]/step)*step
                result.append((q,('align x' if axis==0 else 'align y')+' / grid intersection'))
        return [(q,label) for q,label in result if math.dist(q,cursor)<=tolerance]

    def guides(self,cursor,scale,exclude=()):
        if cursor is None: return []
        result=[]
        for axis in (0,1):
            coordinates=[]
            for p in self.points:
                if any(math.dist(p,q)<1e-9 for q in exclude): continue
                value=p[axis]
                if abs(cursor[axis]-value)*scale<=6 and not any(abs(value-v)<1e-9 for v in coordinates):
                    coordinates.append(value)
                    result.append((axis,value))
        return result
