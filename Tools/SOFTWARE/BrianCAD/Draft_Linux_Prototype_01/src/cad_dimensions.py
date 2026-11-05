"""Independent, editable dimension annotations. Geometry is stored in inches."""
import math
import cad_geometry as g
from cad_units import display_value

METRICS=('length','horizontal','vertical','angle','diameter','circumference','radius','arc_length')


def annotation(metric,a,b,label,height,sweep=g.TAU):
    return dict(type='dimension',metric=metric,a=list(a),b=list(b),label=list(label),
                text_height=height,sweep=sweep)


def between(a,b,spacing=.35,height=.14):
    if g.dist(a,b)<g.EPS:raise ValueError('Choose two distinct measurement points.')
    mid=g.mul(g.add(a,b),.5);normal=g.normal(g.unit(g.sub(b,a)))
    result=[annotation('length',a,b,g.add(mid,g.mul(normal,spacing)),height)]
    dx,dy=g.sub(b,a)
    if abs(dx)>g.EPS and abs(dy)>g.EPS:
        result.extend([
            annotation('horizontal',a,b,[(a[0]+b[0])/2,min(a[1],b[1])-spacing],height),
            annotation('vertical',a,b,[min(a[0],b[0])-spacing,(a[1]+b[1])/2],height)])
        angle=math.atan2(dy,dx);r=max(4*height,min(g.dist(a,b)*.4,spacing*2))
        result.append(annotation('angle',a,b,g.polar(a,r,angle/2),height))
    return result


def on_object(obj,point,spacing=.35,height=.14):
    kind=obj['type']
    if kind=='line':return between(obj['a'],obj['b'],spacing,height)[:1]
    if kind not in ('circle','arc'):raise ValueError('Single-click dimensions support lines, circles and arcs. Pick two snap points for other curves.')
    c=obj['center'];r=obj['radius'];angle=g.angle(c,point);rim=g.polar(c,r,angle)
    metrics=('diameter','circumference') if kind=='circle' else ('radius','arc_length')
    return [annotation(metric,c,rim,g.polar(c,r+spacing*(i+1),angle+i*.65),height,obj.get('sweep',g.TAU))
            for i,metric in enumerate(metrics)]


def measurement(o):
    metric=o['metric'];a,b=o['a'],o['b'];distance=g.dist(a,b)
    if metric=='horizontal':return abs(b[0]-a[0])
    if metric=='vertical':return abs(b[1]-a[1])
    if metric=='angle':return math.degrees(g.angle(a,b))
    if metric=='diameter':return 2*distance
    if metric=='circumference':return g.TAU*distance
    if metric=='arc_length':return abs(o['sweep'])*distance
    return distance


def text(o,unit='in'):
    value=measurement(o)
    if o['metric']=='angle':return f'{value:.4f}'.rstrip('0').rstrip('.')+'°'
    prefix={'horizontal':'X ','vertical':'Y ','diameter':'Ø ','circumference':'C ',
            'radius':'R ','arc_length':'Arc '}.get(o['metric'],'')
    value=display_value(value,unit)
    number=f'{value:.4f}'.rstrip('0').rstrip('.') if abs(value)>=.0001 else f'{value:.4g}'
    return prefix+number+' '+unit


def layout(o,unit='in'):
    """Return disjoint stroke paths, including geometric arrowheads."""
    a,b=o['a'],o['b'];label=o['label'];h=o['text_height'];metric=o['metric']
    paths=[]
    def segment(a,b):
        if g.dist(a,b)>g.EPS:paths.append([a,b])
    def arrow(tip,direction):
        if math.hypot(*direction)<g.EPS:return
        u=g.unit(direction);v=g.normal(u);base=g.add(tip,g.mul(u,h*.85))
        paths.append([g.add(base,g.mul(v,h*.25)),tip,g.sub(base,g.mul(v,h*.25))])
    if metric in ('length','horizontal','vertical','diameter','radius'):
        if metric=='diameter':a=g.sub(a,g.sub(b,a))
        elif metric=='horizontal':a,b=[a[0],label[1]],[b[0],label[1]]
        elif metric=='vertical':a,b=[label[0],a[1]],[label[0],b[1]]
        if metric in ('horizontal','vertical'):
            for original,end in zip((o['a'],o['b']),(a,b)):
                delta=g.sub(end,original)
                if g.dist(end,original)>g.EPS:segment(original,g.add(end,g.mul(g.unit(delta),h*.5)))
        elif metric=='length':
            u=g.unit(g.sub(b,a));n=g.normal(u);offset=g.dot(g.sub(label,a),n)
            pa,pb=g.add(a,g.mul(n,offset)),g.add(b,g.mul(n,offset))
            for original,end in ((a,pa),(b,pb)):
                delta=g.sub(end,original)
                if g.dist(end,original)>g.EPS:segment(original,g.add(end,g.mul(g.unit(delta),h*.5)))
            a,b=pa,pb
        segment(a,b);arrow(a,g.sub(b,a));arrow(b,g.sub(a,b))
        if metric in ('radius','diameter'):
            segment(b,label)
    elif metric=='angle':
        end=g.angle(a,b);r=max(g.dist(a,label),h*2)
        curve=[g.polar(a,r,end*i/48) for i in range(49)]
        paths.append(curve)
        segment(a,g.polar(a,r+h,0));segment(a,g.polar(a,r+h,end))
        arrow(curve[0],g.sub(curve[1],curve[0]));arrow(curve[-1],g.sub(curve[-2],curve[-1]))
    else:
        segment(b,label);arrow(b,g.sub(label,b))
    return _label_gap(paths,label_bounds(o,unit))


def label_bounds(o,unit='in'):
    # Conservative text bounds for picking, window selection and fit.
    h=o['text_height'];w=max(h,len(text(o,unit))*h*.72);x,y=o['label']
    return [x-w/2,y-h*.7,x+w/2,y+h*.7]


def nearest_point(p,o,unit='in'):
    box=label_bounds(o,unit)
    choices=[[max(box[0],min(box[2],p[0])),max(box[1],min(box[3],p[1]))]]
    choices.extend(g.project(p,a,b,True) for path in layout(o,unit) for a,b in zip(path,path[1:]))
    return min(choices,key=lambda q:g.dist(p,q))


def bounds(o,unit='in'):
    pts=[p for path in layout(o,unit) for p in path];box=label_bounds(o,unit)
    pts.extend([box[:2],box[2:]])
    return [min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)]


def _label_gap(paths,box):
    result=[]
    for path in paths:
        for a,b in zip(path,path[1:]):
            lo,hi=0.,1.
            for axis in (0,1):
                delta=b[axis]-a[axis]
                if abs(delta)<g.EPS:
                    if not box[axis]<=a[axis]<=box[axis+2]:lo,hi=1.,0.
                else:
                    t1=(box[axis]-a[axis])/delta;t2=(box[axis+2]-a[axis])/delta
                    lo=max(lo,min(t1,t2));hi=min(hi,max(t1,t2))
            if hi<=lo:result.append([a,b]);continue
            d=g.sub(b,a)
            if lo>0:result.append([a,g.add(a,g.mul(d,lo))])
            if hi<1:result.append([g.add(a,g.mul(d,hi)),b])
    return result
