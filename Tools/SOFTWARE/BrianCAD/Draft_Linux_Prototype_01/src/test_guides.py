import unittest
from cad_guides import directions,targets
from curve_trim import crossings

class GuideTests(unittest.TestCase):
    def test_rotated_shared_endpoint(self):
        start=[1,1]
        line=dict(type='line',a=[0,0],b=start)
        guides=directions(start,[line])
        self.assertEqual(len(guides),2)
        hits, projections=targets(start,guides,[2.02,-.01],.1,
                                  [dict(type='line',a=[2,-1],b=[2,1])])
        self.assertTrue(any(abs(p[0]-2)<1e-8 and abs(p[1])<1e-8 for p,_ in hits))
        self.assertEqual(projections[0][1],'perpendicular guide')

    def test_finite_arc_intersection(self):
        arc=dict(type='arc',center=[0,0],radius=1,start=0,sweep=2)
        line=dict(type='line',a=[-2,0],b=[2,0])
        points=[p for _,_,p in crossings(line,arc)]
        self.assertEqual(len(points),1)
        self.assertAlmostEqual(points[0][0],1)
