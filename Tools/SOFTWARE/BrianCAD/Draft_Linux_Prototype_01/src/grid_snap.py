"""Fixed-spacing grid and alignment helpers."""
import math
from fractions import Fraction
from cad_geometry import dist as distance
def grid_values(spacing, subdivisions):
    """Validate dialog values; a subdivision is one division of a major interval."""
    try:
        spacing = float(Fraction(str(spacing).strip().rstrip('"').strip()))
        divisions = float(subdivisions)
    except (ValueError, TypeError, ZeroDivisionError, OverflowError):
        raise ValueError('Enter a positive spacing in inches and a whole subdivision count.')
    if not math.isfinite(spacing) or not 1e-6 <= spacing <= 1e7:
        raise ValueError('Grid spacing must be between 0.000001 and 10,000,000 inches.')
    if not math.isfinite(divisions) or not divisions.is_integer() or not 1 <= divisions <= 100:
        raise ValueError('Subdivisions must be a whole number from 1 to 100.')
    return spacing, int(divisions)


def grid_candidates(p, step):
    """Nearest intersection, vertical grid line, and horizontal grid line."""
    x, y = (round(v / step) * step for v in p)
    return [([x, y], 'grid intersection'), ([x, p[1]], 'vertical grid line'),
            ([p[0], y], 'horizontal grid line')]


def line_grid_candidates(p, obj, step):
    """Nearest segment/grid crossing in each grid direction, without enumeration.

    Project onto the infinite line first. Rounding its coordinate to a grid
    multiple, clamped to the segment's crossing range, gives the nearest
    crossing in that direction. This remains bounded even for very fine grids.
    """
    a, b = obj['a'], obj['b']
    d = [b[i]-a[i] for i in (0, 1)]
    length2 = sum(v*v for v in d)
    if length2 == 0:
        return []
    t = sum((p[i]-a[i])*d[i] for i in (0, 1)) / length2
    result = []
    for axis in (0, 1):
        if d[axis] == 0:
            continue
        low, high = sorted((a[axis]/step, b[axis]/step))
        first, last = math.ceil(low-1e-10), math.floor(high+1e-10)
        if first > last:
            continue
        k = max(first, min(last, round((a[axis]+t*d[axis])/step)))
        u = (k*step-a[axis])/d[axis]
        if -1e-10 <= u <= 1+1e-10:
            q = [a[i]+max(0, min(1, u))*d[i] for i in (0, 1)]
            q[axis] = k*step
            result.append((q, 'line/grid intersection'))
    return result


def alignment_candidates(p, start):
    dx, dy = p[0]-start[0], p[1]-start[1]
    plus, minus = (dx+dy)/2, (dx-dy)/2
    return [([p[0], start[1]], 'horizontal'),
            ([start[0], p[1]], 'vertical'),
            ([start[0]+plus, start[1]+plus], '45°'),
            ([start[0]+minus, start[1]-minus], '135°')]


def grid_positions(low, high, step, scale, min_pixels):
    """Cull dense lines for display only; snapping always uses the actual step."""
    if step*scale < min_pixels:
        return range(0)
    return range(math.ceil(low/step), math.floor(high/step)+1)


