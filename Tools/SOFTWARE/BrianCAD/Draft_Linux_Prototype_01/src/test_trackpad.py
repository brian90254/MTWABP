"""Workspace scroll modifiers, smooth Aqua deltas, and pointer-centered zoom."""
import os
import sys
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from draft import Draft
from cad_scroll import touchpad_deltas


class ScrollTests(unittest.TestCase):
    def app(self,system):
        a=Draft.__new__(Draft);a.origin=[100.,200.]
        a.root=SimpleNamespace(tk=SimpleNamespace(call=lambda *args:system))
        a.cancel_window_zoom=Mock();a.cancel_snap_hover=Mock();a.motion=Mock();a.zoom=Mock()
        return a
    def event(self,delta=0,state=0,num=None):return SimpleNamespace(delta=delta,state=state,num=num,x=20,y=30)
    def test_mac_wheel_always_zooms_at_half_sensitivity(self):
        a=self.app('aqua')
        for state in (0,1,4,5):
            a.scroll_workspace(self.event(delta=1,state=state))
            self.assertAlmostEqual(a.zoom.call_args.args[1],1.15**.1)
            self.assertEqual(a.origin,[100,200]);a.motion.assert_not_called()
        a.scroll_workspace(self.event(delta=-2));self.assertAlmostEqual(a.zoom.call_args.args[1],1.15**-.2)
        a.zoom.reset_mock();a.scroll_workspace(self.event());a.zoom.assert_not_called()
    def test_real_mac_packed_values_and_modifiers(self):
        a=self.app('aqua')
        for raw,expected in [(65535,(0,-1)),(65534,(0,-2)),(131070,(1,-2)),
                             (131071,(1,-1)),(65537,(1,1)),(-1,(-1,-1)),(1,(0,1))]:
            self.assertEqual(touchpad_deltas(raw),expected)
            origin=list(a.origin);a.scroll_workspace(self.event(delta=raw),precise=True)
            self.assertEqual(a.origin,[origin[0],origin[1]+expected[1]*8])
        origin=list(a.origin)
        a.scroll_workspace(self.event(delta=65535,state=1),precise=True)
        self.assertEqual(a.origin,[origin[0]-8,origin[1]])
        a.scroll_workspace(self.event(delta=65534,state=4),precise=True)
        self.assertAlmostEqual(a.zoom.call_args.args[1],1.15**-.4)
        a.scroll_workspace(self.event(delta=1,state=5),precise=True)
        self.assertAlmostEqual(a.zoom.call_args.args[1],1.15**.2)
    def test_precise_zero_and_horizontal_axis_shift_fallback(self):
        a=self.app('aqua');a.scroll_workspace(self.event(delta=0),precise=True);a.motion.assert_not_called()
        a.scroll_workspace(self.event(delta=65536),precise=True);a.motion.assert_not_called()
        a.scroll_workspace(self.event(delta=65536,state=1),precise=True);self.assertEqual(a.origin,[108,200])
        a.zoom.reset_mock();a.scroll_workspace(self.event(delta=65536,state=4),precise=True);a.zoom.assert_not_called()
        self.assertEqual(touchpad_deltas(0x80007fff),(-32768,32767))
        self.assertEqual(touchpad_deltas(0x7fff8000),(32767,-32768))

    def test_windows_and_linux_wheel_events(self):
        for system in ('win32','x11'):
            a=self.app(system)
            for state in (0,1,4,5):
                for delta in (120,-120,60):
                    a.scroll_workspace(self.event(delta=delta,state=state))
                    self.assertAlmostEqual(a.zoom.call_args.args[1],1.15**(delta/120*.5))
                for number,direction in ((4,1),(5,-1)):
                    a.scroll_workspace(self.event(num=number,state=state))
                    self.assertAlmostEqual(a.zoom.call_args.args[1],1.15**(direction*.5))
            self.assertEqual(a.origin,[100,200]);a.motion.assert_not_called()


@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class ScrollUITests(unittest.TestCase):
    def test_wheel_bindings_only_zoom_without_editing_document(self):
        root=tk.Tk();errors=[]
        try:
            a=Draft(root);root.report_callback_exception=lambda *args:errors.append(args);root.update()
            a.doc.add([dict(type='circle',center=[0,0],radius=1)])
            before=a.doc.state();history=len(a.doc.history)
            aqua=root.tk.call('tk','windowingsystem')=='aqua';delta=1 if aqua else 120
            factor=1.15**(.1 if aqua else .5)
            for pattern in ('<MouseWheel>','<Shift-MouseWheel>','<Control-MouseWheel>'):
                point=a.world(200,200);scale=a.scale
                a.canvas.event_generate(pattern,x=200,y=200,delta=delta);root.update()
                self.assertAlmostEqual(a.scale,scale*factor)
                for actual,expected in zip(a.world(200,200),point):self.assertAlmostEqual(actual,expected)
            self.assertEqual(a.doc.state(),before);self.assertEqual(len(a.doc.history),history);self.assertFalse(errors)
        finally:root.destroy()

    def test_precise_tk_dispatch_when_supported(self):
        root=tk.Tk()
        try:
            try:root.bind('<TouchpadScroll>',lambda e:None)
            except tk.TclError:self.skipTest('Installed Tk does not support TouchpadScroll')
            a=Draft(root);root.update();origin=list(a.origin)
            a.canvas.event_generate('<TouchpadScroll>',x=200,y=200,delta=65535);root.update()
            self.assertEqual(a.origin,[origin[0],origin[1]-8])
            origin=list(a.origin)
            a.canvas.event_generate('<Shift-TouchpadScroll>',x=200,y=200,delta=65535);root.update()
            self.assertEqual(a.origin,[origin[0]-8,origin[1]])
            point=a.world(200,200);scale=a.scale
            a.canvas.event_generate('<Control-TouchpadScroll>',x=200,y=200,delta=65535);root.update()
            self.assertLess(a.scale,scale)
            for actual,expected in zip(a.world(200,200),point):self.assertAlmostEqual(actual,expected)
            content=a.panels.create('library','Library',a.close_library)
            for i in range(100):tk.Label(content,text=str(i)).pack()
            a.panels.rebind('library');root.update()
            panel_canvas=a.panels.panels['library']['canvas']
            panel_canvas.event_generate('<Configure>');root.update();before=panel_canvas.yview()[0]
            content.winfo_children()[0].event_generate('<TouchpadScroll>',delta=65535);root.update()
            self.assertGreater(panel_canvas.yview()[0],before)
        finally:root.destroy()
