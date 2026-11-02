"""Menu commands, persistent recent drawings and rectangle zoom workflows."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
from cad_recent import RecentFiles
from cad_document import Document
from draft import Draft


class RecentTests(unittest.TestCase):
    def test_persistence_order_deduplication_limit_clear_and_corruption(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'prefs'/'recent.json';r=RecentFiles(path)
            self.assertEqual(r.paths,[])
            for i in range(12):r.remember(Path(folder)/f'{i}.draft.json')
            self.assertEqual(len(r.paths),10);r.remember(Path(folder)/'5.draft.json')
            self.assertTrue(r.paths[0].endswith('5.draft.json'));self.assertEqual(len(r.paths),10)
            self.assertEqual(RecentFiles(path).paths,r.paths)
            r.clear();self.assertEqual(RecentFiles(path).paths,[])
            path.write_text('invalid');self.assertEqual(RecentFiles(path).paths,[])
    def test_write_failure_keeps_history_and_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'recent.json';r=RecentFiles(path);r.remember('/old.json');before=path.read_text()
            with patch('cad_recent.os.replace',side_effect=OSError('read-only')):r.remember('/new.json')
            self.assertEqual(path.read_text(),before);self.assertEqual(r.paths[0],'/new.json')
            self.assertEqual(list(Path(folder).iterdir()),[path])


@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class MenuUITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.pref_patch=patch('cad_recent.preferences_path',return_value=self.folder/'recent.json');self.pref_patch.start()
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[];self.callbacks=[]
        self.a.error=self.errors.append;self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.a.doc.add([dict(type='line',a=[0,0],b=[2,1])]);self.a.draw()
    def tearDown(self):
        self.root.destroy();self.pref_patch.stop();self.temp.cleanup()
        self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def labels(self,menu):
        return [menu.entrycget(i,'label') for i in range(menu.index('end')+1) if menu.type(i)!='separator']
    def invoke(self,menu,label):self.a.menus[menu].invoke(label);self.root.update()
    def test_exact_menu_structure_and_actions(self):
        a=self.a
        self.assertEqual(self.labels(a.menu_bar),['File','Edit','Objects','View'])
        self.assertEqual(self.labels(a.menus['File']),['New','Open...','Open Recent...','Save','Save As...','Import...','Export...'])
        self.assertEqual(self.labels(a.menus['Edit']),['Undo','Redo','Copy','Paste','Edit Objects...','Units...'])
        self.assertEqual(self.labels(a.menus['Objects']),['Group','Ungroup','Divide...','Layers...'])
        self.assertEqual(self.labels(a.menus['View']),['Fit','Zoom In','Zoom Out','Window'])
        before=a.doc.state();scale=a.scale;center=(a.canvas.winfo_width()/2,a.canvas.winfo_height()/2)
        world=a.world(*center);self.invoke('View','Zoom In');self.assertAlmostEqual(a.scale,scale*1.25)
        for p,q in zip(world,a.world(*center)):self.assertAlmostEqual(p,q)
        self.invoke('View','Zoom Out');self.assertAlmostEqual(a.scale,scale);self.assertEqual(a.doc.state(),before)
        self.invoke('Objects','Layers...');self.assertTrue(a.layer_window.winfo_exists())
        self.invoke('Edit','Edit Objects...');self.assertTrue(a.edit_window.winfo_exists())
        self.invoke('Edit','Undo');self.assertEqual(len(a.objects),0)
        self.invoke('Edit','Redo');self.assertEqual(len(a.objects),1)
    def test_import_export_menu_routes_and_new_save_as_shortcuts(self):
        a=self.a
        with patch('draft.filedialog.askopenfilename',return_value='') as chooser:self.invoke('File','Import...')
        self.assertTrue(chooser.called)
        self.invoke('File','Export...');self.assertTrue(a.export_window.winfo_exists());a.export_window.destroy()
        path=self.folder/'shortcut.draft.json';a.canvas.focus_force();self.root.update()
        with patch('draft.filedialog.asksaveasfilename',return_value=str(path)) as chooser:
            a.canvas.event_generate('<Control-Shift-KeyPress-S>');self.root.update()
        self.assertTrue(chooser.called);self.assertEqual(a.path,str(path))
        a.canvas.event_generate('<Control-KeyPress-n>');self.root.update();self.assertFalse(a.objects)
    def test_save_as_open_recent_and_discard_cancellation(self):
        a=self.a;path=self.folder/'example.draft.json'
        with patch('draft.filedialog.asksaveasfilename',return_value=str(path)) as chooser:self.invoke('File','Save As...')
        self.assertTrue(chooser.called);self.assertEqual(a.recent_files.paths,[str(path)])
        a.new();self.assertFalse(a.objects)
        a.refresh_recent_menu();a.recent_menu.invoke(0);self.root.update();self.assertEqual(len(a.objects),1)
        self.assertEqual(a.path,str(path));self.assertFalse(a.doc.dirty)
        a.doc.add([dict(type='circle',center=[0,0],radius=1)]);before=a.doc.state()
        with patch('draft.messagebox.askyesno',return_value=False):a.recent_menu.invoke(0)
        self.assertEqual(a.doc.state(),before)
        a.clear_recent();self.assertEqual(a.recent_menu.entrycget(0,'state'),'disabled')
    def test_open_failures_and_cancelled_save_do_not_enter_history(self):
        a=self.a;a.doc.saved=a.doc.state();before=a.doc.state()
        with patch('draft.filedialog.asksaveasfilename',return_value=''):self.invoke('File','Save As...')
        self.assertFalse(a.recent_files.paths)
        with patch('draft.filedialog.askopenfilename',return_value=str(self.folder/'missing.json')):self.invoke('File','Open...')
        self.assertTrue(self.errors);self.errors.clear();self.assertFalse(a.recent_files.paths)
        self.assertEqual(a.doc.state(),before)
    def drag_window(self,start,end):
        c=self.a.canvas
        c.event_generate('<ButtonPress-1>',x=start[0],y=start[1],time=10000)
        c.event_generate('<B1-Motion>',x=end[0],y=end[1],time=10100);self.root.update()
        self.assertTrue(c.find_withtag('zoom-window'))
        c.event_generate('<ButtonRelease-1>',x=end[0],y=end[1],time=10200);self.root.update()
    def test_window_zoom_both_directions_preserves_tool_selection_and_pending_geometry(self):
        a=self.a;a.family.set('Lines');a.family_changed();a.pick([0,0]);a.doc.selected={0};a.draw()
        before=a.doc.state();points=copy.deepcopy(a.points);history=len(a.doc.history)
        for start,end in [((150,150),(400,350)),((400,350),(150,150))]:
            old_world=[a.world(*start),a.world(*end)]
            self.invoke('View','Window');self.drag_window(start,end)
            self.assertFalse(a._zoom_window);self.assertEqual(a.family.get(),'Lines');self.assertEqual(a.points,points)
            self.assertEqual(a.doc.state(),before);self.assertEqual(len(a.doc.history),history);self.assertEqual(a.selected,{0})
            for world in old_world:
                x,y=a.screen(world);self.assertGreaterEqual(x,19.9);self.assertLessEqual(x,a.canvas.winfo_width()-19.9)
                self.assertGreaterEqual(y,19.9);self.assertLessEqual(y,a.canvas.winfo_height()-19.9)
    def test_window_cancel_with_pending_spline_and_tiny_drag(self):
        a=self.a;a.family.set('Splines');a.family_changed();a.pick([0,0]);a.pick([1,1])
        points=copy.deepcopy(a.points);view=(a.scale,list(a.origin));before=a.doc.state()
        self.invoke('View','Window');self.drag_window((100,100),(101,101));self.assertTrue(a._zoom_window)
        a.right_click();self.assertFalse(a._zoom_window);self.assertEqual(a.family.get(),'Splines');self.assertEqual(a.points,points)
        self.invoke('View','Window');a.canvas.focus_force();self.root.update();a.canvas.event_generate('<Escape>');self.root.update()
        self.assertFalse(a._zoom_window);self.assertEqual(a.points,points);self.assertEqual((a.scale,a.origin),view)
        self.assertEqual(a.doc.state(),before)
