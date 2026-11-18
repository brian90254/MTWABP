"""Workspace scroll modifiers, smooth Aqua deltas, and pointer-centered zoom."""
import os
import sys
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from draft import Draft


class ScrollTests(unittest.TestCase):
    def app(self,system):
        a=Draft.__new__(Draft);a.origin=[100.,200.]
        a.root=SimpleNamespace(tk=SimpleNamespace(call=lambda *args:system))
        a.cancel_window_zoom=Mock();a.cancel_snap_hover=Mock();a.motion=Mock();a.zoom=Mock()
        return a
    def event(self,delta=0,state=0,num=None):return SimpleNamespace(delta=delta,state=state,num=num,x=20,y=30)
    def test_mac_small_deltas_pan_both_axes_and_zero_is_noop(self):
        a=self.app('aqua');a.scroll_workspace(self.event(delta=1));self.assertEqual(a.origin,[100,208])
        a.scroll_workspace(self.event(delta=-2,state=1));self.assertEqual(a.origin,[84,208])
        a.scroll_workspace(self.event(delta=.5));self.assertEqual(a.origin,[84,212])
        a.motion.reset_mock();a.scroll_workspace(self.event());a.motion.assert_not_called();a.zoom.assert_not_called()
    def test_control_overrides_shift_zoom_magnitude_and_direction(self):
        a=self.app('aqua');a.scroll_workspace(self.event(delta=1,state=5))
        self.assertAlmostEqual(a.zoom.call_args.args[1],1.15**.2);self.assertEqual(a.origin,[100,200])
        a.scroll_workspace(self.event(delta=-2,state=4));self.assertAlmostEqual(a.zoom.call_args.args[1],1.15**-.4)
    def test_windows_and_linux_wheel_events(self):
        for system in ('win32','x11'):
            a=self.app(system);a.scroll_workspace(self.event(delta=120));self.assertEqual(a.origin,[100,240])
            a.scroll_workspace(self.event(delta=-60,state=1));self.assertEqual(a.origin,[80,240])
            a.scroll_workspace(self.event(num=5));self.assertEqual(a.origin,[80,200])
            a.scroll_workspace(self.event(num=4,state=4));self.assertEqual(a.zoom.call_args.args[1],1.15)
            a.scroll_workspace(self.event(delta=-120,state=4));self.assertAlmostEqual(a.zoom.call_args.args[1],1/1.15)


@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class ScrollUITests(unittest.TestCase):
    def test_wheel_bindings_pan_and_zoom_without_editing_document(self):
        root=tk.Tk();errors=[]
        try:
            a=Draft(root);root.report_callback_exception=lambda *args:errors.append(args);root.update()
            a.doc.add([dict(type='circle',center=[0,0],radius=1)])
            before=a.doc.state();history=len(a.doc.history);origin=list(a.origin);scale=a.scale
            a.canvas.event_generate('<MouseWheel>',x=200,y=200,delta=120);root.update()
            self.assertGreater(a.origin[1],origin[1]);self.assertEqual(a.origin[0],origin[0]);self.assertEqual(a.scale,scale)
            origin=list(a.origin)
            a.canvas.event_generate('<Shift-MouseWheel>',x=200,y=200,delta=-120);root.update()
            self.assertLess(a.origin[0],origin[0]);self.assertEqual(a.origin[1],origin[1])
            point=a.world(200,200)
            a.canvas.event_generate('<Control-MouseWheel>',x=200,y=200,delta=120);root.update()
            self.assertGreater(a.scale,scale)
            for actual,expected in zip(a.world(200,200),point):self.assertAlmostEqual(actual,expected)
            self.assertEqual(a.doc.state(),before);self.assertEqual(len(a.doc.history),history);self.assertFalse(errors)
        finally:root.destroy()
