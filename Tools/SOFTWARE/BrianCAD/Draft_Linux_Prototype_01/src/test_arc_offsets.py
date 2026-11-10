"""Connected arc offsets retain analytic curves, grouping and physical geometry."""
import copy
import math
import unittest
import cad_geometry as g
import cad_groups
from cad_offset import offset,connected_path
from cad_document import Document

try:import shapely
except ImportError:shapely=None

@unittest.skipUnless(shapely,'Optional Shapely is required')
class AnalyticArcOffsetTests(unittest.TestCase):
    def check_joined(self,objects,closed=False):
        points=connected_path(objects)
        self.assertGreater(len(points),2)
        if closed:self.assertLess(g.dist(points[0],points[-1]),1e-9)
        for obj in objects:g.validate_geometry(obj)
    def test_tangent_line_arc_both_sides_with_shuffled_reversed_sources(self):
        source=[dict(type='line',a=[-2,0],b=[0,0]),
                dict(type='arc',center=[0,1],radius=1,start=-math.pi/2,sweep=math.pi/2),
                dict(type='line',a=[1,1],b=[1,3])]
        before=copy.deepcopy(source)
        for chain in (source,[dict(source[2],a=[1,3],b=[1,1]),source[0],source[1]]):
            for ref,radius,y in [([-1,-1],1.25,-.25),([-1,1],.75,.25)]:
                result,approx=offset(chain,.25,ref)
                self.assertFalse(approx);self.assertEqual(len(result),3)
                arc=next(o for o in result if o['type']=='arc')
                self.assertEqual(arc['center'],[0,1]);self.assertAlmostEqual(arc['radius'],radius)
                self.assertAlmostEqual(abs(arc['sweep']),math.pi/2)
                self.assertTrue(any(abs(p[1]-y)<1e-9 for o in result if o['type']=='line' for p in (o['a'],o['b'])))
                self.check_joined(result);self.assertEqual(len({o['group'] for o in result}),1)
        self.assertEqual(source,before)
    def test_adjacent_clockwise_and_counterclockwise_arcs_merge(self):
        for sign in (-1,1):
            arcs=[dict(type='arc',center=[2,3],radius=4,start=sign*(.2+i*.6),sweep=sign*.6) for i in range(4)]
            for delta,radius in [(1,4.3),(-1,3.7)]:
                ref=g.polar([2,3],4+delta,.8*sign)
                result,approx=offset(arcs,.3,ref)
                self.assertFalse(approx);self.assertEqual(len(result),1)
                self.assertEqual(result[0]['type'],'arc');self.assertAlmostEqual(result[0]['radius'],radius)
                self.assertAlmostEqual(abs(result[0]['sweep']),2.4)
    def test_closed_circle_fragments_merge_to_circle(self):
        arcs=[dict(type='arc',center=[0,0],radius=2,start=i*math.pi/2,sweep=math.pi/2) for i in range(4)]
        for ref,radius in [([0,0],1.5),([4,0],2.5)]:
            result,approx=offset([arcs[2],arcs[0],arcs[3],arcs[1]],.5,ref)
            self.assertFalse(approx);self.assertEqual(len(result),1)
            self.assertEqual(result[0]['type'],'circle');self.assertAlmostEqual(result[0]['radius'],radius)
    def test_closed_capsule_and_collapse_keep_safe_fallback(self):
        capsule=[dict(type='line',a=[0,-1],b=[3,-1]),
                 dict(type='arc',center=[3,0],radius=1,start=-math.pi/2,sweep=math.pi),
                 dict(type='line',a=[3,1],b=[0,1]),
                 dict(type='arc',center=[0,0],radius=1,start=math.pi/2,sweep=math.pi)]
        for ref,radius in [([1,0],.8),([1,-2],1.2)]:
            result,approx=offset(capsule,.2,ref)
            self.assertFalse(approx);self.assertEqual(len(result),4)
            self.assertTrue(cad_groups.is_closed(result));self.check_joined(result,True)
            for obj in result:
                if obj['type']=='arc':self.assertAlmostEqual(obj['radius'],radius)
        with self.assertRaises(ValueError):offset(capsule,2,[1,0])
        # A corner is not treated as a tangent joint.
        corners=[dict(type='line',a=[0,0],b=[2,0]),dict(type='line',a=[2,0],b=[2,2])]
        result,approx=offset(corners,.2,[1,1]);self.assertEqual(result[0]['type'],'polygon')
    def test_document_history_layer_pen_native_and_dxf_arcs(self):
        d=Document();source=[dict(type='line',a=[-2,0],b=[0,0]),
                dict(type='arc',center=[0,1],radius=1,start=-math.pi/2,sweep=math.pi/2)]
        d.add(source);d.add_layer('Offsets');d.set_layer('Offsets');d.set_layer_color('#123456')
        before=d.state();n=len(d.history)
        self.assertFalse(d.offset_objects([0,1],.2,[-1,-1]))
        self.assertEqual(len(d.objects),4);self.assertEqual(len(d.history),n+1)
        self.assertTrue(all(o['layer']=='Offsets' and o['color']=='#123456' for o in d.objects[2:]))
        self.assertEqual(d.objects[:2],before['objects'])
        loaded=Document.from_payload(d.payload());self.assertEqual(loaded.objects,d.objects)
        d.undo();self.assertEqual(d.state(),before);d.redo();self.assertEqual(len(d.objects),4)
        try:import ezdxf
        except ImportError:return
        from cad_dxf import build_dxf,snapshot_drawing
        d.selected={2,3};drawing,_=build_dxf(snapshot_drawing(d),True)
        self.assertEqual([e.dxftype() for e in drawing.modelspace()],['LINE','ARC'])

    def test_large_sampled_fallback_is_compact_without_losing_vertices(self):
        from cad_offset import _polylines
        from shapely.geometry import LineString
        points=[g.polar([0,0],3,i*g.TAU/500) for i in range(500)]
        points.append(points[0])
        parts=_polylines(LineString(points),{})
        self.assertEqual(len(parts),3);self.assertTrue(cad_groups.is_closed(parts))
        recovered=[]
        for part in parts:
            path=g.path(part)
            recovered.extend(path if not recovered else path[1:])
        self.assertEqual(recovered,points)
        self.assertTrue(all(len(p.get('points',[]))<=200 for p in parts))
