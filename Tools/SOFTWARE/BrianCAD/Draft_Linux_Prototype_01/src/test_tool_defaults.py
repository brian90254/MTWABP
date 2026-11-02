"""Session-only defaults remember successful values and retain physical units."""
import copy
import os
import sys
import tkinter as tk
import unittest
from unittest.mock import patch
from draft import Draft
from cad_tools import DEFAULTS

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class ToolDefaultTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[];self.callbacks=[]
        self.a.error=self.errors.append;self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
    def tearDown(self):
        self.root.destroy();self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def tool(self,family,method=None):
        a=self.a;a.family.set(family);a.family_changed()
        if method:a.tool.set(method);a.method_changed()
    def test_circle_expression_units_and_new_drawing_keep_last_used(self):
        a=self.a;defaults=copy.deepcopy(DEFAULTS);self.tool('Circles');a.params['diameter'].set('12mm');a.apply_parameters()
        self.tool('Select');self.tool('Circles');self.assertAlmostEqual(a.values()['diameter'],12/25.4)
        a.change_units('mm');self.tool('Select');self.tool('Circles');self.assertAlmostEqual(float(a.params['diameter'].get()),12)
        a.doc.saved=a.doc.state();a.new();self.tool('Circles');self.assertAlmostEqual(a.values()['diameter'],12/25.4)
        self.assertEqual(DEFAULTS,defaults)
    def test_cancelled_and_invalid_values_do_not_replace_last_success(self):
        a=self.a;self.tool('Circles');a.params['diameter'].set('2');a.apply_parameters()
        a.params['diameter'].set('-3');a.apply_parameters();self.assertTrue(self.errors);self.errors.clear()
        self.tool('Select');self.tool('Circles');self.assertEqual(a.values()['diameter'],2)
        a.params['diameter'].set('10');self.tool('Select');self.tool('Circles');self.assertEqual(a.values()['diameter'],2)
    def test_polygon_count_shared_between_regular_polygon_methods(self):
        a=self.a;self.tool('Polygons','Inscribed polygon');a.params['sides'].set('4+4');a.apply_parameters()
        self.tool('Select');self.tool('Polygons','Circumscribed polygon');self.assertEqual(a.values()['sides'],8)
        self.assertEqual(a.params['x'].get(),'0');self.assertEqual(a.params['y'].get(),'0')
    def test_fillet_radius_saved_only_when_fillet_created(self):
        a=self.a;a.scale=100;a.origin=[250,350]
        a.doc.add([dict(type='line',a=[0,0],b=[3,0]),dict(type='line',a=[3,0],b=[3,3])]);self.tool('Chamfer')
        a.params['radius'].set('.4');a.chamfer_click([1,0]);a.chamfer_click([3,1])
        self.tool('Select');self.tool('Chamfer');self.assertAlmostEqual(a.values()['radius'],.4)
        a.params['radius'].set('1');a.chamfer_click([1,0]);self.tool('Select');self.tool('Chamfer')
        self.assertAlmostEqual(a.values()['radius'],.4)
    def test_line_relative_defaults_remain_consistent_and_undo_does_not_reset_memory(self):
        a=self.a;self.tool('Lines');a.pick([5,5]);a.pick([8,9]);a.undo()
        self.tool('Select');self.tool('Lines');self.assertEqual(a.field_point(0),[0,0]);self.assertEqual(a.field_point(1),[3,4])
        self.assertEqual(a.values()['length'],5);a.apply_parameters();self.assertEqual(a.objects[-1]['b'],[3,4])
    def test_offset_transform_and_mouse_circle_defaults(self):
        a=self.a;a.doc.add([dict(type='line',a=[0,0],b=[2,0])]);self.tool('Offset')
        a.params['offset'].set('.6');a.params['y'].set('2');a.apply_offset()
        self.tool('Select');self.tool('Offset');self.assertAlmostEqual(a.values()['offset'],.6)
        self.tool('Modify','Scale');a.params['factor'].set('2');a.apply_parameters()
        self.tool('Select');self.tool('Modify','Scale');self.assertEqual(a.values()['factor'],2)
        self.tool('Circles','Diameter endpoints');a.pick([0,0]);a.pick([3,0])
        self.tool('Select');self.tool('Circles');self.assertEqual(a.values()['diameter'],3)
