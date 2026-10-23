"""Selection geometry and document regressions, independent of a display."""
import copy
import json
import math
import unittest
import cad_geometry as g
import cad_selection as s
from cad_document import Document


class ControlTests(unittest.TestCase):
    def point(self,a,b):
        for x,y in zip(a,b): self.assertAlmostEqual(x,y,places=8)

    def test_circle_handle_is_not_four_independent_radius_points(self):
        circle={'type':'circle','center':[0,0],'radius':1}
        self.assertEqual(set(dict(s.controls(circle))),{'center','radius'})
        self.assertEqual(len([a for a,label in g.anchors(circle) if label=='quadrant']),4)
        n=s.move_controls(circle,{'radius'},0,1)
        self.point(dict(s.controls(n))['radius'],[1,1]); self.point(n['center'],[0,0])
        self.assertAlmostEqual(n['radius'],math.sqrt(2))
        n=s.move_controls(circle,{'center'},3,4)
        self.point(n['center'],[3,4]); self.assertEqual(n['radius'],1)

    def test_line_single_endpoint_and_both(self):
        o={'type':'line','a':[0,0],'b':[2,0]}
        n=s.move_controls(o,{'a'},0,1)
        self.assertEqual(n['a'],[0,1]); self.assertEqual(n['b'],[2,0])
        n=s.move_controls(o,{'a','b'},3,4)
        self.assertEqual(n['a'],[3,4]); self.assertEqual(n['b'],[5,4])
        with self.assertRaises(ValueError): s.move_controls(o,{'a'},2,0)
        self.assertEqual(o['a'],[0,0])

    def test_arc_rim_controls_retain_the_unmoved_points(self):
        o=g.arc_three([1,0],[.8,.6],[-1,0])
        old=dict(s.controls(o)); n=s.move_controls(o,{'start'},.25,.5); new=dict(s.controls(n))
        self.point(new['start'],g.add(old['start'],[.25,.5]))
        self.point(new['through'],old['through']); self.point(new['end'],old['end'])
        n=s.move_controls(o,{'through'},0,.2); new=dict(s.controls(n))
        self.point(new['through'],g.add(old['through'],[0,.2]))
        self.point(new['start'],old['start']); self.point(new['end'],old['end'])

    def test_ellipse_preserves_perpendicular_axes(self):
        o=g.ellipse_axes([0,0],[2,0],[0,1])
        n=s.move_controls(o,{'axis_y'},.7,1)
        self.assertEqual(n['rx'],2); self.assertEqual(n['ry'],2)
        self.point(dict(s.controls(n))['axis_y'],[0,2])
        n=s.move_controls(o,{'axis_x'},0,1)
        self.point(dict(s.controls(n))['axis_x'],[2,1])
        self.point(n['center'],[0,0])

    def test_vertices_and_spline_controls(self):
        for o in [g.rectangle([0,0],[2,1]),{'type':'spline','points':[[0,0],[1,2],[3,0]],'method':'bezier','closed':False}]:
            n=s.move_controls(o,{'p1'},1,1)
            self.assertEqual(n['points'][1],g.add(o['points'][1],[1,1]))
            self.assertEqual(n['points'][0],o['points'][0])

    def test_handle_angle_and_arc_controls_survive_transforms_and_files(self):
        circle=s.move_controls({'type':'circle','center':[0,0],'radius':1},{'radius'},0,1)
        rotated=g.transform(circle,'Rotate',angle=90)
        self.point(dict(s.controls(rotated))['radius'],[-1,1])
        mirrored=g.transform(circle,'Mirror',angle=0)
        self.point(dict(s.controls(mirrored))['radius'],[1,-1])
        d=Document(); d.add([circle,g.arc_three([1,0],[.8,.6],[-1,0])])
        loaded=Document.from_payload(json.loads(json.dumps(d.payload())))
        self.assertEqual(loaded.objects,d.objects)


class BoundsAndProjectionTests(unittest.TestCase):
    def test_exact_circle_and_rotated_ellipse_bounds(self):
        circle={'type':'circle','center':[2,3],'radius':1}
        self.assertEqual(s.bounds(circle),[1,2,3,4])
        e={'type':'ellipse','center':[0,0],'rx':2,'ry':1,'angle':math.pi/4}
        b=s.bounds(e); extent=math.sqrt(2.5)
        for actual,expected in zip(b,[-extent,-extent,extent,extent]): self.assertAlmostEqual(actual,expected)
        self.assertTrue(s.wholly_inside(e,[-extent,-extent,extent,extent]))
        self.assertFalse(s.wholly_inside(e,[-extent,-extent,extent-1e-5,extent]))

    def test_arc_extrema_between_sample_points(self):
        o=g.arc_center([0,0],g.polar([0,0],2,.1),g.polar([0,0],2,2.8))
        self.assertAlmostEqual(s.bounds(o)[3],2)
        self.assertFalse(s.wholly_inside(o,[-3,-3,3,2-1e-6]))
        o=g.arc_center([0,0],g.polar([0,0],2,3),g.polar([0,0],2,.1),True)
        self.assertAlmostEqual(s.bounds(o)[3],2)

    def test_bezier_bounds_follow_curve_not_control_hull(self):
        o={'type':'spline','points':[[0,0],[1,2],[2,0]],'method':'bezier','closed':False}
        self.assertEqual(s.bounds(o),[0,0,2,1])
        self.assertTrue(s.wholly_inside(o,[0,0,2,1]))
        self.assertFalse(s.wholly_inside(o,[0,0,2,.999999]))
        o={'type':'spline','points':[[0,0],[0,3],[3,3],[3,0]],'method':'bezier','closed':False}
        self.assertAlmostEqual(s.bounds(o)[3],2.25)

    def test_through_spline_bounds_enclose_overshoot(self):
        o={'type':'spline','points':[[0,0],[1,2],[2,2],[3,0]],'method':'through','closed':False}
        self.assertAlmostEqual(s.bounds(o)[3],2.25)
        self.assertFalse(s.wholly_inside(o,[0,0,3,2]))

    def test_exact_line_circle_and_arc_projection(self):
        line={'type':'line','a':[0,0],'b':[2,0]}
        self.assertEqual(s.nearest_point([.37,.08],line),[.37,0])
        self.assertEqual(s.nearest_point([3,.08],line),[2,0])
        circle={'type':'circle','center':[0,0],'radius':1}
        q=s.nearest_point([2,2],circle); self.assertAlmostEqual(q[0],2**-.5); self.assertAlmostEqual(g.dist(q,[0,0]),1)
        arc=g.arc_center([0,0],[1,0],[0,1])
        q=s.nearest_point([-2,0],arc); self.assertAlmostEqual(q[0],0); self.assertAlmostEqual(q[1],1)

    def test_ellipse_and_spline_projection_returns_curve_points(self):
        ellipse={'type':'ellipse','center':[0,0],'rx':2,'ry':1,'angle':0}
        q=s.nearest_point([1.7,.7],ellipse)
        self.assertAlmostEqual(q[0]**2/4+q[1]**2,1,places=10)
        tangent=[-2*q[1],q[0]/2]
        self.assertAlmostEqual(g.dot(g.sub([1.7,.7],q),tangent),0,places=7)
        spline={'type':'spline','points':[[0,0],[1,2],[2,0]],'method':'bezier','closed':False}
        q=s.nearest_point([1,1.08],spline)
        self.assertAlmostEqual(q[0],1,places=7); self.assertAlmostEqual(q[1],1,places=7)


class SelectionDocumentTests(unittest.TestCase):
    def setUp(self):
        self.d=Document(); self.d.add([{'type':'circle','center':[0,0],'radius':1}]); self.d.clear_selection()

    def test_whole_circle_vs_partial_radius(self):
        d=self.d; d.select_window([-1.1,-1.1],[1.1,1.1])
        self.assertEqual(d.selected,{0}); self.assertEqual(d.point_selection,{})
        d.select_window([1.1,.1],[.9,-.1])
        self.assertEqual(d.selected,set()); self.assertEqual(d.point_selection,{0:{'radius'}})
        d.select_window([-.1,-.1],[.1,.1])
        self.assertEqual(d.point_selection,{0:{'center'}})

    def test_partial_does_not_accidentally_select_whole_object(self):
        d=self.d; d.select_window([-.1,.9],[.1,1.1])
        # The top quadrant is a snap point, not an independent editable radius.
        self.assertFalse(d.selected); self.assertFalse(d.point_selection)
        d.select_window([.9,-.1],[1.1,.1]); d.select_window([-1.1,-1.1],[1.1,1.1],True)
        self.assertEqual(d.selected,{0}); self.assertFalse(d.point_selection)

    def test_preview_is_immutable_one_commit_one_undo(self):
        d=self.d; d.select_window([.9,-.1],[1.1,.1]); before=d.state(); count=len(d.history)
        updates=d.selection_updates(.5,0)
        self.assertEqual(d.state(),before); self.assertEqual(len(d.history),count)
        d.commit_updates(updates); self.assertEqual(d.objects[0]['radius'],1.5)
        self.assertEqual(len(d.history),count+1)
        d.undo(); self.assertEqual(d.state(),before); self.assertFalse(d.point_selection)
        d.redo(); self.assertEqual(d.objects[0]['radius'],1.5)

    def test_mixed_selection_and_atomic_invalid_move(self):
        d=self.d; d.add([{'type':'line','a':[3,0],'b':[4,0]}]); d.selected={1}; d.point_selection={0:{'radius'}}
        before=d.state(); count=len(d.history)
        with self.assertRaises(ValueError): d.selection_updates(-1,0)
        self.assertEqual(d.state(),before); self.assertEqual(len(d.history),count)
        d.move_selection(1,0)
        self.assertEqual(d.objects[0]['radius'],2); self.assertEqual(d.objects[1]['a'],[4,0])
        d.undo(); self.assertEqual(d.state(),before)

    def test_visibility_lock_and_noop_history(self):
        d=self.d; d.point_selection={0:{'radius'}}; d.objects[0]['locked']=True
        self.assertEqual(d.selection_updates(1,0),{})
        d.objects[0]['locked']=False; count=len(d.history)
        d.move_selection(0,0); self.assertEqual(len(d.history),count)
        d.toggle_layer('Layer1'); self.assertFalse(d.point_selection)
        d.select_window([-2,-2],[2,2]); self.assertFalse(d.selected)

    def test_selection_is_transient_and_layer_deletion_prunes(self):
        d=self.d; saved=d.payload(); d.saved=d.state()
        d.select_window([.9,-.1],[1.1,.1]); self.assertFalse(d.dirty)
        self.assertEqual(saved,d.payload())
        d.add_layer('Hidden'); d.set_layer('Hidden'); d.add([{'type':'line','a':[3,0],'b':[4,0]}])
        d.selected={1}; d.point_selection={0:{'radius'}}; d.delete_selected()
        self.assertFalse(d.point_selection)


if __name__=='__main__': unittest.main()
