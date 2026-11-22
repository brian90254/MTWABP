"""Explicit Move uses original selection snaps and a reversible ghost preview."""
import copy
import os
import sys
import tkinter as tk
import unittest
from types import SimpleNamespace
from draft import Draft
import cad_geometry as g

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class ModifyMovePreviewTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[];self.callbacks=[]
        self.a.error=self.errors.append;self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.a.grid_snap.set(False)
        self.a.doc.add([dict(type='line',a=[1.13,2.17],b=[3.13,2.17])])
        self.a.family.set('Modify');self.a.family_changed();self.a.tool.set('Move');self.a.method_changed()
    def tearDown(self):
        self.root.destroy();self.assertFalse(self.errors);self.assertFalse(self.callbacks,repr(self.callbacks))
    def event(self,p):
        x,y=self.a.screen(p);return SimpleNamespace(x=x,y=y,state=0)
    def test_original_endpoint_snaps_preview_commit_and_undo(self):
        a=self.a;before=copy.deepcopy(a.objects);history=len(a.doc.history)
        a.motion(self.event([1.15,2.18]));self.assertEqual(a.marker,'endpoint')
        a.click(self.event([1.15,2.18]));self.assertEqual(a.points,[[1.13,2.17]])
        a.motion(self.event([3.15,2.18]));a.draw()
        self.assertEqual(a.mouse,[3.13,2.17]);self.assertEqual(a.marker,'endpoint')
        self.assertTrue(a.canvas.find_withtag('move-origin-ghost'));self.assertTrue(a.canvas.find_withtag('modify-move-preview'))
        self.assertEqual(a.objects,before);self.assertEqual(len(a.doc.history),history)
        self.assertEqual(a._modify_move_preview[0]['a'],[3.13,2.17])
        a.click(self.event([3.15,2.18]));self.assertEqual(a.objects[0]['a'],[3.13,2.17])
        self.assertFalse(a.canvas.find_withtag('move-origin-ghost'));self.assertFalse(a.canvas.find_withtag('modify-move-preview'))
        self.assertEqual(len(a.doc.history),history+1);a.undo();self.assertEqual(a.objects,before)
    def test_partial_control_copy_and_cancellation(self):
        a=self.a;a.doc.clear_selection();a.doc.point_selection={0:{'b'}};before=copy.deepcopy(a.objects)
        a.click(self.event([3.15,2.18]));a.motion(self.event([4.13,3.17]));a.draw()
        self.assertEqual(a._modify_move_preview[0]['a'],before[0]['a'])
        self.assertEqual(a.objects,before);a.cancel();self.assertFalse(a.canvas.find_withtag('modify-move-preview'))
        a.copy_mode.set(True);a.click(self.event([3.15,2.18]));a.click(self.event([4.13,3.17]))
        self.assertEqual(a.objects[0],before[0]);self.assertEqual(len(a.objects),2)
        self.assertEqual(a.objects[1]['a'],before[0]['a']);self.assertLess(g.dist(a.objects[1]['b'],[4.13,3.17]),1e-8)
