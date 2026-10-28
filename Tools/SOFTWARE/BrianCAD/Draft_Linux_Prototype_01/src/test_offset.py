"""Offset side, distances, chain topology, primitive exactness and atomic history."""
import copy
import math
import unittest
from unittest.mock import patch
try:import shapely
except ImportError:shapely=None
import cad_geometry as g
from cad_offset import offset,sample,connected_path,require_shapely,TOLERANCE
from cad_document import Document

class OffsetTests(unittest.TestCase):
    def test_exact_line_both_sides_and_styles(self):
        o=dict(type='line',a=[0,0],b=[3,4],layer='Layer1',color='#123456',weight=.02)
        before=copy.deepcopy(o)
        for ref,sign in [([-4,3],1),([4,-3],-1)]:
            result,approx=offset([o],.5,ref);self.assertFalse(approx);n=result[0]
            self.assertEqual(n['color'],o['color']);self.assertEqual(n['weight'],.02)
            self.assertLess(g.dist(n['a'],[-.4*sign,.3*sign]),1e-12)
            self.assertAlmostEqual(g.dist(n['a'],n['b']),5)
        self.assertEqual(o,before)
    def test_circles_and_signed_wrapped_arcs_stay_exact(self):
        for kind in ('circle','arc'):
            o=dict(type=kind,center=[2,3],radius=2)
            if kind=='arc':o.update(start=5.9,sweep=-2.)
            for ref,radius in [([2,3],1.5),([6,3],2.5)]:
                if kind=='arc':ref=g.polar(o['center'],3 if radius>2 else 1,5.2)
                result,approx=offset([o],.5,ref);self.assertFalse(approx)
                self.assertEqual(result[0]['type'],kind);self.assertEqual(result[0]['radius'],radius)
                if kind=='arc':self.assertEqual(result[0]['sweep'],-2.)
        with self.assertRaises(ValueError):offset([dict(type='circle',center=[0,0],radius=1)],2,[0,0])
    def test_invalid_inputs_and_dependency_message(self):
        o=dict(type='line',a=[0,0],b=[2,0])
        for distance in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):offset([o],distance,[0,1])
        with self.assertRaises(ValueError):offset([o],1,[1,0])
        with patch.dict('sys.modules',{'shapely':None}):
            with self.assertRaisesRegex(ValueError,'requirements-offset.txt'):require_shapely()
            self.assertEqual(offset([o],1,[0,1])[0][0]['a'],[0,1])
    def test_bezier_closed_flag_does_not_move_a_rendered_endpoint(self):
        # BrianCAD Béziers render their control endpoints even with the closed flag.
        o=dict(type='spline',method='bezier',points=[[0,0],[1,2],[3,0]],closed=True)
        points=sample(o);self.assertEqual(points[0],[0,0]);self.assertLess(g.dist(points[-1],[3,0]),1e-10)
    def test_document_atomic_undo_redo_and_source_style(self):
        d=Document();d.add([dict(type='circle',center=[0,0],radius=1,color='#123456',weight=.03)])
        before=d.state();history=len(d.history)
        with self.assertRaises(ValueError):d.offset_objects([0],2,[0,0])
        self.assertEqual(d.state(),before);self.assertEqual(len(d.history),history)
        self.assertFalse(d.offset_objects([0],.2,[2,0]));self.assertEqual(len(d.history),history+1)
        self.assertEqual(d.objects[1]['color'],'#123456');self.assertEqual(d.selected,{1})
        d.undo();self.assertEqual(d.state(),before);d.redo();self.assertEqual(len(d.objects),2)

@unittest.skipUnless(shapely,'Optional Shapely is required')
class GeneralOffsetTests(unittest.TestCase):
    def test_polygon_inward_outward_and_collapse(self):
        o=dict(type='polygon',points=[[0,0],[4,0],[4,4],[0,4]],closed=True)
        from shapely.geometry import Polygon
        for ref,area in [([2,2],4),([6,2],36)]:
            result,approx=offset([o],1,ref);self.assertFalse(approx)
            self.assertTrue(result[0]['closed']);self.assertAlmostEqual(Polygon(result[0]['points']).area,area)
        with self.assertRaises(ValueError):offset([o],3,[2,2])
    def test_shuffled_reversed_open_and_closed_line_chains(self):
        chain=[dict(type='line',a=[2,2],b=[2,0]),dict(type='line',a=[0,0],b=[2,0])]
        path=connected_path(chain);self.assertEqual(len(path),3)
        result,approx=offset(chain,.5,[1,.5]);self.assertFalse(approx)
        self.assertEqual(len(result),1)
        pts=result[0]['points'];self.assertTrue(any(g.dist(p,[1.5,.5])<1e-10 for p in pts))
        chain += [dict(type='line',a=[0,2],b=[2,2]),dict(type='line',a=[0,0],b=[0,2])]
        result,approx=offset(chain,.25,[1,1]);self.assertTrue(result[0]['closed'])
    def test_disconnected_branched_and_self_crossing_rejected(self):
        line=lambda a,b:dict(type='line',a=a,b=b)
        for source in [[line([0,0],[1,0]),line([3,0],[4,0])],
                       [line([0,0],[1,0]),line([1,0],[2,0]),line([1,0],[1,1])],
                       [dict(type='polygon',points=[[0,0],[2,2],[0,2],[2,0]],closed=True)]]:
            with self.assertRaises(ValueError):offset(source,.1,[3,3])
    def test_oval_and_spline_offset_distance(self):
        from shapely.geometry import LineString,Point
        for o in [dict(type='ellipse',center=[0,0],rx=3,ry=2,angle=.3),
                  dict(type='spline',method='bezier',points=[[0,0],[1,2],[3,2],[4,0]],closed=False),
                  dict(type='spline',method='through',points=[[0,0],[2,2],[4,0]],closed=False),
                  dict(type='ellipse',center=[0,0],rx=3,ry=2,angle=0,start=0,sweep=2.)]:
            result,approx=offset([o],.2,[10,10]);self.assertTrue(approx)
            source=LineString(sample(o));self.assertGreater(len(result),0)
            for obj in result:
                for p in g.path(obj)[::max(1,len(g.path(obj))//10)]:
                    # Mitre vertices can exceed the normal distance by a small amount.
                    self.assertAlmostEqual(source.distance(Point(p)),.2,delta=.001)
    def test_closed_spline_and_split_inward_boundary(self):
        spline=dict(type='spline',method='through',points=[[0,0],[3,0],[3,3],[0,3]],closed=True)
        result,approx=offset([spline],.1,[1,1]);self.assertTrue(approx);self.assertTrue(result)
        # A narrow neck disappears on an inward offset, leaving two closed loops.
        polygon=dict(type='polygon',closed=True,points=[[0,0],[2,0],[2,.9],[4,.9],[4,0],[6,0],
                    [6,2],[4,2],[4,1.1],[2,1.1],[2,2],[0,2]])
        result,approx=offset([polygon],.2,[1,1]);self.assertEqual(len(result),2)
        self.assertTrue(all(o.get('closed') for o in result))
    def test_connected_line_arc(self):
        source=[dict(type='line',a=[-2,0],b=[0,0]),dict(type='arc',center=[0,1],radius=1,start=-math.pi/2,sweep=math.pi/2)]
        result,approx=offset(source,.1,[-1,-1]);self.assertTrue(approx);self.assertTrue(result)
        # Every result is valid and can be saved/reopened as editable geometry.
        d=Document();d.add(result);self.assertEqual(Document.from_payload(d.payload()).objects,d.objects)
