"""Tk workflow checks; skip on headless hosts unless a display is supplied."""
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from draft import Draft
from cad_tools import METHODS
from cad_geometry import length


@unittest.skipUnless(os.environ.get('DISPLAY') or __import__('sys').platform=='darwin', 'A graphical display is required')
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk(); self.app=Draft(self.root)
        self.errors=[]; self.callbacks=[]
        self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.app.error=self.errors.append
        self.dialog_errors=patch('draft.messagebox.showerror',side_effect=lambda *a,**k:self.errors.append(a[1]))
        self.dialog_errors.start(); self.root.update()

    def tearDown(self):
        self.root.destroy(); self.dialog_errors.stop()
        self.assertFalse(self.callbacks,repr(self.callbacks))

    def choose(self,family,method=None):
        self.app.family.set(family); self.app.family_changed()
        if method:
            self.app.tool.set(method); self.app.method_changed()
        self.root.update()

    def button(self,widget,text):
        for child in widget.winfo_children():
            if child.winfo_class()=='TButton' and child.cget('text')==text: return child
            found=self.button(child,text)
            if found: return found
        return None

    def test_all_tool_controls_and_tab_order(self):
        for family,methods in METHODS.items():
            for method in methods:
                self.choose(family,method)
                self.assertEqual(self.app.tool.get(),method)
                self.assertTrue(self.app.status.get())
        self.choose('Lines')
        entries=[]
        for frame in self.app.parameter_frame.winfo_children():
            entries.extend(w for w in frame.winfo_children() if w.winfo_class()=='TEntry')
        self.assertEqual(len(entries),8)
        for a,b in zip(entries,entries[1:]):
            self.assertEqual(str(a.tk_focusNext()),str(b))
        self.assertLess(self.app.parameter_frame.winfo_reqwidth(),self.root.winfo_width())

    def test_click_and_manual_bottom_parameters(self):
        self.choose('Lines'); a=self.app
        a.pick([2,3]); self.assertEqual(a.params['x'].get(),'2'); self.assertEqual(a.params['y'].get(),'3')
        a.params['x'].set('4')  # amend the clicked start before choosing endpoint
        a.pick([6,3]); self.assertEqual(a.objects[0]['a'],[4,3]); self.assertEqual(a.objects[0]['b'],[6,3])
        a.params['x'].set('0'); a.params['y'].set('0'); a.params['length'].set('2'); a.params['angle'].set('90')
        a.last_parameter='angle'; a.apply_parameters(); self.assertAlmostEqual(a.objects[-1]['b'][1],2)
        self.choose('Circles'); a.params['x'].set('0'); a.params['y'].set('0'); a.params['diameter'].set('1')
        a.apply_parameters(); self.assertEqual(a.objects[-1]['radius'],.5)
        self.assertFalse(self.errors)

    def test_continuous_offset_and_tangent(self):
        a=self.app; self.choose('Lines','Connected points')
        for p in [[0,0],[2,0],[2,2]]: a.pick(p)
        self.assertEqual(len(a.objects),2); self.assertEqual(a.points,[[2,2]])
        a.finish(); self.assertEqual(a.points,[])
        self.choose('Lines','Offset from line'); a.pick([1,0]); a.pick([1,.25])
        self.assertAlmostEqual(a.objects[-1]['a'][1],.25)
        self.choose('Arcs','Start tangent + end'); a.pick([1,0]); a.pick([2,1])
        self.assertEqual(a.objects[-1]['type'],'arc')
        self.assertFalse(self.errors)

    def test_spline_workflow_and_group_transforms(self):
        a=self.app; self.choose('Splines')
        for p in [[0,0],[1,2],[2,0]]: a.pick(p)
        self.assertEqual(len(a.objects),0); a.finish(); self.assertEqual(a.objects[0]['type'],'spline')
        self.choose('Polygons'); a.pick([3,0]); a.pick([4,1])
        a.selected={0,1}; self.choose('Modify','Move')
        a.params['dx'].set('2'); a.params['dy'].set('3'); a.apply_parameters()
        self.assertEqual(a.objects[0]['points'][0],[2,3]); self.assertEqual(a.objects[1]['points'][0],[5,3])
        a.undo(); self.assertEqual(a.objects[0]['points'][0],[0,0])
        self.assertFalse(self.errors)

    def test_mouse_transform_and_selection(self):
        a=self.app; self.choose('Lines'); a.pick([0,0]); a.pick([2,0])
        self.choose('Modify','Rotate')
        for p in [[0,0],[1,0],[0,1]]: a.pick(p)
        self.assertAlmostEqual(a.objects[0]['b'][1],2)
        self.choose('Select'); a.fit(); self.root.update()
        px,py=a.screen([0,1])
        a.click(SimpleNamespace(x=px,y=py,state=0)); self.assertEqual(a.selected,{0})
        a.click(SimpleNamespace(x=px,y=py,state=1)); self.assertFalse(a.selected)
        self.assertFalse(self.errors)

    def test_layer_highlight_double_click_visibility(self):
        a=self.app; a.doc.add_layer('Ramps'); a.layers_dialog(); self.root.update()
        tree=a.layer_tree; row=next(k for k in tree.get_children() if tree.item(k,'values')[-1]=='Ramps')
        tree.selection_set(row); self.root.update(); self.assertEqual(a.doc.active,'Layer1')
        self.button(a.layer_window,'Set Layer').invoke(); self.assertEqual(a.doc.active,'Ramps')
        self.choose('Lines'); a.pick([0,0]); a.pick([2,0])
        self.assertEqual(a.objects[-1]['layer'],'Ramps')
        self.button(a.layer_window,'Show / Hide').invoke(); self.assertFalse(a.doc.visible(0))
        self.assertIsNone(a.hit([1,0]))
        a.grid_snap.set(False)
        self.assertNotEqual(a.snap_point([2,0])[1],'endpoint')
        a.undo(); self.assertTrue(a.doc.visible(0))
        self.assertFalse(self.errors)

    def test_layer_actual_double_click_bindings(self):
        a=self.app; a.layers_dialog(); self.root.update(); tree=a.layer_tree
        row=next(k for k in tree.get_children() if tree.item(k,'values')[-1]=='Dimension')
        def click_column(column,time):
            x,y,w,h=tree.bbox(row,column)
            tree.event_generate('<ButtonPress-1>',x=x+w//2,y=y+h//2,time=time)
            tree.event_generate('<ButtonRelease-1>',x=x+w//2,y=y+h//2,time=time+10)
            self.root.update()
        click_column('name',10000)
        self.assertEqual(a.doc.active,'Layer1')
        click_column('name',10100)
        self.assertEqual(a.doc.active,'Dimension')
        click_column('#0',20000); click_column('#0',20100)
        self.assertFalse(next(l for l in a.doc.layers if l['name']=='Dimension')['visible'])
        self.assertFalse(self.errors)

    def test_object_editor_length_and_apply(self):
        a=self.app; self.choose('Lines'); a.pick([0,0]); a.pick([1,0]); a.edit_dialog(); self.root.update()
        a.edit_fields['bx'].set('3'); a.edit_fields['by'].set('4'); self.root.update()
        self.assertIn('5 in',a.edit_length.get())
        self.button(a.edit_window,'Apply').invoke(); self.assertEqual(length(a.objects[0]),5)
        self.button(a.edit_window,'Close').invoke(); a.undo(); self.assertEqual(length(a.objects[0]),1)
        self.assertFalse(self.errors)

    def test_every_object_editor(self):
        import cad_geometry as g
        shapes=[{'type':'circle','center':[0,0],'radius':1},g.arc_three([1,0],[0,1],[-1,0]),
                g.ellipse_box([0,0],[2,1]),g.regular_polygon([0,0],[1,0],6),
                {'type':'spline','points':[[0,0],[1,1],[2,0]],'method':'through','closed':False}]
        for shape in shapes:
            self.app.doc.add([shape]); self.app.edit_dialog(); self.root.update()
            self.assertNotIn('check entered',self.app.edit_length.get())
            self.button(self.app.edit_window,'Apply').invoke()
            self.button(self.app.edit_window,'Close').invoke()
        self.assertFalse(self.errors)

    def test_grid_dialog_and_file_round_trip(self):
        a=self.app; a.grid_dialog(); self.root.update()
        dlg=[w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel)][0]
        entries=[w for f in dlg.winfo_children() for w in f.winfo_children() if w.winfo_class()=='TEntry']
        entries[0].delete(0,'end'); entries[0].insert(0,'1/2')
        entries[1].delete(0,'end'); entries[1].insert(0,'8')
        self.button(dlg,'OK').invoke(); self.assertEqual(a.grid_spacing,.5); self.assertEqual(a.grid_subdivisions,8)
        self.choose('Ovals','Center + axis + width')
        for p in [[0,0],[1,1],[-1,1]]: a.pick(p)
        with tempfile.TemporaryDirectory() as tmp:
            filename=str(Path(tmp)/'drawing.json'); a.path=filename; a.save()
            self.assertFalse(a.doc.dirty)
            with patch('draft.filedialog.askopenfilename',return_value=filename): a.open()
            self.assertEqual(a.objects[0]['type'],'ellipse'); self.assertEqual(a.grid_spacing,.5)
        self.assertFalse(self.errors)


if __name__=='__main__': unittest.main()
