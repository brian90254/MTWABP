"""Rotation may use selected geometry as pivot/start/end snap references."""
import copy
import os
import sys
import tkinter as tk
import unittest
from types import SimpleNamespace
from draft import Draft
from test_grid import editor,Value
import cad_geometry as g


class RotateSnapTests(unittest.TestCase):
    def test_selected_anchors_at_each_stage_and_explicit_exclusion(self):
        a=editor();a.family=Value('Modify');a.tool=Value('Rotate');a.grid_snap.set(False)
        a.doc.add([dict(type='polygon',points=[[1.13,2.17],[3.13,2.17],[1.13,4.17]],closed=True)])
        a.doc.selected={0}
        for stage in ([],[[1.13,2.17]],[[1.13,2.17],[3.13,2.17]]):
            a.points=stage;a.start=stage[0] if stage else None
            for p in a.objects[0]['points']:
                point,label=a.snap_point(g.add(p,[.02,.01]));self.assertEqual(point,p);self.assertEqual(label,'vertex')
        a.points=[];a.start=None
        p=[1.15,2.18];self.assertEqual(a.snap_point(p,exclude={0}),(p,''))
        a.snap.set(False);self.assertEqual(a.snap_point(p),(p,''))

    def test_partial_spline_control_and_move_still_excluded(self):
        a=editor();a.family=Value('Modify');a.tool=Value('Rotate');a.grid_snap.set(False)
        a.doc.add([dict(type='spline',method='bezier',closed=False,points=[[1,1],[2.13,4.17],[5,1]])])
        a.doc.clear_selection();a.doc.point_selection={0:{'p1'}}
        self.assertEqual(a.snap_point([2.15,4.18]),([2.13,4.17],'control point'))
        a.tool.set('Move');self.assertEqual(a.snap_point([2.15,4.18]),([2.15,4.18],''))


@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class RotateSnapUITests(unittest.TestCase):
    def test_three_nearby_mouse_picks_rotate_selected_geometry_and_undo(self):
        root=tk.Tk();errors=[]
        try:
            a=Draft(root);root.update();a.error=errors.append
            a.doc.add([dict(type='polygon',points=[[1.13,2.17],[3.13,2.17],[1.13,4.17]],closed=True)])
            a.doc.selected={0};before=copy.deepcopy(a.objects)
            a.family.set('Modify');a.family_changed();a.tool.set('Rotate');a.method_changed()
            a.grid_snap.set(False)
            for p in before[0]['points']:
                x,y=a.screen(g.add(p,[.02,.01]));event=SimpleNamespace(x=x,y=y,state=0)
                a.motion(event);self.assertEqual(a.mouse,p)
                a.click(event);root.update()
            self.assertFalse(errors)
            for actual,expected in zip(a.objects[0]['points'],[[1.13,2.17],[1.13,4.17],[-.87,2.17]]):
                self.assertLess(g.dist(actual,expected),1e-8)
            a.undo();self.assertEqual(a.objects,before)
        finally:root.destroy()
