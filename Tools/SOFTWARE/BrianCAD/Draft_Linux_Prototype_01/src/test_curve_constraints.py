"""True curve tangents/normals, finite arc quadrants and line endpoint snaps."""
import math
import unittest
import cad_geometry as g
import cad_selection as s
from test_grid import editor, Value
from snap_tracking import SnapHistory


class CurveConstraintTests(unittest.TestCase):
    def assertPoint(self,a,b): self.assertLess(g.dist(a,b),1e-7)

    def test_rotated_oval_tangents(self):
        o={'type':'ellipse','center':[2,-3],'rx':3,'ry':1,'angle':.6}
        start=[8,4]; points=s.constraint_points(start,o,'tangent')
        self.assertEqual(len(points),2)
        for p in points:
            x,y=g.sub(p,o['center']); ca,sa=math.cos(.6),math.sin(.6)
            u,v=ca*x+sa*y,-sa*x+ca*y
            self.assertAlmostEqual((u/3)**2+v*v,1)
            normal=[ca*u/9-sa*v,sa*u/9+ca*v]
            self.assertAlmostEqual(g.dot(g.unit(g.sub(start,p)),g.unit(normal)),0)
        self.assertEqual(s.constraint_points(o['center'],o,'tangent'),[])

    def test_oval_perpendicular_multiple_contacts_and_circle_limit(self):
        o={'type':'ellipse','center':[0,0],'rx':3,'ry':1,'angle':0}
        points=s.constraint_points([0,0],o,'perpendicular')
        self.assertEqual(len(points),4)
        for target in [[3,0],[-3,0],[0,1],[0,-1]]:
            self.assertTrue(any(g.dist(q,target)<1e-7 for q in points))
        start=[4,2]; points=s.constraint_points(start,o,'perpendicular')
        self.assertGreaterEqual(len(points),2)
        for q in points:
            normal=[q[0]/9,q[1]]
            self.assertAlmostEqual(g.cross(g.unit(g.sub(start,q)),g.unit(normal)),0,places=6)
        o.update(rx=1,ry=1)
        self.assertEqual(s.constraint_points([0,0],o,'perpendicular'),[])

    def test_spline_tangent_and_perpendicular_known_contacts(self):
        o={'type':'spline','method':'bezier','closed':False,'points':[[0,0],[1,2],[2,0]]}
        tangents=s.constraint_points([3,1],o,'tangent')
        self.assertTrue(any(g.dist(q,[1,1])<1e-7 for q in tangents))
        normals=s.constraint_points([1,3],o,'perpendicular')
        self.assertTrue(any(g.dist(q,[1,1])<1e-7 for q in normals))
        for q in tangents:
            t=q[0]/2; derivative=[2,4-8*t]
            self.assertAlmostEqual(g.cross(g.unit(g.sub([3,1],q)),g.unit(derivative)),0,places=6)
        # Through-point and closed interpolating splines use their true cubic spans.
        for closed in (False,True):
            o.update(method='through',closed=closed,points=[[0,0],[1,2],[2,0]])
            normals=s.constraint_points([1,4],o,'perpendicular')
            self.assertTrue(any(g.dist(q,[1,2])<1e-7 for q in normals))

    def test_rotated_oval_normal_and_high_degree_spline_contacts(self):
        o={'type':'ellipse','center':[2,-3],'rx':3,'ry':1,'angle':.8}
        theta=.7; ca,sa=math.cos(.8),math.sin(.8)
        q=g.add(o['center'],[ca*3*math.cos(theta)-sa*math.sin(theta),
                             sa*3*math.cos(theta)+ca*math.sin(theta)])
        normal=[ca*math.cos(theta)/3-sa*math.sin(theta),sa*math.cos(theta)/3+ca*math.sin(theta)]
        start=g.add(q,g.mul(normal,4))
        points=s.constraint_points(start,o,'perpendicular')
        self.assertTrue(any(g.dist(p,q)<1e-7 for p in points))
        for n in (6,32):
            span=[[i/(n-1)*4,math.sin(i/(n-1)*4)] for i in range(n)]
            o={'type':'spline','method':'bezier','closed':False,'points':span}
            t=.37; q=s._bezier_point(span,t)
            derivative=s._bezier_point([g.mul(g.sub(b,a),n-1) for a,b in zip(span,span[1:])],t)
            for mode,direction in [('tangent',derivative),('perpendicular',g.normal(derivative))]:
                start=g.add(q,g.mul(direction,2))
                points=s.constraint_points(start,o,mode)
                self.assertTrue(any(g.dist(p,q)<1e-6 for p in points),(n,mode,points))

    def test_trimmed_circle_retains_quadrant_targets(self):
        from cad_trim import trim
        circle={'type':'circle','center':[0,0],'radius':1}
        arc=trim(circle,[{'type':'line','a':[0,-2],'b':[0,2]}],[1,0])[0]
        quadrants=[p for p,label in g.anchors(arc) if label=='quadrant']
        self.assertEqual(len(quadrants),3)
        self.assertTrue(any(g.dist(p,[-1,0])<1e-9 for p in quadrants))
        self.assertFalse(any(g.dist(p,[1,0])<1e-9 for p in quadrants))

    def test_line_circle_arc_perpendicular_and_finite_limits(self):
        line={'type':'line','a':[0,0],'b':[2,0]}
        self.assertEqual(s.constraint_points([1,3],line,'perpendicular'),[[1,0]])
        self.assertEqual(s.constraint_points([3,3],line,'perpendicular'),[])
        circle={'type':'circle','center':[0,0],'radius':1}
        points=s.constraint_points([2,0],circle,'perpendicular')
        for target in [[1,0],[-1,0]]: self.assertTrue(any(g.dist(q,target)<1e-7 for q in points))
        arc=dict(circle,type='arc',start=-math.pi/4,sweep=math.pi/2)
        self.assertEqual(len(s.constraint_points([2,0],arc,'perpendicular')),1)
        self.assertEqual(s.constraint_points([0,0],circle,'perpendicular'),[])

    def test_arc_quadrants_on_actual_clockwise_and_wrapped_sweeps(self):
        for start,sweep,expected in [(math.radians(350),math.radians(110),[0,1]),
                                     (math.radians(10),math.radians(-110),[0,3])]:
            o={'type':'arc','center':[2,3],'radius':2,'start':start,'sweep':sweep}
            points=[q for q,label in g.anchors(o) if label=='quadrant']
            self.assertEqual(len(points),2)
            for i in expected:
                self.assertTrue(any(g.dist(q,g.polar([2,3],2,i*math.pi/2))<1e-8 for q in points))

    def test_generator_labels_edited_start_toggles_visibility_and_cache(self):
        a=editor(); a.tool=Value('Two points'); a.points=[[1,3]]; a.start=[1,3]
        a.params={'x':Value('1'),'y':Value('3')}; a.snap_history=SnapHistory()
        a.doc.add([{'type':'line','a':[0,0],'b':[4,0]}])
        q,label=a.snap_point([1.02,.03]); self.assertPoint(q,[1,0]); self.assertEqual(label,'perpendicular')
        cache=len(a._constraint_cache); a.snap_point([1.01,.02]); self.assertEqual(len(a._constraint_cache),cache)
        a.params['x'].set('3'); q,label=a.snap_point([3.02,.03]); self.assertPoint(q,[3,0])
        self.assertEqual(label,'perpendicular')
        self.assertNotEqual(a.snap_point([3.02,.03],exclude={0})[1],'perpendicular')
        a.doc.layers[-1]['visible']=False
        self.assertNotEqual(a.snap_point([3.02,.03])[1],'perpendicular')
        a.doc.layers[-1]['visible']=True; a.snap.set(False)
        self.assertNotEqual(a.snap_point([3.02,.03])[1],'perpendicular')


if __name__=='__main__': unittest.main()
