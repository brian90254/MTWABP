"""Analytic tangent contacts and line endpoint snap integration."""
import math
import unittest
import cad_geometry as g
from test_grid import editor, Value


class TangentTests(unittest.TestCase):
    def test_contacts_are_on_circle_and_perpendicular(self):
        for c,r,start in [([0,0],1,[2,0]),([4,-3],2,[-3,4]),
                          ([0,0],1,[1.000001,0]),([0,0],1,[1e8,2])]:
            obj={'type':'circle','center':c,'radius':r}
            points=g.tangent_points(start,obj)
            self.assertEqual(len(points),2)
            for q in points:
                self.assertAlmostEqual(g.dist(c,q),r)
                # Normalize to check angle independently of distance to the start.
                self.assertAlmostEqual(g.dot(g.unit(g.sub(q,c)),g.unit(g.sub(start,q))),0)

    def test_no_nonzero_tangent_inside_or_on_circle(self):
        o={'type':'circle','center':[0,0],'radius':1}
        for start in [[0,0],[.9,0],[1,0]]: self.assertEqual(g.tangent_points(start,o),[])
        self.assertEqual(g.tangent_points([2,0],{'type':'line'}),[])

    def test_arc_sweep_clockwise_and_wraparound(self):
        for start,sweep,sign in [(0,math.pi/2,1),(0,-math.pi/2,-1),
                                 (math.radians(350),math.pi/2,1),
                                 (math.radians(10),-math.pi/2,-1)]:
            o={'type':'arc','center':[0,0],'radius':1,'start':start,'sweep':sweep}
            points=g.tangent_points([2,0],o)
            self.assertEqual(len(points),1)
            self.assertAlmostEqual(points[0][0],.5)
            self.assertAlmostEqual(points[0][1],sign*math.sqrt(3)/2)
        o.update(start=math.pi*.8,sweep=.2)
        self.assertEqual(g.tangent_points([2,0],o),[])

    def setup_line(self,method='Two points'):
        a=editor(); a.tool=Value(method); a.points=[[2,0]]; a.start=[2,0]
        a.params={'x':Value('2'),'y':Value('0')}
        a.doc.add([{'type':'circle','center':[0,0],'radius':1}])
        return a

    def test_snap_priority_tolerance_toggles_and_visibility(self):
        a=self.setup_line(); q=[.5,math.sqrt(3)/2]
        for method in ['Two points','Connected points']:
            a.tool.set(method)
            p,label=a.snap_point([q[0]+.02,q[1]-.01])
            self.assertEqual(label,'tangent'); self.assertAlmostEqual(g.dist(p,q),0)
        self.assertNotEqual(a.snap_point([q[0]+.2,q[1]])[1],'tangent')
        a.snap.set(False); self.assertNotEqual(a.snap_point(q)[1],'tangent')
        a.snap.set(True); a.doc.layers[-1]['visible']=False
        self.assertNotEqual(a.snap_point(q)[1],'tangent')
        a.doc.layers[-1]['visible']=True
        self.assertNotEqual(a.snap_point(q,exclude={0})[1],'tangent')
        a.tool.set('Offset from line'); self.assertNotEqual(a.snap_point(q)[1],'tangent')
        a.tool.set('Two points'); a.points=[]
        self.assertNotEqual(a.snap_point(q)[1],'tangent')

    def test_edited_start_fields_are_used(self):
        a=self.setup_line(); a.params['x'].set('-2')
        q=[-.5,math.sqrt(3)/2]
        self.assertEqual(a.snap_point(q)[1],'tangent')
        self.assertNotEqual(a.snap_point([.5,q[1]])[1],'tangent')
        a.params['x'].set('invalid')
        self.assertNotEqual(a.snap_point(q)[1],'tangent')


if __name__=='__main__': unittest.main()
