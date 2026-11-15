"""Session drawing pen width, validation, unit conversion and new-object styles."""
import copy
import os
import sys
import tkinter as tk
import unittest
from draft import Draft

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class PenSizeUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[];self.callbacks=[]
        self.a.error=self.errors.append;self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
    def tearDown(self):
        self.root.destroy();self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def choose(self,family,method=None):
        a=self.a;a.family.set(family);a.family_changed()
        if method:a.tool.set(method);a.method_changed()
        self.root.update()
    def test_entry_commit_new_shapes_preview_and_existing_objects(self):
        a=self.a;self.assertTrue(a.pen_size_entry.winfo_ismapped());self.assertEqual(a.pen_width(),.01)
        self.choose('Lines');a.pick([0,0]);a.pick([2,0]);old=copy.deepcopy(a.objects[0])
        a.pen_size.set('0.5mm');a.pen_size_entry.focus_force();self.root.update()
        a.pen_size_entry.event_generate('<Return>');self.root.update()
        self.assertAlmostEqual(a.pen_width(),.5/25.4)
        for family,method in [('Lines','Two points'),('Circles','Center + diameter'),('Polygons','Rectangle corners')]:
            self.choose(family,method);a.create_object([[0,0],[1,1]])
            self.assertAlmostEqual(a.objects[-1]['weight'],.5/25.4)
        self.assertEqual(a.objects[0],old)
        self.choose('Lines');a.pick([0,0]);a.mouse=[1,1]
        self.assertAlmostEqual(a.preview()['weight'],.5/25.4)
        a.pen_size.set('.03');a.canvas.focus_force();self.root.update()
        self.assertTrue(a.commit_pen_size());self.assertEqual(a.pen_width(),.03)
    def test_units_convert_the_same_physical_pen_size_and_new_session_drawings(self):
        a=self.a;a.pen_size.set('.02');self.assertTrue(a.commit_pen_size())
        a.change_units('mm');self.assertEqual(a.pen_size_label.get(),'Size (mm)')
        self.assertAlmostEqual(float(a.pen_size.get()),.508);self.assertAlmostEqual(a.pen_width(),.02)
        a.doc.undo();a.draw();self.assertEqual(a.pen_size_label.get(),'Size (in)')
        self.assertAlmostEqual(float(a.pen_size.get()),.02)
        a.doc.saved=a.doc.state();a.new();self.assertAlmostEqual(a.pen_width(),.02)
        a.pen_size.set('1/64');a.commit_pen_size();self.assertAlmostEqual(a.pen_width(),1/64)
    def test_invalid_width_blocks_new_geometry_without_history_changes(self):
        a=self.a;self.choose('Circles');before=a.doc.state();history=len(a.doc.history)
        for text in ('0','-1','2in','bad','1/0'):
            a.pen_size.set(text);self.assertFalse(a.commit_pen_size());self.assertTrue(a.pen_error.get())
            self.assertEqual(a.pen_size.get(),text)
            a.apply_parameters();self.assertTrue(self.errors);self.errors.clear()
            self.assertEqual(a.doc.state(),before);self.assertEqual(len(a.doc.history),history)
        a.pen_size.set('.01');self.assertTrue(a.commit_pen_size());self.assertEqual(a.pen_error.get(),'')
    def test_dimensions_use_pen_size_while_offset_retains_source_width(self):
        a=self.a;a.pen_size.set('.04');a.commit_pen_size();self.choose('Dimension')
        a.dimension_click([0,0]);a.dimension_click([2,0])
        self.assertEqual(a.objects[-1]['weight'],.04)
        self.choose('Lines');a.pen_size.set('.02');a.commit_pen_size();a.create_object([[0,0],[2,0]])
        a.pen_size.set('.06');a.commit_pen_size()
        a.doc.offset_objects([len(a.objects)-1],.2,[1,1])
        self.assertEqual(a.objects[-1]['weight'],.02)
