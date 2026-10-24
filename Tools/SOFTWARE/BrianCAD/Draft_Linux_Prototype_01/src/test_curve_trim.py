"""Oval/spline trim contacts, exact fragments, persistence and downstream geometry."""
import math
import unittest
import cad_geometry as g
import cad_selection as s
from cad_trim import trim, intersections
from curve_trim import crossings
from cad_document import Document


def oval(): return {'type':'ellipse','center':[0,0],'rx':2,'ry':1,'angle':0}
def line(a,b): return {'type':'line','a':a,'b':b}
def spline(points,method='bezier',closed=False): return {'type':'spline','points':points,'method':method,'closed':closed}


class CurveTrimTests(unittest.TestCase):
    def test_oval_retains_exact_arc_and_retrim(self):
        o=trim(oval(),[line([0,-3],[0,3])],[2,0])[0]
        self.assertEqual(o['type'],'ellipse'); self.assertAlmostEqual(o['sweep'],math.pi)
        self.assertLess(g.dist(g.ellipse_point(o,.5),[-2,0]),1e-9)
        self.assertGreater(g.dist(s.nearest_point([2,0],o),[2,0]),1)
        self.assertAlmostEqual(s.bounds(o)[2],0)
        kept=trim(o,[line([-3,0],[3,0])],[-1,.8])[0]
        self.assertAlmostEqual(abs(kept['sweep']),math.pi/2)
        self.assertTrue(all(p[1]<=1e-9 for p in g.path(kept)))
        self.assertEqual(s.axis_intersections(kept,1,.5),[])

    def test_oval_boundary_line_and_tangent_contacts(self):
        pieces=trim(line([-3,0],[3,0]),[oval()],[0,0])
        self.assertEqual(len(pieces),2)
        self.assertAlmostEqual(pieces[0]['b'][0],-2); self.assertAlmostEqual(pieces[1]['a'][0],2)
        points=intersections(oval(),line([-3,1],[3,1]))
        self.assertEqual(len(points),1); self.assertLess(g.dist(points[0],[0,1]),1e-7)
        self.assertEqual(trim(oval(),[line([-3,1],[3,1])],[2,0]),[])

    def test_conic_conic_rotated_and_finite_oval_arc(self):
        a=oval(); b=dict(oval(),center=[1,0],angle=.4)
        points=intersections(a,b); self.assertGreaterEqual(len(points),2)
        for p in points:
            for obj in (a,b):
                x,y=g.sub(p,obj['center']); ca,sa=math.cos(obj['angle']),math.sin(obj['angle'])
                self.assertAlmostEqual(((ca*x+sa*y)/obj['rx'])**2+((-sa*x+ca*y)/obj['ry'])**2,1,places=6)
        a.update(start=math.pi,sweep=math.pi)
        self.assertEqual(intersections(a,line([-3,.5],[3,.5])),[])
        self.assertEqual(len(intersections(a,line([-3,-.5],[3,-.5]))),2)
        self.assertEqual(intersections(oval(),oval()),[])

    def test_bezier_trim_has_exact_subdivision_and_retained_style(self):
        source=spline([[0,0],[1,2],[2,0]]); source.update(color='#2465d8',pattern='Dashed')
        pieces=trim(source,[line([.5,-2],[.5,3]),line([1.5,-2],[1.5,3])],[1,1])
        self.assertEqual(len(pieces),2)
        for piece,lo,hi in [(pieces[0],0,.25),(pieces[1],.75,1)]:
            self.assertEqual(piece['method'],'bezier'); self.assertFalse(piece['closed'])
            self.assertEqual(piece['color'],source['color'])
            for t in (0,.2,.5,.8,1):
                self.assertLess(g.dist(g.spline_point(piece,t),g.spline_point(source,lo+(hi-lo)*t)),1e-8)
        self.assertAlmostEqual(pieces[0]['points'][-1][0],.5)
        # A retained piece remains a valid target and boundary for later operations.
        again=trim(pieces[0],[line([.25,-2],[.25,3])],[.1,.19])
        self.assertEqual(len(again),1); self.assertAlmostEqual(again[0]['points'][0][0],.25)

    def test_through_and_closed_spline_fragments_keep_curve(self):
        source=spline([[0,0],[1,2],[2,0]],'through')
        pieces=trim(source,[line([1,-2],[1,3])],[.2,.5])
        self.assertEqual(len(pieces),1)
        for t in (0,.25,.5,.75,1):
            self.assertLess(g.dist(g.spline_point(pieces[0],t),g.spline_point(source,.5+.5*t)),1e-8)
        closed=spline([[-1,-1],[1,-1],[1,1],[-1,1]],'through',True)
        pieces=trim(closed,[line([0,-3],[0,3])],[1,0])
        self.assertGreaterEqual(len(pieces),2)
        self.assertTrue(all(p[0]<=1e-7 for piece in pieces for p in g.path(piece)))
        self.assertTrue(all(piece['method']=='bezier' and not piece['closed'] for piece in pieces))

    def test_spline_as_boundary_and_spline_pair_tangent(self):
        boundary=spline([[0,0],[1,2],[2,0]])
        pieces=trim(line([-.5,.5],[2.5,.5]),[boundary],[1,.5])
        self.assertEqual(len(pieces),2)
        self.assertAlmostEqual(pieces[0]['b'][0],1-math.sqrt(.5),places=6)
        a=spline([[0,0],[1,2],[2,0]])
        b=spline([[0,1],[2,1]])
        result=crossings(a,b)
        self.assertEqual(len(result),1)
        self.assertLess(g.dist(result[0][2],[1,1]),1e-6)
        self.assertEqual(crossings(a,a),[])
        curved=crossings(a,spline([[0,1.5],[1,.5],[2,1.5]]))
        self.assertEqual(len(curved),1)
        self.assertLess(g.dist(curved[0][2],[1,1]),1e-6)
        # Two proper spline/spline crossings.
        result=crossings(a,spline([[0,.5],[2,.5]]))
        self.assertEqual(len(result),2)
        curved=crossings(a,spline([[0,.5],[1,.7],[2,.5]]))
        self.assertEqual(len(curved),2)
        self.assertAlmostEqual(min(p[0] for _,_,p in curved),1/3,places=6)

    def test_oval_arc_transforms_controls_and_document_roundtrip(self):
        d=Document(); d.add([oval(),line([0,-3],[0,3])]); d.selected={1}
        before=d.state(); history=len(d.history)
        d.trim_object(0,{1},[2,0]); self.assertEqual(len(d.history),history+1)
        self.assertEqual(d.selected,{1}); arc=d.objects[0]
        self.assertEqual(Document.from_payload(d.payload()).state(),d.state())
        mirrored=g.transform(arc,'Mirror',angle=30)
        for t in (0,.25,.5,.75,1):
            p=g.ellipse_point(arc,t)
            expected=g.transform(line(p,g.add(p,[1,0])),'Mirror',angle=30)['a']
            self.assertLess(g.dist(g.ellipse_point(mirrored,t),expected),1e-8)
        self.assertEqual(set(dict(s.controls(arc))),{'center','start','end'})
        adjusted=s.move_controls(arc,{'end'},-.2,.1); g.validate_geometry(adjusted)
        d.undo(); self.assertEqual(d.state(),before); d.redo(); self.assertIn('sweep',d.objects[0])

    def test_spline_fragment_save_reopen_and_retrim_boundary(self):
        d=Document(); d.add([spline([[0,0],[1,2],[2,0]]),line([1,-2],[1,3])])
        d.selected={1}; d.trim_object(0,{1},[.2,.36])
        self.assertEqual(Document.from_payload(d.payload()).state(),d.state())
        a=spline([[0,0],[0,0],[1,1],[1,1]])
        b=spline([[1,1],[1,1],[2,0],[2,0]])
        contacts=crossings(a,b)
        self.assertTrue(any(g.dist(p,[1,1])<1e-8 for _,_,p in contacts))
        o=trim(oval(),[line([0,-3],[0,3])],[2,0])[0]
        for mode in ('tangent','perpendicular'):
            self.assertTrue(all(g.ellipse_contains(o,p) for p in s.constraint_points([3,2],o,mode)))

    def test_no_contact_is_atomic_and_polygon_boundary_works(self):
        d=Document(); d.add([oval(),line([5,-2],[5,2])]); before=d.state(); n=len(d.history)
        with self.assertRaises(ValueError): d.trim_object(0,{1},[2,0])
        self.assertEqual(d.state(),before); self.assertEqual(len(d.history),n)
        source=spline([[-3,0],[3,0]])
        box={'type':'polygon','points':[[-1,-1],[1,-1],[1,1],[-1,1]]}
        result=trim(source,[box],[0,0]); self.assertEqual(len(result),2)
        self.assertAlmostEqual(result[0]['points'][-1][0],-1)
        self.assertAlmostEqual(result[1]['points'][0][0],1)


if __name__=='__main__': unittest.main()
