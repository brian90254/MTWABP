"""Transient recent object snap locations and coordinate alignment guides and snaps."""
import math

OBJECT_SNAPS={'endpoint','midpoint','center','quadrant','radius handle','through point',
              'axis endpoint','vertex','control point','fit point','tangent',
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
