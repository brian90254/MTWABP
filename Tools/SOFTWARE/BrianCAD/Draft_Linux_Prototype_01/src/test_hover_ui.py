"""Hover feedback timing must not delay actual snapping or dragging."""
import os
import sys
import tkinter as tk
from tkinter import font as tkfont
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from draft import Draft, SNAP_HOVER_MS, SNAP_LABEL_COLOR


@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class HoverTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk(); self.app=Draft(self.root); self.root.update()
        self.errors=[]; self.root.report_callback_exception=lambda *args:self.errors.append(args)
        self.app.doc.add([{'type':'circle','center':[0,0],'radius':1}])
        self.app.scale=100; self.app.origin=[400,300]; self.app.grid_snap.set(False)

    def tearDown(self):
        self.root.destroy(); self.assertFalse(self.errors,repr(self.errors))

    def event(self,p):
        x,y=self.app.screen(p); return SimpleNamespace(x=x,y=y,state=0)

    def wait(self,ms):
        self.root.after(ms,self.root.quit); self.root.mainloop()

    def test_real_delay_and_subtle_style(self):
        a=self.app; self.assertEqual(SNAP_HOVER_MS,600)
        a.motion(self.event([1.02,.01]))
        self.assertEqual(a.mouse,[1.,0.]); self.assertEqual(a.marker,'quadrant')
        markers=a.canvas.find_withtag('snap-marker')
        self.assertEqual(len(markers),2)
        for marker in markers:
            self.assertEqual(a.canvas.type(marker),'line')
            self.assertEqual(a.canvas.itemcget(marker,'fill'),'black')
        self.assertEqual(a.canvas.coords(markers[0]),[497.,297.,503.,303.])
        self.assertEqual(a.canvas.coords(markers[1]),[497.,303.,503.,297.])
        self.assertEqual(a.canvas.cget('cursor'),'arrow')
        self.assertGreater(a.select_icon.width(),0)
        self.assertFalse(a.canvas.find_withtag('snap-label'))
        self.wait(650)
        label=a.canvas.find_withtag('snap-label')
        self.assertEqual(len(label),1)
        self.assertEqual(a.canvas.itemcget(label[0],'fill'),SNAP_LABEL_COLOR)
        self.assertLess(abs(a.snap_label_font.cget('size')),abs(tkfont.nametofont('TkDefaultFont').cget('size')))
        a.motion(self.event([1.03,.01]))
        self.assertFalse(a.canvas.find_withtag('snap-label'))

    def test_object_snap_history_and_tracking_guides(self):
        a=self.app
        a.motion(self.event([1.01,.01]))
        self.assertEqual(a.snap_history.points,[[1.,0.]])
        a.motion(self.event([1.04,2.0]))  # free space, close to remembered X
        guides=a.canvas.find_withtag('tracking-guide')
        self.assertEqual(len(guides),1)
        self.assertEqual(a.canvas.coords(guides[0]),[500.,0.,500.,float(a.canvas.winfo_height())])
        self.assertEqual(a.canvas.itemcget(guides[0],'dash'),'1 5')
        labels=a.canvas.find_withtag('tracking-label')
        self.assertEqual([a.canvas.itemcget(i,'text') for i in labels],['align x'])
        # Tracking guides now constrain the corresponding coordinate immediately.
        self.assertEqual(a.mouse,[1.,2.]); self.assertEqual(a.marker,'align x')
        a.motion(self.event([3,.04]))
        labels=a.canvas.find_withtag('tracking-label')
        self.assertEqual([a.canvas.itemcget(i,'text') for i in labels],['align y'])
        self.assertEqual(a.snap_history.points,[[1.,0.]])
        a.leave_canvas(self.event([3,.04]))
        self.assertFalse(a.canvas.find_withtag('tracking-guide'))
        self.assertEqual(a.snap_history.points,[[1.,0.]])
        a.motion(self.event([1.,2.])); a.snap.set(False); a.draw()
        self.assertFalse(a.canvas.find_withtag('tracking-guide'))
        a.snap.set(True); a.draw(); self.assertTrue(a.canvas.find_withtag('tracking-guide'))
        a.family.set('Lines'); a.family_changed()
        self.assertEqual(a.snap_history.points,[])
        self.assertFalse(a.canvas.find_withtag('tracking-guide'))
        a.motion(self.event([1.,0.])); self.assertTrue(a.snap_history.points)
        a.tool.set('Connected points'); a.method_changed()
        self.assertEqual(a.snap_history.points,[])

    def test_alignment_snap_mouse_commit_and_drag(self):
        a=self.app; a.family.set('Lines'); a.family_changed()
        a.snap_history.remember([2,4],'endpoint')
        a.snap_history.remember([5,3],'quadrant')
        before=list(a.snap_history.points)
        a.pick([6,6]); a.motion(self.event([2.04,3.03]))
        self.assertEqual(a.mouse,[2,3]); self.assertEqual(a.marker,'align x + align y')
        self.assertEqual(a.snap_history.points,before)
        a.click(self.event([2.04,3.03]))
        self.assertEqual(a.objects[-1]['b'],[2,3])
        a.return_to_select(); a.snap_history.remember([3,4],'endpoint')
        a.selected={0}; a.click(self.event([0,0]))
        a.drag_select(self.event([3.03,4.04]))
        self.assertEqual(a.drag_preview[0]['center'],[3,4])
        a.release_select(self.event([3.03,4.04]))
        self.assertEqual(a.objects[0]['center'],[3,4])

    def test_single_guide_intersections_commit_exact_line_endpoints(self):
        import math
        a=self.app; a.family.set('Lines'); a.family_changed()
        a.snap_history.remember([.5,4],'endpoint'); before=list(a.snap_history.points)
        a.pick([3,3]); e=self.event([.52,.88]); a.motion(e)
        self.assertEqual(a.marker,'align x / object intersection')
        self.assertEqual(a.mouse[0],.5)
        self.assertAlmostEqual(a.mouse[1],math.sqrt(3)/2)
        a.click(e)
        self.assertEqual(a.objects[-1]['b'][0],.5)
        self.assertAlmostEqual(a.objects[-1]['b'][1],math.sqrt(3)/2)
        self.assertEqual(a.snap_history.points,before)
        a.method_changed(); a.grid_snap.set(True)
        a.snap_history.remember([2.13,5],'endpoint'); before=list(a.snap_history.points)
        a.pick([4,4]); e=self.event([2.15,1.02]); a.motion(e)
        self.assertEqual(a.marker,'align x / grid intersection')
        self.assertEqual(a.mouse,[2.13,1.]); a.click(e)
        self.assertEqual(a.objects[-1]['b'],[2.13,1.])
        self.assertEqual(a.snap_history.points,before)

    def test_memory_acquires_tangent_but_ignores_all_grid_snaps(self):
        a=self.app; a.family.set('Lines'); a.family_changed()
        a.pick([2,0])
        import math
        tangent=[.5,math.sqrt(3)/2]
        a.motion(self.event(tangent)); self.assertEqual(a.marker,'tangent')
        self.assertAlmostEqual(a.snap_history.points[0][1],tangent[1])
        a.cancel(); self.assertTrue(a.snap_history.points)  # same tool retains memory
        a.doc.add([{'type':'line','a':[3,.1],'b':[5,.1]}]); a.grid_snap.set(True)
        before=list(a.snap_history.points)
        a.motion(self.event([3.5,.12])); self.assertEqual(a.marker,'line/grid intersection')
        self.assertEqual(a.snap_history.points,before)
        a.motion(self.event([6.25,6.25])); self.assertEqual(a.marker,'grid intersection')
        self.assertEqual(a.snap_history.points,before)

    def test_select_uses_native_cursor_during_motion_drag_and_tool_changes(self):
        a=self.app; e=self.event([1.02,.01])
        self.assertEqual(a.canvas.cget('cursor'),'arrow')
        a.motion(e)
        self.assertFalse(a.canvas.find_withtag('select-pointer'))
        self.assertTrue(a.canvas.find_withtag('snap-marker'))
        a.click(e); a.drag_select(self.event([2.02,1.01]))
        self.assertEqual(a.canvas.cget('cursor'),'arrow')
        self.assertFalse(a.canvas.find_withtag('select-pointer'))
        a.release_select(self.event([2.02,1.01])); a.leave_canvas(e)
        a.family.set('Lines'); a.family_changed()
        self.assertEqual(a.canvas.cget('cursor'),'arrow')
        a.return_to_select(); a.motion(e)
        self.assertEqual(a.canvas.cget('cursor'),'arrow')
        self.assertFalse(a.canvas.find_withtag('select-pointer'))
        self.assertGreater(a.select_icon.width(),0)

    def test_movement_restarts_and_leave_cancels(self):
        a=self.app
        with patch('draft.SNAP_HOVER_MS',60):
            a.motion(self.event([1.01,.01])); first=a._snap_hover_job
            a.motion(self.event([1.01,.01])); self.assertEqual(a._snap_hover_job,first)
            a.motion(self.event([.01,1.01])); second=a._snap_hover_job
            self.assertNotEqual(first,second)
            with self.assertRaises(tk.TclError): self.root.tk.call('after','info',first)
            self.wait(100); self.assertTrue(a.canvas.find_withtag('snap-label'))
            a.motion(self.event([.02,1.01])); self.assertFalse(a.canvas.find_withtag('snap-label'))
            a.leave_canvas(self.event([.02,1.01])); self.assertIsNone(a._snap_hover_job)
            self.wait(100); self.assertFalse(a.canvas.find_withtag('snap-label'))
            a.motion(self.event([1.01,.01])); a.cancel()
            self.wait(100); self.assertFalse(a.canvas.find_withtag('snap-label'))

    def test_drag_snaps_immediately_but_label_waits(self):
        a=self.app; a.grid_snap.set(True); a.selected={0}
        with patch('draft.SNAP_HOVER_MS',60):
            a.click(self.event([1,0])); a.drag_select(self.event([2.26,1.26]))
            self.assertEqual(a.mouse,[2.25,1.25]); self.assertEqual(a.marker,'grid intersection')
            self.assertEqual(a.drag_preview[0]['center'],[1.25,1.25])
            self.assertEqual(a.objects[0]['center'],[0,0])
            self.assertFalse(a.canvas.find_withtag('snap-label'))
            self.wait(100); self.assertTrue(a.canvas.find_withtag('snap-label'))
            a.release_select(self.event([2.26,1.26]))
            self.assertEqual(a.objects[0]['center'],[1.25,1.25])


if __name__=='__main__': unittest.main()
