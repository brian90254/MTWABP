"""Shape-preserving equal-length division of individual drawing objects."""
import bisect
import copy
import math
import cad_geometry as g
import cad_groups
from cad_chamfer import evaluate,_PreparedCurve
from cad_trim import fragment
from curve_trim import spline_fragments


def segment_count(value):
    try:
        if isinstance(value,bool):raise ValueError()
        number=float(value)
        if not math.isfinite(number) or not number.is_integer() or not 2<=number<=1000:raise ValueError()
    except (ValueError,TypeError,OverflowError):raise ValueError('Enter a whole number of segments from 2 to 1000.')
    return int(number)


class CurveLength:
    """Adaptive speed integration and inversion, seeded across each spline span."""
    def __init__(self,obj):
        self.obj=_PreparedCurve(obj);self.calls=0;self.intervals=[]
        spans=self.obj.parts
        seeds=sum(max(8,2*(len(span)-1)) for span in spans) if spans else 16
        rough=sum(g.dist(evaluate(self.obj,i/seeds)[0],evaluate(self.obj,(i+1)/seeds)[0]) for i in range(seeds))
        self.tolerance=max(1e-13,1e-9*rough)
        for i in range(seeds):self.integral(i/seeds,(i+1)/seeds,self.tolerance/seeds,self.intervals)
        self.ends=[];total=0.
        for a,b,length in self.intervals:total+=length;self.ends.append(total)
        self.total=total
        if total<g.EPS:raise ValueError('This curve is too short to divide.')

    def speed(self,t):
        self.calls+=1
        if self.calls>2000000:raise ValueError('Curve is too complex to divide accurately.')
        return math.hypot(*evaluate(self.obj,t)[1])

    def integral(self,a,b,tolerance,collect=None):
        if b<=a:return 0.
        f=self.speed;mid=(a+b)/2;fa,fm,fb=f(a),f(mid),f(b)
        whole=(b-a)*(fa+4*fm+fb)/6
        def refine(a,b,fa,fm,fb,whole,tol,depth):
            m=(a+b)/2;fl=f((a+m)/2);fr=f((m+b)/2)
            left=(m-a)*(fa+4*fl+fm)/6;right=(b-m)*(fm+4*fr+fb)/6
            error=left+right-whole
            if abs(error)<=15*tol:
                length=max(0.,left+right+error/15)
                if collect is not None:collect.append((a,b,length))
                return length
            if depth>=24:raise ValueError('Curve length could not be resolved; try fewer segments.')
            return refine(a,m,fa,fl,fm,left,tol/2,depth+1)+refine(m,b,fm,fr,fb,right,tol/2,depth+1)
        return refine(a,b,fa,fm,fb,whole,tolerance,0)

    def parameter(self,length):
        index=min(bisect.bisect_right(self.ends,length),len(self.intervals)-1)
        a,b,size=self.intervals[index];target=length-(self.ends[index-1] if index else 0.)
        low,high=a,b;t=a+(b-a)*target/size if size else a
        for _ in range(50):
            error=self.integral(a,t,self.tolerance/20)-target
            if abs(error)<=self.tolerance/5:return t
            if error>0:high=t
            else:low=t
            speed=self.speed(t);candidate=t-error/speed if speed>1e-14 else (low+high)/2
            t=candidate if low<candidate<high else (low+high)/2
        raise ValueError('Could not locate a division point accurately.')


def _independent(parts):
    """Discard old selection groups; a multi-span section is its own new group."""
    group=cad_groups.new_id() if len(parts)>1 else None
    for part in parts:
        part.pop('group',None)
        if group:part['group']=group
        g.validate_geometry(part)
    return parts


def _polygon_sections(obj,count):
    points=g.path(obj);edges=[];total=0.
    for a,b in zip(points,points[1:]):
        length=g.dist(a,b)
        if length>0:edges.append((total,total+length,a,b));total+=length
    if total<g.EPS:raise ValueError('This polygon is too short to divide.')
    base=copy.deepcopy(obj);base.pop('points');base.pop('closed',None);sections=[]
    for i in range(count):
        lo=total*i/count;hi=total*(i+1)/count;piece=[]
        for start,end,a,b in edges:
            x=max(start,lo);y=min(end,hi)
            if y<=x:continue
            vector=g.sub(b,a)
            p=g.add(a,g.mul(vector,(x-start)/(end-start)));q=g.add(a,g.mul(vector,(y-start)/(end-start)))
            if not piece:piece.append(p)
            if g.dist(piece[-1],q)>0:piece.append(q)
        if len(piece)<2:raise ValueError('Segments are too small; choose fewer divisions.')
        if len(piece)==2:parts=[dict(base,type='line',a=piece[0],b=piece[1])]
        elif len(piece)<=200:parts=[dict(base,type='polygon',points=piece,closed=False)]
        else:parts=[dict(base,type='line',a=a,b=b) for a,b in zip(piece,piece[1:])]
        sections.append(_independent(parts))
    return sections


def divide_object(obj,count):
    """Return exactly count logical sections; multi-span sections contain grouped parts."""
    count=segment_count(count);kind=obj['type']
    if kind=='polygon':return _polygon_sections(obj,count)
    if kind in ('line','circle','arc'):cuts=[i/count for i in range(count+1)]
    elif kind in ('ellipse','spline'):
        measure=CurveLength(obj);cuts=[0.]+[measure.parameter(measure.total*i/count) for i in range(1,count)]+[1.]
    else:raise ValueError('Unsupported geometry for Divide.')
    source=copy.deepcopy(obj)
    if kind=='circle':source['start']=source.get('handle_angle',0.)
    sections=[]
    for a,b in zip(cuts,cuts[1:]):
        parts=spline_fragments(source,a,b) if kind=='spline' else [fragment(source,a,b)]
        if not parts:raise ValueError('Segments are too small; choose fewer divisions.')
        sections.append(_independent(parts))
    return sections
