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
        self.assertTrue(a.canvas.find_withtag('snap-marker'))
        self.assertFalse(a.canvas.find_withtag('snap-label'))
        self.wait(650)
        label=a.canvas.find_withtag('snap-label')
        self.assertEqual(len(label),1)
        self.assertEqual(a.canvas.itemcget(label[0],'fill'),SNAP_LABEL_COLOR)
        self.assertLess(abs(a.snap_label_font.cget('size')),abs(tkfont.nametofont('TkDefaultFont').cget('size')))
        a.motion(self.event([1.03,.01]))
        self.assertFalse(a.canvas.find_withtag('snap-label'))

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
