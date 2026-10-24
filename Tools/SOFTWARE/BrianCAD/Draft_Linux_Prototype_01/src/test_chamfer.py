"""Radius fillets: tangent joins, retained click sides and atomic document edits."""
import math
import unittest
import cad_geometry as g
import cad_selection as s
from cad_chamfer import chamfer, evaluate
from cad_document import Document
from curve_trim import parameter


def line(a,b): return {'type':'line','a':a,'b':b}


class ChamferTests(unittest.TestCase):
    def verify(self,a,b,pa,pb,r):
        left,right,arc=chamfer(a,b,pa,pb,r)
        self.assertAlmostEqual(arc['radius'],r)
        contacts=[g.polar(arc['center'],r,arc['start']+v) for v in (0,arc['sweep'])]
        for pieces,pick in zip((left,right),(pa,pb)):
            self.assertLess(min(g.dist(s.nearest_point(pick,piece),pick) for piece in pieces),1e-6)
        for original,pieces,q in zip((a,b),(left,right),contacts):
            self.assertLess(g.dist(s.nearest_point(q,original),q),1e-6)
            t=parameter(original,q); _,d=evaluate(original,t)
            self.assertAlmostEqual(g.dot(g.unit(d),g.unit(g.sub(q,arc['center']))),0,places=6)
            self.assertLess(min(g.dist(s.nearest_point(q,piece),q) for piece in pieces),1e-6)
        return left,right,arc

    def test_right_angle_and_reversed_line_orientations(self):
        for reverse_a in (False,True):
            for reverse_b in (False,True):
                a=line([0,0],[4,0]); b=line([0,0],[0,4])
                if reverse_a: a['a'],a['b']=a['b'],a['a']
                if reverse_b: b['a'],b['b']=b['b'],b['a']
                aa,bb,arc=self.verify(a,b,[3,0],[0,3],.5)
                self.assertLess(g.dist(arc['center'],[.5,.5]),1e-8)
                self.assertAlmostEqual(abs(arc['sweep']),math.pi/2)
                self.assertTrue(all(p[0]>=.5-1e-8 for p in g.path(aa[0])))
                self.assertTrue(all(p[1]>=.5-1e-8 for p in g.path(bb[0])))

    def test_acute_obtuse_translated_and_opposite_keep_sides(self):
        for angle in (math.pi/3,2*math.pi/3):
            c=[2,-3]; a=line(c,g.add(c,[4,0])); b=line(c,g.add(c,[4*math.cos(angle),4*math.sin(angle)]))
            _,_,arc=self.verify(a,b,g.add(c,[3,0]),g.add(c,[3*math.cos(angle),3*math.sin(angle)]),.3)
            self.assertAlmostEqual(abs(arc['sweep']),math.pi-angle,places=6)
        a=line([-4,0],[4,0]); b=line([0,-4],[0,4])
        for x,y in [(3,3),(-3,3),(3,-3),(-3,-3)]:
            _,_,arc=self.verify(a,b,[x,0],[0,y],.5)
            self.assertLess(g.dist(arc['center'],[math.copysign(.5,x),math.copysign(.5,y)]),1e-8)

    def test_arc_oval_and_spline_segments(self):
        a=line([1,-3],[1,3])
        cases=[({'type':'arc','center':[0,3],'radius':2,'start':math.pi,'sweep':3*math.pi/4},[-.4,3-math.sqrt(4-.16)]),
               ({'type':'ellipse','center':[0,3],'rx':3,'ry':2,'angle':0,'start':math.pi,'sweep':3*math.pi/4},[-.4,3-2*math.sqrt(1-(.4/3)**2)]),
               ({'type':'spline','method':'bezier','closed':False,'points':[[-2,5],[0,-3],[2,5]]},[-.4,1.16])]
        for b,pick in cases:
            with self.subTest(kind=b['type']):
                _,_,arc=self.verify(a,b,[1,-.5],pick,1)
                self.assertLess(g.dist(arc['center'],[0,0]),1e-6)

    def test_two_splines_and_closed_circle_corner(self):
        a={'type':'spline','method':'bezier','closed':False,'points':[[5,-2],[-3,0],[5,2]]}
        b={'type':'spline','method':'bezier','closed':False,'points':[[-2,5],[0,-3],[2,5]]}
        _,_,arc=self.verify(a,b,[1.16,-.4],[-.4,1.16],1)
        self.assertLess(g.dist(arc['center'],[0,0]),1e-6)
        a=line([-3,0],[3,0]); b={'type':'circle','center':[0,0],'radius':2}
        _,pieces,_=self.verify(a,b,[2.5,0],[1,math.sqrt(3)],.3)
        self.assertEqual(pieces[0]['type'],'arc')

    def test_two_curved_segments_and_closed_oval_spline(self):
        a={'type':'arc','center':[3,0],'radius':2,'start':math.pi/2,'sweep':math.pi}
        b={'type':'arc','center':[0,3],'radius':2,'start':math.pi,'sweep':3*math.pi/4}
        _,_,arc=self.verify(a,b,[3-math.sqrt(4-.16),-.4],[-.4,3-math.sqrt(4-.16)],1)
        self.assertLess(g.dist(arc['center'],[0,0]),1e-6)
        a={'type':'ellipse','center':[3,0],'rx':2,'ry':3,'angle':0,'start':math.pi/2,'sweep':math.pi}
        b={'type':'ellipse','center':[0,3],'rx':3,'ry':2,'angle':0,'start':math.pi,'sweep':3*math.pi/4}
        delta=3-2*math.sqrt(1-(.4/3)**2)
        _,_,arc=self.verify(a,b,[delta,-.4],[-.4,delta],1)
        self.assertLess(g.dist(arc['center'],[0,0]),1e-6)
        full={'type':'ellipse','center':[0,0],'rx':3,'ry':2,'angle':.3}
        self.verify(line([-4,0],[4,0]),full,[3.8,0],g.ellipse_point(full,1/6),.3)
        closed={'type':'spline','method':'through','closed':True,'points':[[-2,-2],[2,-2],[2,2],[-2,2]]}
        self.verify(line([-4,0],[4,0]),closed,[3.5,0],g.spline_point(closed,.4),.3)

    def test_invalid_radius_no_fit_and_no_changes(self):
        a=line([0,0],[1,0]); b=line([0,0],[0,1])
        for r in (0,-1,math.nan,math.inf,True,10):
            with self.assertRaises(ValueError): chamfer(a,b,[.8,0],[0,.8],r)
        with self.assertRaises(ValueError): chamfer(a,line([0,2],[1,2]),[.8,0],[.8,2],.2)
        d=Document(); d.add([a,b]); before=d.state(); history=len(d.history)
        with self.assertRaises(ValueError): d.chamfer_objects(0,1,[.8,0],[0,.8],10)
        self.assertEqual(d.state(),before); self.assertEqual(len(d.history),history)
        with self.assertRaises(ValueError): d.chamfer_objects(0,0,[.8,0],[.7,0],.2)
        d.objects[0]['locked']=True
        with self.assertRaises(ValueError): d.chamfer_objects(0,1,[.8,0],[0,.8],.2)

    def test_document_atomic_style_history_roundtrip(self):
        d=Document(); d.add([line([0,0],[4,0]),line([0,0],[0,4]),line([8,8],[9,9])])
        d.objects[0].update(color='#2465d8',pattern='Dashed',weight=.03)
        untouched=d.objects[2]; before=d.state(); history=len(d.history)
        arc=d.chamfer_objects(0,1,[3,0],[0,3],.5)
        self.assertEqual(len(d.history),history+1); self.assertEqual(len(d.objects),4)
        self.assertIs(d.objects[2],untouched); self.assertEqual(d.selected,{3})
        for key in ('layer','color','pattern','weight'): self.assertEqual(arc[key],before['objects'][0][key])
        self.assertEqual(Document.from_payload(d.payload()).state(),d.state())
        after=d.state(); d.undo(); self.assertEqual(d.state(),before)
        d.redo(); self.assertEqual(d.state(),after)


if __name__=='__main__': unittest.main()
