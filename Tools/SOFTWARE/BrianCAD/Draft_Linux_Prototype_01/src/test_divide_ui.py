"""Objects > Divide dialog, independent application and cancellation/error handling."""
import copy
import os
import sys
import tkinter as tk
import unittest
from unittest.mock import patch
from draft import Draft

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class DivideUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[];self.callbacks=[]
        self.a.error=self.errors.append;self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.error_patch=patch('draft.messagebox.showerror',side_effect=lambda *a,**k:self.errors.append(a[1]));self.error_patch.start()
        self.a.doc.add([dict(type='line',a=[0,0],b=[6,0]),dict(type='circle',center=[0,0],radius=1)])
        self.a.draw()
    def tearDown(self):
        self.root.destroy();self.error_patch.stop()
        self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def button(self,text):
        def find(parent):
            for child in parent.winfo_children():
                if child.winfo_class()=='TButton' and child.cget('text')==text:return child
                result=find(child)
                if result is not None:return result
        return find(self.a.divide_window)
    def open(self):self.a.menus['Objects'].invoke('Divide...');self.root.update()
    def test_apply_count_to_each_object_and_undo(self):
        a=self.a;before=a.doc.state();n=len(a.doc.history);self.open()
        self.assertIs(self.root.grab_current(),a.divide_window)
        a.divide_count.set('3');self.button('Apply').invoke();self.root.update()
        self.assertFalse(a.divide_window.winfo_exists());self.assertIsNone(self.root.grab_current())
        self.assertEqual(len(a.objects),6);self.assertEqual([o['type'] for o in a.objects],['line']*3+['arc']*3)
        self.assertEqual(len(a.doc.history),n+1);self.assertEqual(a.selected,set(range(6)))
        a.undo();self.assertEqual(a.doc.state(),before)
    def test_bad_count_keeps_dialog_and_selection_then_cancel(self):
        a=self.a;before=a.doc.state();selection=set(a.selected);n=len(a.doc.history);self.open()
        a.divide_count.set('2.5');self.button('Apply').invoke();self.root.update()
        self.assertTrue(self.errors);self.errors.clear();self.assertTrue(a.divide_window.winfo_exists())
        self.assertEqual(a.doc.state(),before);self.assertEqual(a.selected,selection);self.assertEqual(len(a.doc.history),n)
        self.button('Cancel').invoke();self.assertIsNone(self.root.grab_current());self.assertEqual(a.doc.state(),before)
    def test_escape_preserves_unfinished_tool_and_empty_selection_feedback(self):
        a=self.a;a.family.set('Lines');a.family_changed();a.pick([1,2]);points=copy.deepcopy(a.points)
        self.open();a.divide_window.focus_force();self.root.update();a.divide_window.event_generate('<Escape>');self.root.update()
        self.assertEqual(a.points,points);self.assertEqual(len(a.objects),2)
        a.doc.clear_selection();a.divide_dialog();self.assertTrue(self.errors);self.errors.clear()
    def test_multispan_sections_select_independently(self):
        a=self.a;a.doc.add([dict(type='spline',method='through',points=[[0,0],[1,3],[4,1],[5,2],[6,0]],closed=False)])
        self.open();a.divide_count.set('2');self.button('Apply').invoke()
        parts=a.objects[2:];groups={o.get('group') for o in parts};self.assertEqual(len(groups),2);self.assertNotIn(None,groups)
        first=a.doc.group_members({2});other=set(range(2,len(a.objects)))-first
        self.assertTrue(other);self.assertTrue(first.isdisjoint(other))
