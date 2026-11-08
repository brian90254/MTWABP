"""Layer lock persistence, selection/edit protections, and layer-panel gestures."""
import copy
import os
import sys
import tkinter as tk
from tkinter import ttk
import unittest
from types import SimpleNamespace
from cad_document import Document
from draft import Draft
import cad_import
import cad_clipboard

class LayerLockTests(unittest.TestCase):
    def make(self):
        d=Document();d.add([dict(type='line',a=[0,0],b=[2,0]),
            dict(type='circle',center=[4,0],radius=1,layer='Construction')])
        return d
    def test_lock_prunes_whole_and_partial_selection_without_hiding(self):
        d=self.make();d.selected={0};d.point_selection={1:{'radius'}}
        before=d.state();history=len(d.history)
        d.toggle_layer_lock('Construction')
        self.assertTrue(d.visible(1));self.assertEqual(d.selected,{0});self.assertFalse(d.point_selection)
        self.assertEqual(len(d.history),history+1)
        d.select_window([-10,-10],[10,10]);self.assertEqual(d.selected,{0})
        d.select_window([4.9,-.1],[5.1,.1]);self.assertFalse(d.point_selection)
        d.undo();self.assertEqual(d.state(),before)
        d.redo();self.assertTrue(d.layer_locked(1))
        loaded=Document.from_payload(d.payload());self.assertTrue(loaded.layer_locked(1))
        bad=d.payload();bad['layers'][1]['locked']='yes'
        with self.assertRaises(ValueError):Document.from_payload(bad)
    def test_bulk_lock_includes_active_and_preserves_visibility_and_object_locks(self):
        d=self.make();d.objects[0]['locked']=True;d.toggle_layer('Dimension')
        visible=[l['visible'] for l in d.layers];active=d.active
        d.toggle_all_layer_locks()
        self.assertTrue(all(l['locked'] for l in d.layers));self.assertFalse(d.selected)
        self.assertEqual([l['visible'] for l in d.layers],visible);self.assertEqual(d.active,active)
        d.toggle_all_layer_locks();self.assertFalse(any(l['locked'] for l in d.layers));self.assertTrue(d.objects[0]['locked'])
    def test_locked_members_block_group_and_geometry_edits(self):
        d=self.make();d.selected={0,1};d.group_selection();d.toggle_layer_lock('Construction')
        self.assertFalse(d.selected);self.assertFalse(d.selectable_ids())
        d.select_window([-10,-10],[10,10]);self.assertFalse(d.selected)
        before=d.state();n=len(d.history)
        for operation in (lambda:d.edit(1,d.objects[1]),lambda:d.commit_updates({1:d.objects[1]}),
                lambda:d.offset_objects([1],.2,[6,0]),lambda:d.divide_objects({1},2),
                lambda:d.trim_object(1,{0},[5,0]),lambda:d.chamfer_objects(0,1,[1,0],[5,0],.2)):
            with self.assertRaises(ValueError):operation()
            self.assertEqual(d.state(),before);self.assertEqual(len(d.history),n)
        d.toggle_layer_lock('Construction');d.select_window([-10,-10],[10,10]);self.assertEqual(d.selected,{0,1})
    def test_new_names_increment_suffix_skip_collisions_and_keep_padding(self):
        d=Document();self.assertEqual(d.next_layer_name(),'Layer2')
        d.add_layer('Layer2');self.assertEqual(d.next_layer_name(),'Layer3')
        d.add_layer('Ramp008');self.assertEqual(d.next_layer_name('Ramp007'),'Ramp009')
        self.assertEqual(d.next_layer_name('Construction'),'Construction1')
        self.assertLessEqual(len(d.next_layer_name('A'*255)),255)
    def test_new_paste_and_import_on_locked_layers_are_not_selected(self):
        d=self.make();clip=cad_clipboard.snapshot(d,{0});source=Document.from_payload(d.payload())
        d.toggle_layer_lock('Layer1');d.add([dict(type='line',a=[0,1],b=[2,1])])
        self.assertFalse(d.selected);self.assertTrue(d.visible(2))
        cad_clipboard.place(d,clip,[0,3]);self.assertFalse(d.selected)
        cad_import.merge(d,source);self.assertNotIn(4,d.selected)
        self.assertTrue(d.layer_locked(4))

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class LayerLockUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[];self.callbacks=[]
        self.a.error=self.errors.append;self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.a.doc.add([dict(type='line',a=[0,0],b=[2,0])])
        self.a.layers_dialog();self.root.update();self.tree=self.a.layer_tree;self.clock=10000
    def tearDown(self):
        self.root.destroy();self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def double(self,x,y):
        self.clock+=2000
        for offset in (0,120):
            self.tree.event_generate('<ButtonPress-1>',x=x,y=y,time=self.clock+offset)
            self.tree.event_generate('<ButtonRelease-1>',x=x,y=y,time=self.clock+offset+20)
        self.root.update()
    def row(self,name):
        return next(row for row in self.tree.get_children() if self.tree.item(row,'values')[-1]==name)
    def cell(self,name,column):
        row=self.row(name);self.tree.see(row);self.root.update()
        x,y,w,h=self.tree.bbox(row,column);self.double(x+w//2,y+h//2)
    def header(self,column):
        names=['#0','active','locked','name'];i=names.index(column)
        x=sum(self.tree.column(col,'width') for col in names[:i])+self.tree.column(column,'width')//2
        self.double(x,10)
    def button(self,name):
        def find(parent):
            for child in parent.winfo_children():
                if isinstance(child,ttk.Button) and child.cget('text')==name:return child
                result=find(child)
                if result:return result
        find(self.a.layer_window).invoke();self.root.update()
    def test_row_and_header_locks_leave_geometry_and_snaps_available(self):
        a=self.a;a.grid_snap.set(False);a.edit_dialog();self.root.update()
        self.assertEqual(a.edit_selection(),[0])
        self.cell('Layer1','locked')
        self.assertTrue(a.doc.layer_locked(0));self.assertFalse(a.selected);self.assertFalse(a.edit_selection())
        self.assertTrue(a.doc.visible(0));self.assertIsNone(a.hit([1,0]))
        self.assertEqual(a.snap_point([2,0]),([2,0],'endpoint'));self.assertEqual(a.snap_point([.37,0])[1],'on line')
        self.assertTrue(a.canvas.find_withtag('entity:0'))
        e=SimpleNamespace(x=a.screen([1,0])[0],y=a.screen([1,0])[1],state=0)
        a.click(e);a.release_select(e);self.assertFalse(a.selected)
        self.cell('Layer1','locked');self.assertIsNotNone(a.hit([1,0]))
        before=[l['visible'] for l in a.doc.layers]
        self.header('locked');self.assertTrue(all(l['locked'] for l in a.doc.layers))
        self.header('locked');self.assertFalse(any(l['locked'] for l in a.doc.layers))
        self.assertEqual([l['visible'] for l in a.doc.layers],before)
    def test_enter_renames_active_and_new_without_editing_increments(self):
        a=self.a
        self.tree.selection_set(self.row('Construction'));self.root.update()
        a.layer_name.set('Main');a.layer_name_entry.focus_force();self.root.update()
        a.layer_name_entry.event_generate('<Return>');self.root.update()
        self.assertEqual(a.doc.active,'Main');self.assertEqual(a.objects[0]['layer'],'Main')
        self.assertTrue(any(l['name']=='Construction' for l in a.doc.layers))
        self.tree.selection_set(self.row('Main'));self.root.update();self.button('New')
        self.assertEqual(a.layer_name.get(),'Main1');self.assertEqual(a.doc.active,'Main')
        self.button('New');self.assertEqual(a.layer_name.get(),'Main2')
        a.layer_name.set('Ramp007');self.button('New');self.assertEqual(a.layer_name.get(),'Ramp007')
        a.doc.add_layer('Ramp008');self.button('New');self.assertEqual(a.layer_name.get(),'Ramp009')
        self.header('name');self.cell('Main','locked');self.assertTrue(a.doc.layer_locked(0))
