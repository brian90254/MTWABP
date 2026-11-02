"""Drawing units dialog, input normalization, grid invariance and shared inspector."""
import copy
import os
import sys
import tkinter as tk
import unittest
from unittest.mock import patch
from draft import Draft

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class UnitsUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[];self.callbacks=[]
        self.a.error=self.errors.append;self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.patch=patch('draft.messagebox.showerror',side_effect=lambda *a,**k:self.errors.append(a[1]));self.patch.start()
        self.a.doc.add([dict(type='line',a=[0,0],b=[2,0])]);self.a.draw()
    def tearDown(self):
        self.root.destroy();self.patch.stop();self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def button(self,parent,label):
        for w in parent.winfo_children():
            if w.winfo_class()=='TButton' and w.cget('text')==label:return w
            found=self.button(w,label)
            if found is not None:return found
    def test_units_dialog_grid_rendering_and_undo(self):
        a=self.a;before=copy.deepcopy(a.objects);grid=a.canvas.find_withtag('background');spacing=a.grid_spacing;scale=a.scale
        a.menus['Edit'].invoke('Units...');self.root.update();a.unit_choice.set('Millimeters (mm)')
        self.button(a.units_window,'Apply').invoke();self.root.update()
        self.assertEqual(a.doc.display_unit,'mm');self.assertEqual(a.objects,before);self.assertEqual(a.grid_spacing,spacing);self.assertEqual(a.scale,scale)
        self.assertEqual(a.canvas.find_withtag('background'),grid);self.assertIn('mm',a.parameter_frame.cget('text'))
        a.undo();self.assertEqual(a.doc.display_unit,'in');self.assertEqual(a.objects,before)
    def test_circle_diameter_suffix_math_normalization_and_metric_input(self):
        a=self.a;a.family.set('Circles');a.family_changed();a.params['diameter'].set('12mm');a.normalize_parameter('diameter')
        self.assertAlmostEqual(float(a.params['diameter'].get()),12/25.4)
        a.apply_parameters();self.assertAlmostEqual(a.objects[-1]['radius'],6/25.4)
        a.change_units('mm');a.params['diameter'].set('12"');a.apply_parameters()
        self.assertEqual(a.objects[-1]['radius'],6);self.assertAlmostEqual(float(a.params['diameter'].get()),304.8)
        a.params['diameter'].set('6+4');a.apply_parameters();self.assertAlmostEqual(a.objects[-1]['radius'],5/25.4)
        a.params['diameter'].set('5/8');a.normalize_parameter('diameter');self.assertEqual(a.params['diameter'].get(),'0.625')
    def test_pending_fields_and_editor_convert_without_committing(self):
        a=self.a;a.family.set('Lines');a.family_changed();a.params['x2'].set('2in+12mm');a.params['angle'].set('45+45')
        a.edit_dialog();a.edit_fields['bx'].set('2in+12mm');before=copy.deepcopy(a.objects)
        a.change_units('mm');self.assertAlmostEqual(float(a.params['x2'].get()),62.8);self.assertEqual(a.params['angle'].get(),'90')
        self.assertAlmostEqual(float(a.edit_fields['bx'].get()),62.8);self.assertAlmostEqual(float(a.edit_fields['weight'].get()),.254)
        self.assertEqual(a.objects,before);self.assertIn('mm',a.edit_length.get())
        a.edit_apply.invoke();self.assertAlmostEqual(a.objects[0]['b'][0],2+12/25.4)
        a.edit_fields['weight'].set('1/2mm');a.normalize_edit_field('weight');self.assertEqual(a.edit_fields['weight'].get(),'0.5')
    def test_grid_expressions_and_scalar_scale_factor(self):
        a=self.a;a.change_units('mm');a.grid_dialog();self.root.update();dlg=self.root.winfo_children()[-1]
        entries=[]
        def collect(w):
            if w.winfo_class()=='TEntry':entries.append(w)
            for child in w.winfo_children():collect(child)
        collect(dlg);entries[0].delete(0,'end');entries[0].insert(0,'1/2in');entries[1].delete(0,'end');entries[1].insert(0,'2*4')
        self.button(dlg,'OK').invoke();self.assertAlmostEqual(a.grid_spacing,.5);self.assertEqual(a.grid_subdivisions,8)
        a.family.set('Modify');a.family_changed();a.tool.set('Scale');a.method_changed();a.params['factor'].set('2*3')
        self.assertEqual(a.values()['factor'],6)
    def test_metric_mouse_picks_keep_physical_diameter_move_and_offset(self):
        a=self.a;a.change_units('mm');a.family.set('Circles');a.family_changed()
        a.pick([0,0]);a.pick([1,0]);self.assertAlmostEqual(a.objects[-1]['radius'],1)
        self.assertAlmostEqual(float(a.params['diameter'].get()),50.8)
        a.selected={0};a.family.set('Modify');a.family_changed();a.pick([0,0]);a.pick([1,2])
        self.assertAlmostEqual(a.objects[0]['a'][0],1);self.assertAlmostEqual(a.objects[0]['a'][1],2);self.assertAlmostEqual(float(a.params['dx'].get()),25.4)
        a.undo();a.family.set('Lines');a.family_changed();a.tool.set('Offset from line');a.method_changed()
        a.pick([1,0]);a.pick([1,1]);self.assertAlmostEqual(a.objects[-1]['a'][1],1)
    def test_invalid_expression_does_not_change_document_or_unit(self):
        a=self.a;a.family.set('Circles');a.family_changed();a.params['diameter'].set('1/0');before=a.doc.state()
        a.apply_parameters();self.assertTrue(self.errors);self.errors.clear();self.assertEqual(a.doc.state(),before)
        with self.assertRaises(ValueError):a.change_units('mm')
        self.assertEqual(a.doc.state(),before)
