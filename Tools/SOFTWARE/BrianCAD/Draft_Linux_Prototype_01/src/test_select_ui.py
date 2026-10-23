"""Real Tk mouse/drag selection regressions. A display is required."""
import copy
import math
import os
import sys
import tkinter as tk
from types import SimpleNamespace
import unittest
import cad_geometry as g
from draft import Draft


@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class SelectWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk(); self.app=Draft(self.root); self.root.update()
        self.errors=[]; self.callbacks=[]; self.app.error=self.errors.append
        self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.app.scale=100; self.app.origin=[400,300]
        self.app.grid_snap.set(False); self.app.snap.set(False)

    def tearDown(self):
        self.root.destroy(); self.assertFalse(self.callbacks,repr(self.callbacks))

    def event(self,p,shift=False):
        x,y=self.app.screen(p); return SimpleNamespace(x=x,y=y,state=1 if shift else 0)

    def click(self,p):
        self.app.click(self.event(p)); self.app.release_select(self.event(p))

    def drag(self,a,b):
        self.app.click(self.event(a)); self.app.drag_select(self.event(b)); self.app.release_select(self.event(b))

    def add_circle(self):
        self.app.doc.add([{'type':'circle','center':[0,0],'radius':1}]); self.app.doc.clear_selection()

    def test_click_controls_and_off_curve_handles_select_owner(self):
        a=self.app; self.add_circle()
        for p in [[0,0],[1,0],[0,1]]:
            a.doc.clear_selection(); self.click(p)
            self.assertEqual(a.selected,{0}); self.assertEqual(a.doc.point_selection,{})
        a.doc.add([{'type':'spline','points':[[3,0],[4,2],[5,0]],'method':'bezier','closed':False}]); a.doc.clear_selection()
        self.click([4,2]); self.assertEqual(a.selected,{1})
        self.assertFalse(self.errors)

    def test_actual_windows_whole_circle_vs_radius_and_shift_extension(self):
        a=self.app; self.add_circle()
        self.drag([-1.2,-1.2],[1.2,1.2]); self.assertEqual(a.selected,{0}); self.assertFalse(a.doc.point_selection)
        self.drag([1.2,.2],[.8,-.2]); self.assertFalse(a.selected); self.assertEqual(a.doc.point_selection,{0:{'radius'}})
        a.doc.add([{'type':'line','a':[3,0],'b':[4,0]}]); a.doc.selected=set(); a.doc.point_selection={0:{'radius'}}
        a.click(self.event([2.8,-.2],True)); a.drag_select(self.event([4.2,.2],True)); a.release_select(self.event([4.2,.2],True))
        self.assertEqual(a.selected,{1}); self.assertEqual(a.doc.point_selection,{0:{'radius'}})

    def test_radius_drag_preview_and_plain_click_promotion(self):
        a=self.app; self.add_circle(); a.doc.select_window([.9,-.1],[1.1,.1])
        before=a.doc.state(); history=len(a.doc.history)
        a.click(self.event([1,0])); a.drag_select(self.event([2,.3]))
        self.assertEqual(a.doc.state(),before); self.assertEqual(len(a.doc.history),history)
        self.assertAlmostEqual(a.drag_preview[0]['radius'],math.hypot(2,.3))
        a.release_select(self.event([2,.3])); self.assertEqual(len(a.doc.history),history+1)
        self.assertEqual(a.objects[0]['center'],[0,0]); self.assertFalse(a.selected)
        a.undo(); self.assertEqual(a.doc.state(),before)
        a.doc.select_window([.9,-.1],[1.1,.1]); self.click([1,0])
        self.assertEqual(a.selected,{0}); self.assertFalse(a.doc.point_selection)

    def test_live_curve_target_and_release_coordinates(self):
        a=self.app; a.snap.set(True)
        a.doc.add([{'type':'circle','center':[-3,0],'radius':.5}, {'type':'line','a':[0,2],'b':[4,2]}]); a.selected={0}
        history=len(a.doc.history)
        a.click(self.event([-3,0])); a.drag_select(self.event([1.37,2.04]))
        self.assertEqual(a.marker,'on line'); self.assertEqual(a.drag_preview[0]['center'],[1.37,2.])
        self.assertEqual(a.objects[0]['center'],[-3,0])
        # Final mouse release is recomputed even without a matching Motion event.
        a.release_select(self.event([1.67,2.03]))
        self.assertAlmostEqual(a.objects[0]['center'][0],1.67); self.assertEqual(a.objects[0]['center'][1],2)
        self.assertEqual(len(a.doc.history),history+1)
        a.undo(); self.assertEqual(a.objects[0]['center'],[-3,0])

    def test_grid_handle_drop_and_no_self_snapping(self):
        a=self.app; a.snap.set(True); a.grid_snap.set(True)
        a.doc.add([{'type':'line','a':[-3,0],'b':[-2,0]}]); a.selected={0}
        self.drag([-3,0],[2.26,.24])
        self.assertEqual(a.objects[0]['a'],[2.25,.25]); self.assertEqual(a.objects[0]['b'],[3.25,.25])
        # Move a selected endpoint close to its own old location; it must not stick there.
        a.snap.set(True); a.grid_snap.set(False); a.doc.selected=set(); a.doc.point_selection={0:{'b'}}
        self.drag([3.25,.25],[3.30,.32])
        self.assertAlmostEqual(a.objects[0]['b'][0],3.31); self.assertAlmostEqual(a.objects[0]['b'][1],.31)
        self.assertEqual(a.marker,'45°')  # alignment remains live, without self-snapping

    def test_mixed_whole_and_point_selection_moves_together(self):
        a=self.app; self.add_circle(); a.doc.add([{'type':'line','a':[3,0],'b':[4,0]}])
        a.doc.selected={1}; a.doc.point_selection={0:{'radius'}}
        self.drag([3,0],[3.5,1])
        self.assertEqual(a.objects[1]['a'],[3.5,1]); self.assertEqual(a.objects[0]['center'],[0,0])
        self.assertAlmostEqual(a.objects[0]['radius'],math.hypot(1.5,1))

    def test_cancel_noop_and_invalid_deformation_do_not_commit(self):
        a=self.app; a.doc.add([{'type':'line','a':[0,0],'b':[2,0]}]); a.doc.selected=set(); a.doc.point_selection={0:{'b'}}
        before=a.doc.state(); history=len(a.doc.history)
        a.click(self.event([2,0])); a.drag_select(self.event([3,1])); a.cancel()
        self.assertEqual(a.doc.state(),before); self.assertEqual(len(a.doc.history),history)
        a.click(self.event([2,0])); a.drag_select(self.event([3,1])); a.release_select(self.event([2,0]))
        self.assertEqual(a.doc.state(),before); self.assertEqual(len(a.doc.history),history)
        self.drag([2,0],[0,0]); self.assertTrue(self.errors)
        self.assertEqual(a.doc.state(),before); self.assertEqual(len(a.doc.history),history)
        self.drag([2,0],[3,0]); self.assertEqual(a.objects[0]['b'],[3,0])

    def test_curve_hover_quadrants_and_anchor_priority(self):
        a=self.app; a.snap.set(True); self.add_circle()
        for target in [[1,0],[0,1],[-1,0],[0,-1]]:
            p,label=a.snap_point(g.add(target,[.02,.02])); self.assertEqual(label,'quadrant')
            self.assertLess(g.dist(p,target),1e-10)
        p,label=a.snap_point([.72,.72]); self.assertEqual(label,'on curve'); self.assertAlmostEqual(g.dist(p,[0,0]),1)
        a.doc.add([{'type':'line','a':[2,2],'b':[4,2]}])
        self.assertEqual(a.snap_point([2.37,2.03]),([2.37,2.],'on line'))
        self.assertEqual(a.snap_point([2.02,2.01])[1],'endpoint')
        a.doc.toggle_layer('Layer1')
        self.assertEqual(a.snap_point([2.37,2.03]),([2.37,2.03],''))

    def test_real_button_bindings_drag_selection(self):
        a=self.app; a.doc.add([{'type':'line','a':[0,0],'b':[2,0]}]); a.draw(); self.root.update()
        x,y=a.screen([1,0]); tx,ty=a.screen([2,1])
        a.canvas.event_generate('<ButtonPress-1>',x=int(x),y=int(y))
        a.canvas.event_generate('<B1-Motion>',x=int(tx),y=int(ty))
        a.canvas.event_generate('<ButtonRelease-1>',x=int(tx),y=int(ty)); self.root.update()
        self.assertEqual(a.objects[0]['a'],[1,1]); self.assertEqual(a.objects[0]['b'],[3,1])


if __name__=='__main__': unittest.main()
