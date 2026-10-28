"""Offset tool preselection, direction fields, mouse preview and Apply."""
import copy
import os
import sys
import tkinter as tk
import unittest
from unittest.mock import patch
from draft import Draft

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class OffsetUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update()
        self.errors=[];self.callbacks=[];self.a.error=self.errors.append
        self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.info=patch('draft.messagebox.showinfo');self.info.start()
        self.a.doc.add([dict(type='line',a=[0,0],b=[3,0],color='#123456',weight=.02)])
    def tearDown(self):
        self.root.destroy();self.info.stop()
        self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def activate(self):
        self.a.family.set('Offset');self.a.family_changed();self.root.update()
    def click(self,p):
        x,y=self.a.screen(p)
        for event in ('<ButtonPress-1>','<ButtonRelease-1>'):
            self.a.canvas.event_generate(event,x=round(x),y=round(y))
        self.root.update()
    def entry(self,key):
        name=str(self.a.params[key])
        def find(w):
            if w.winfo_class()=='TEntry' and str(w.cget('textvariable'))==name:return w
            for child in w.winfo_children():
                result=find(child)
                if result is not None:return result
        return find(self.a.parameter_frame)
    def test_active_x_or_y_field_click_sets_both_then_apply_undo(self):
        a=self.a;self.activate();before=a.doc.state();n=len(a.doc.history)
        self.assertEqual(len(a.offset_sources),1);self.assertEqual(set(a.params),{'offset','x','y'})
        a.params['offset'].set('.5')
        for key,p in [('x',[1,1]),('y',[2,-1])]:
            self.entry(key).focus_force();self.root.update();self.click(p)
            self.assertAlmostEqual(float(a.params['x'].get()),p[0]);self.assertAlmostEqual(float(a.params['y'].get()),p[1])
            self.assertTrue(a.offset_preview);self.assertEqual(a.doc.state(),before)
        a.apply_parameters();self.assertEqual(len(a.objects),2);self.assertEqual(a.objects[1]['a'],[0,-.5])
        self.assertEqual(a.objects[1]['color'],'#123456');self.assertEqual(len(a.doc.history),n+1)
        self.assertEqual(a.objects[0],before['objects'][0]);a.undo();self.assertEqual(a.doc.state(),before)
    def test_no_selection_choose_source_then_manual_point_and_cancel(self):
        a=self.a;a.doc.clear_selection();self.activate();self.click([1,0]);self.assertEqual(len(a.offset_sources),1)
        a.params['x'].set('1');a.params['y'].set('2');a.params['offset'].set('.3');a.preview_offset()
        self.assertTrue(a.offset_preview);self.assertEqual(len(a.objects),1)
        a.right_click();self.assertEqual(a.family.get(),'Select');self.assertFalse(a.offset_preview)
        self.assertEqual(len(a.objects),1)
    def test_invalid_distance_no_commit(self):
        a=self.a;self.activate();before=a.doc.state();n=len(a.doc.history)
        a.params['offset'].set('-1');a.apply_offset();self.assertTrue(self.errors);self.errors.clear()
        self.assertEqual(a.doc.state(),before);self.assertEqual(len(a.doc.history),n)
