"""Grid point snaps must beat plain guide projections while placing a line end."""
import os
import sys
import tkinter as tk
import unittest
from types import SimpleNamespace
from test_grid import editor,Value
from snap_tracking import SnapHistory
from draft import Draft

class LineGridPriorityTests(unittest.TestCase):
    def make(self,method='Two points'):
        app=editor();app.tool=Value(method)
        app.params={'x':Value('.11'),'y':Value('0')}
        app.doc.add([dict(type='line',a=[.11,0],b=[3.11,3])])
        app.points=[[.11,0]];app.start=[.11,0]
        return app
    def test_grid_intersection_beats_plain_extension_and_perpendicular(self):
        app=self.make()
        for scale in (90,100):
            app.scale=scale
            for point in ([1,1],[1.01,.99],[-1,1]):
                result,label=app.snap_point(point)
                self.assertEqual(label,'grid intersection')
                self.assertEqual(result,[round(v/.25)*.25 for v in point])
    def test_connected_points_and_disabled_grid_keep_expected_snaps(self):
        app=self.make('Connected points')
        self.assertEqual(app.snap_point([1,1]),([1.,1.],'grid intersection'))
        app.grid_snap.set(False)
        point,label=app.snap_point([1,1])
        self.assertEqual(label,'extension guide')
        self.assertAlmostEqual(point[0],1.055);self.assertAlmostEqual(point[1],.945)
        app.snap.set(False);self.assertEqual(app.snap_point([1,1]),([1,1],''))
    def test_object_points_and_real_guide_intersections_still_work(self):
        app=self.make();app.doc.add([dict(type='circle',center=[1,1],radius=.3)])
        self.assertEqual(app.snap_point([1,1]),([1,1],'center'))
        app=self.make();app.snap_history=SnapHistory();app.snap_history.remember([.11,0],'endpoint')
        point,label=app.snap_point([1,1])
        self.assertEqual(label,'grid intersection');self.assertEqual(point,[1,1])
        point,label=app.snap_point([1,.89])
        self.assertIn('guide / grid intersection',label)
        self.assertAlmostEqual(point[0],1);self.assertAlmostEqual(point[1],.89)

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class LineEndGridUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[];self.callbacks=[]
        self.a.error=self.errors.append;self.root.report_callback_exception=lambda *a:self.callbacks.append(a)
    def tearDown(self):
        self.root.destroy();self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def click(self,point):
        x,y=self.a.screen(point)
        self.a.click(SimpleNamespace(x=round(x),y=round(y),state=0));self.root.update()
    def test_mouse_preview_and_commit_snap_end_for_both_line_methods(self):
        a=self.a;a.scale=100
        for method in ('Two points','Connected points'):
            a.doc.objects=[];a.doc.add([dict(type='line',a=[.11,0],b=[3.11,3])])
            a.family.set('Lines');a.family_changed();a.tool.set(method);a.method_changed();self.root.update()
            self.click([.11,0])
            x,y=a.screen([1,1]);a.motion(SimpleNamespace(x=round(x),y=round(y),state=0))
            self.assertEqual(a.marker,'grid intersection');self.assertEqual(a.mouse,[1,1])
            self.assertEqual(a.preview()['b'],[1,1])
            self.click([1,1]);self.assertEqual(a.objects[-1]['a'],[.11,0]);self.assertEqual(a.objects[-1]['b'],[1,1])
            self.assertEqual(a.field_point(1),[1,1])
