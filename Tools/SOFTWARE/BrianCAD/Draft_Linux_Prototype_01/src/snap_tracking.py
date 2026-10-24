"""Transient recent object snap locations and visual coordinate guides."""
import math

OBJECT_SNAPS={'endpoint','midpoint','center','quadrant','radius handle','through point',
              'axis endpoint','vertex','control point','fit point','tangent',
              'intersection','line/grid intersection'}


class SnapHistory:
    def __init__(self): self.points=[]

    def clear(self): self.points.clear()

    def remember(self,point,label):
        if point is None or label not in OBJECT_SNAPS: return
        # Revisiting a point makes it most recent, without using another slot.
        self.points=[p for p in self.points if math.dist(p,point)>1e-9]
        self.points.insert(0,list(point))
        del self.points[4:]

    def guides(self,cursor,scale):
        if cursor is None: return []
        result=[]
        for axis in (0,1):
            coordinates=[]
            for p in self.points:
                value=p[axis]
                if abs(cursor[axis]-value)*scale<=6 and not any(abs(value-v)<1e-9 for v in coordinates):
                    coordinates.append(value)
                    result.append((axis,value))
        return result
