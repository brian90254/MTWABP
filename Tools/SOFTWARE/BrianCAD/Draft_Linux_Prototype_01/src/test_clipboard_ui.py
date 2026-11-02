"""Menu/shortcut copy-paste, native retained preview, placement and cancellation."""
import copy
import os
import sys
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from draft import Draft

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class ClipboardUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[];self.callbacks=[]
        self.a.error=self.errors.append;self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        a=self.a;a.scale=100;a.origin=[250,350]
        a.doc.add([dict(type='line',a=[0,0],b=[2,0]),dict(type='circle',center=[3,2],radius=1)])
        a.doc.group_selection();a.canvas.focus_force();self.root.update();a.mouse=[0,0];a.draw()
    def tearDown(self):
        self.root.destroy();self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def menu(self,label):self.a.menus['Edit'].invoke(label);self.root.update()
    def test_menu_move_and_pointer_preview_snap_place_undo(self):
        a=self.a;before=a.doc.state();n=len(a.doc.history);self.menu('Copy');self.menu('Paste')
        self.assertTrue(a._paste);self.assertEqual(a.doc.state(),before);self.assertEqual(len(a.doc.history),n)
        preview=a.canvas.find_withtag('paste-preview');self.assertEqual(len(preview),2)
        # Grid intersection snaps the clipboard anchor to (1,1); no curve recomputation.
        with patch('draft.geo.path',side_effect=AssertionError('moving preview must reuse canvas items')):
            x,y=a.screen([1.02,1.01]);a.motion(SimpleNamespace(x=x,y=y));self.root.update()
        self.assertEqual(a._paste['point'],[1,1]);self.assertEqual(a.canvas.find_withtag('paste-preview'),preview)
        self.assertEqual(a.canvas.coords(preview[0]),a.screen([1,1])+a.screen([3,1]))
        a.canvas.event_generate('<ButtonPress-1>',x=round(x),y=round(y),time=10000)
        a.canvas.event_generate('<ButtonRelease-1>',x=round(x),y=round(y),time=10010);self.root.update()
        self.assertIsNone(a._paste);self.assertFalse(a.canvas.find_withtag('paste-preview'))
        self.assertEqual(len(a.objects),4);self.assertEqual(a.objects[2]['a'],[1,1]);self.assertEqual(len(a.doc.history),n+1)
        self.assertNotEqual(a.objects[0]['group'],a.objects[2]['group']);a.undo();self.assertEqual(a.doc.state(),before)
        labels=[a.menus['Objects'].entrycget(i,'label') for i in range(a.menus['Objects'].index('end')+1) if a.menus['Objects'].type(i)!='separator']
        self.assertNotIn('Edit Objects...',labels)
    def test_shortcuts_cancel_and_repeat_paste_groups(self):
        a=self.a;a.canvas.event_generate('<Control-KeyPress-c>');self.root.update()
        before=a.doc.state();selection=set(a.selected);n=len(a.doc.history)
        a.canvas.event_generate('<Control-KeyPress-v>');self.root.update();self.assertTrue(a._paste)
        a.canvas.event_generate('<Escape>');self.root.update();self.assertIsNone(a._paste)
        self.assertEqual(a.doc.state(),before);self.assertEqual(a.selected,selection);self.assertEqual(len(a.doc.history),n)
        self.menu('Paste');a.right_click();self.assertIsNone(a._paste);self.assertEqual(a.doc.state(),before)
        self.menu('Paste');a.zoom(SimpleNamespace(x=400,y=250),1.2);self.assertTrue(a._paste)
        self.assertTrue(a.canvas.find_withtag('paste-preview'))
    def test_copy_across_new_drawing_and_text_entry_menu_clipboard(self):
        a=self.a;self.menu('Copy');a.doc.saved=a.doc.state();a.new();self.menu('Paste')
        a.snap.set(False);a.grid_snap.set(False);x,y=a.screen([5,5]);a.click(SimpleNamespace(x=x,y=y,state=0))
        self.assertEqual(len(a.objects),2);self.assertEqual(a.objects[0]['a'],[5,5])
        top=tk.Toplevel(self.root);entry=tk.Entry(top);entry.pack();entry.insert(0,'normal text');self.root.update()
        entry.focus_force();entry.selection_range(0,'end');self.root.update()
        self.menu('Copy');self.assertEqual(self.root.clipboard_get(),'normal text')
        entry.delete(0,'end');self.menu('Paste');self.assertEqual(entry.get(),'normal text');self.assertIsNone(a._paste)
        entry.selection_range(0,'end');entry.event_generate('<Control-KeyPress-c>');self.root.update()
        entry.delete(0,'end');entry.event_generate('<Control-KeyPress-v>');self.root.update()
        self.assertEqual(entry.get(),'normal text');self.assertIsNone(a._paste)
    def test_invalid_clipboard_no_changes(self):
        a=self.a;before=a.doc.state();self.root.clipboard_clear();self.root.clipboard_append('not geometry')
        self.menu('Paste');self.assertTrue(self.errors);self.errors.clear()
        self.assertEqual(a.doc.state(),before);self.assertFalse(getattr(a,'_paste',None))
