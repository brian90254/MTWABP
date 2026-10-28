"""Real mouse and keyboard group selection, movement and polygon ungrouping."""
import os
import sys
import tkinter as tk
import unittest
from draft import Draft

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class GroupUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update()
        self.errors=[];self.callbacks=[];self.a.error=self.errors.append
        self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        a=self.a;a.origin=[250,350];a.scale=100
        a.doc.add([dict(type='line',a=[0,0],b=[2,0]),dict(type='line',a=[2,0],b=[2,2])]);a.draw()
    def tearDown(self):
        self.root.destroy();self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def click(self,p,shift=False):
        x,y=self.a.screen(p);self.clock=getattr(self,'clock',10000)+1000
        for event in ('<ButtonPress-1>','<ButtonRelease-1>'):
            self.a.canvas.event_generate(event,x=round(x),y=round(y),state=1 if shift else 0,time=self.clock)
        self.root.update()
    def test_shortcuts_click_shift_and_group_drag(self):
        a=self.a;a.canvas.focus_force();self.root.update()
        a.canvas.event_generate('<Control-KeyPress-g>');self.root.update()
        self.assertTrue(a.objects[0].get('group'));self.assertEqual(a.objects[0]['group'],a.objects[1]['group'])
        a.doc.clear_selection();a.draw();self.click([1,0]);self.assertEqual(a.selected,{0,1})
        self.click([1,0],shift=True);self.assertFalse(a.selected)
        self.click([1,0]);a.snap.set(False);a.grid_snap.set(False)
        x,y=a.screen([1,0]);xx,yy=a.screen([2,1])
        a.canvas.event_generate('<ButtonPress-1>',x=round(x),y=round(y))
        a.canvas.event_generate('<B1-Motion>',x=round(xx),y=round(yy));a.canvas.event_generate('<ButtonRelease-1>',x=round(xx),y=round(yy))
        self.root.update();self.assertEqual(a.objects[0]['a'],[1,1]);self.assertEqual(a.objects[1]['b'],[3,3])
        a.canvas.event_generate('<Control-Shift-KeyPress-G>');self.root.update()
        self.assertFalse(any(o.get('group') for o in a.objects));a.doc.clear_selection();a.draw()
        self.click([2,1]);self.assertEqual(a.selected,{0})
    def test_polygon_ungroup_and_closed_inspector(self):
        a=self.a;a.doc.add([dict(type='polygon',points=[[0,0],[1,0],[1,1],[0,1]],closed=True)]);a.draw()
        a.ungroup_selected();self.assertEqual(len(a.objects),6);self.assertEqual(a.selected,{2,3,4,5})
        a.group_selected();a.edit_dialog();self.root.update()
        labels=[w.cget('text') for w in a.edit_frame.winfo_children() if w.winfo_class()=='TLabel']
        self.assertTrue(any('closed group' in text for text in labels))
        a.doc.clear_selection();a.draw();self.click([0,.5]);self.assertEqual(a.selected,{2,3,4,5})
