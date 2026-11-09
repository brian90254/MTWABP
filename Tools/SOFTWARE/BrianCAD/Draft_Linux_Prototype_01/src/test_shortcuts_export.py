"""Tool key/hover behavior and physical DXF conversion in every display unit."""
import copy
import math
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch
try:import ezdxf
except ImportError:ezdxf=None
from cad_tools import METHODS,TOOL_KEYS
from cad_units import UNITS
from cad_document import Document
from cad_dxf import build_dxf,snapshot_drawing
import cad_dimensions as dimensions
from draft import Draft

@unittest.skipUnless(ezdxf,'Optional ezdxf is required')
class ExportUnitsTests(unittest.TestCase):
    def test_units_coordinates_curves_patterns_widths_and_round_trip(self):
        from cad_import import read_dxf
        d=Document();d.add([
            dict(type='line',a=[1,2],b=[3,4],pattern='Dashed',weight=.01),
            dict(type='circle',center=[3,2],radius=.5),
            dict(type='arc',center=[0,0],radius=2,start=.2,sweep=-1.4),
            dict(type='ellipse',center=[2,1],rx=2,ry=1,angle=.3),
            dict(type='spline',method='bezier',points=[[0,0],[1,2],[3,0]],closed=False)])
        for unit,code in [('in',1),('ft',2),('mm',4),('cm',5),('m',6)]:
            d.display_unit=unit;before=d.state();factor=1/UNITS[unit][1]
            drawing,report=build_dxf(snapshot_drawing(d));entities=list(drawing.modelspace())
            self.assertEqual(drawing.units,code);self.assertEqual(report['unit'],unit)
            self.assertAlmostEqual(entities[0].dxf.start.x,factor);self.assertAlmostEqual(entities[0].dxf.end.y,4*factor)
            self.assertAlmostEqual(entities[1].dxf.radius,.5*factor)
            self.assertAlmostEqual(entities[2].dxf.radius,2*factor)
            self.assertAlmostEqual(entities[2].dxf.start_angle,math.degrees(-1.2)%360)
            self.assertAlmostEqual(entities[3].dxf.major_axis.magnitude,2*factor)
            self.assertAlmostEqual(entities[4].control_points[1][1],2*factor)
            self.assertEqual(entities[0].dxf.lineweight,25)
            pattern=drawing.linetypes.get('BRIANCAD_DASHED').pattern_tags.compile()
            self.assertAlmostEqual(pattern[0],.25*factor)
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'units.dxf';drawing.saveas(path);imported,warnings=read_dxf(path)
                self.assertFalse(warnings);self.assertEqual(len(imported.objects),5)
                for actual,expected in zip(imported.objects[0]['b'],[3,4]):self.assertAlmostEqual(actual,expected)
                self.assertAlmostEqual(imported.objects[1]['radius'],.5)
                self.assertFalse(ezdxf.readfile(path).audit().has_errors)
            self.assertEqual(d.state(),before)
    def test_dimension_labels_and_sizes_scale_once(self):
        d=Document();d.add_dimensions(dimensions.between([0,0],[2,0]));d.display_unit='mm'
        drawing,_=build_dxf(snapshot_drawing(d));text=list(drawing.modelspace().query('TEXT'))[0]
        self.assertEqual(text.dxf.text,'50.8 mm')
        self.assertAlmostEqual(text.dxf.height,.14*25.4)
        self.assertAlmostEqual(text.dxf.align_point.x,25.4)
    def test_partial_only_export_is_empty_but_whole_drawing_works(self):
        d=Document();d.add([dict(type='line',a=[0,0],b=[1,0])]);d.clear_selection();d.point_selection={0:{'b'}}
        snap=snapshot_drawing(d);self.assertFalse(snap['selected'])
        with self.assertRaises(ValueError):build_dxf(snap,True)
        self.assertEqual(build_dxf(snap)[1]['objects'],1)

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class ShortcutUITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.pref=patch('cad_workspace.preferences_path',return_value=Path(self.temp.name)/'recent.json');self.pref.start()
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[];self.callbacks=[]
        self.a.error=self.errors.append;self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.root.focus_force();self.a.canvas.focus_set();self.root.update()
    def tearDown(self):
        self.root.destroy();self.pref.stop();self.temp.cleanup()
        self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def press(self,key,state=0):
        self.root.focus_get().event_generate('<KeyPress>',keysym=key,state=state);self.root.update()
    def test_every_tool_key_and_method_memory(self):
        a=self.a;self.assertEqual(set(TOOL_KEYS.values()),set(METHODS))
        for key,family in TOOL_KEYS.items():
            self.press(key);self.assertEqual(a.family.get(),family)
        self.press('a');a.tool.set('Three-point arc');a.method_changed()
        self.press('v');self.press('A');self.assertEqual(a.tool.get(),'Three-point arc')
    def test_typing_modifier_keys_modal_and_float_panel_focus(self):
        a=self.a;self.press('l');entry=a.parameter_entries['x']
        entry.focus_force();self.root.update();self.press('c')
        self.assertEqual(a.family.get(),'Lines');self.assertIn('c',a.params['x'].get())
        a.params['x'].set('0');a.canvas.focus_force();self.root.update()
        self.assertIsNone(a.tool_shortcut(SimpleNamespace(widget=a.canvas,state=4,keysym='a')))
        self.assertEqual(a.family.get(),'Lines')
        dlg=tk.Toplevel(self.root);dlg.grab_set()
        a.tool_shortcut(SimpleNamespace(widget=a.canvas,state=0,keysym='c'))
        self.assertEqual(a.family.get(),'Lines');dlg.destroy()
        a.layers_dialog();a.toggle_panel('layers');self.root.update()
        a.layer_tree.focus_force();self.root.update();self.press('c');self.assertEqual(a.family.get(),'Circles')
    def test_hover_delay_and_cancel(self):
        a=self.a;hint=a.tool_hints['Lines']
        hint.schedule();self.assertIsNone(hint.popup);self.assertIsNotNone(hint.job)
        self.assertEqual(hint.delay,1000)
        self.root.after(1050,self.root.quit);self.root.mainloop()
        self.assertIsNotNone(hint.popup)
        label=hint.popup.winfo_children()[0];self.assertIn('L',label.cget('text'))
        hint.hide();self.assertIsNone(hint.popup)
        hint.schedule();hint.widget.event_generate('<Leave>');self.root.update()
        self.assertIsNone(hint.job);self.assertIsNone(hint.popup)
    def test_export_dialog_partial_selection_and_frozen_units(self):
        a=self.a;a.doc.add([dict(type='line',a=[0,0],b=[2,0])]);a.doc.clear_selection()
        a.doc.point_selection={0:{'b'}};a.doc.set_display_unit('mm')
        a.export_dxf_dialog();self.root.update()
        def widgets(parent):
            for child in parent.winfo_children():
                yield child;yield from widgets(child)
        radios=[w for w in widgets(a.export_window) if w.winfo_class()=='TRadiobutton']
        self.assertTrue(next(w for w in radios if w.cget('text').startswith('Selected')).instate(['disabled']))
        texts=[w.cget('text') for w in widgets(a.export_window) if w.winfo_class()=='TLabel']
        self.assertTrue(any('Millimeters (mm)' in t for t in texts));self.assertTrue(any('excluded' in t for t in texts))
        cancel=next(w for w in widgets(a.export_window) if w.winfo_class()=='TButton' and w.cget('text')=='Cancel')
        cancel.invoke()
