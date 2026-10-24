"""Independent guide intersections with grid, finite geometry and other guides."""
import math
import unittest
import cad_geometry as g
from cad_selection import axis_intersections
from snap_tracking import SnapHistory
from test_grid import editor


class AlignmentCrossingsTests(unittest.TestCase):
    def test_independent_guide_grid_and_mutual_crossings(self):
        h=SnapHistory(); h.remember([2.13,8],'endpoint')
        self.assertEqual(h.crossings([2.15,3.02],100,step=.25),
                         [([2.13,3.0],'align x / grid intersection')])
        h.clear(); h.remember([8,3.13],'endpoint')
        self.assertEqual(h.crossings([2.02,3.15],100,step=.25),
                         [([2.,3.13],'align y / grid intersection')])
        h.remember([2.13,8],'endpoint')
        self.assertIn(([2.13,3.13],'align x + align y'),h.crossings([2.15,3.15],100))
        self.assertEqual(h.crossings([2.3,3.3],100,step=.25),[])

    def test_generator_object_grid_toggles_visibility_exclusions_and_memory(self):
        a=editor(); a.snap_history=SnapHistory(); a.snap_history.remember([2.13,8],'endpoint')
        a.doc.add([{'type':'line','a':[1,2],'b':[5,6]}])
        before=list(a.snap_history.points)
        point,label=a.snap_point([2.15,3.14])
        self.assertEqual(label,'align x / object intersection')
        self.assertAlmostEqual(g.dist(point,[2.13,3.13]),0)
        a.snap_history.remember(point,label); self.assertEqual(a.snap_history.points,before)
        self.assertNotIn('object intersection',a.snap_point([2.15,3.14],exclude={0})[1])
        a.doc.layers[-1]['visible']=False
        self.assertNotIn('object intersection',a.snap_point([2.15,3.14])[1])
        a.grid_snap.set(False)
        self.assertEqual(a.snap_point([2.15,3.14]),([2.13,3.14],'align x'))
        a.snap.set(False); self.assertEqual(a.snap_point([2.15,3.14]),([2.15,3.14],''))

    def test_circle_arc_tangent_and_finite_line_contacts(self):
        circle={'type':'circle','center':[0,0],'radius':1}
        self.assertEqual(axis_intersections(circle,0,1),[[1,0]])
        self.assertEqual(axis_intersections(circle,0,1.1),[])
        arc=dict(circle,type='arc',start=math.pi,sweep=-math.pi)
        pts=axis_intersections(arc,0,.5)
        self.assertEqual(len(pts),1); self.assertAlmostEqual(pts[0][1],math.sqrt(3)/2)
        self.assertEqual(axis_intersections({'type':'line','a':[0,0],'b':[1,1]},0,2),[])
        # Collinear guide/edge does not invent a finite crossing.
        self.assertEqual(axis_intersections({'type':'line','a':[1,0],'b':[1,2]},0,1),[])

    def test_rotated_ellipse_and_polygon(self):
        o={'type':'ellipse','center':[2,-1],'rx':3,'ry':1,'angle':.6}
        pts=axis_intersections(o,0,2.2); self.assertEqual(len(pts),2)
        for p in pts:
            x,y=g.sub(p,o['center']); a=o['angle']
            u=x*math.cos(a)+y*math.sin(a); v=-x*math.sin(a)+y*math.cos(a)
            self.assertAlmostEqual((u/3)**2+v*v,1)
            self.assertEqual(p[0],2.2)
        box={'type':'polygon','points':[[-1,-1],[1,-1],[1,1],[-1,1]]}
        self.assertEqual(sorted(axis_intersections(box,0,0)),[[0,-1],[0,1]])

    def test_spline_interior_and_tangent_roots(self):
        o={'type':'spline','method':'bezier','closed':False,'points':[[0,0],[1,2],[2,0]]}
        for axis,value,expected in [(0,1,[1,1]),(1,1,[1,1])]:
            pts=axis_intersections(o,axis,value)
            self.assertEqual(len(pts),1); self.assertLess(g.dist(pts[0],expected),1e-8)
        o={'type':'spline','method':'through','closed':False,'points':[[0,0],[1,2],[2,0]]}
        pts=axis_intersections(o,0,1)
        self.assertEqual(len(pts),1); self.assertLess(g.dist(pts[0],[1,2]),1e-8)


if __name__=='__main__': unittest.main()
