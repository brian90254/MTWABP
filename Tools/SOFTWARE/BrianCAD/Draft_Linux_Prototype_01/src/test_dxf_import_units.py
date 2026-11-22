"""Explicit DXF source units and workspace-defaulted import choices."""
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
try:import ezdxf
except ImportError:ezdxf=None
import cad_import
from draft import Draft

@unittest.skipUnless(ezdxf,'Install requirements-dxf.txt')
class SourceUnitsTests(unittest.TestCase):
    def test_override_units_missing_header_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'units.dxf'
            for code in (0,1,4):
                d=ezdxf.new();d.units=code;d.modelspace().add_line((0,0),(25.4,0));d.saveas(path)
                for unit,length in [('mm',1),('in',25.4)]:
                    src,warnings=cad_import.read_drawing(path,dxf_unit=unit)
                    self.assertAlmostEqual(src.objects[0]['b'][0],length);self.assertEqual(warnings,[])
                src,_=cad_import.read_dxf(path)
                self.assertAlmostEqual(src.objects[0]['b'][0],1 if code==4 else 25.4)

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class ImportUnitUITests(unittest.TestCase):
    def setUp(self):self.root=tk.Tk();self.a=Draft(self.root);self.root.update()
    def tearDown(self):self.root.destroy()
    def choose(self,value=None,cancel=False):
        def respond():
            self.assertEqual(self.a.import_unit.get(),'mm' if self.a.doc.display_unit in ('mm','cm','m') else 'in')
            if cancel:self.a.import_units_window.destroy();return
            if value:self.a.import_unit.set(value)
            def accept(parent):
                for child in parent.winfo_children():
                    if child.winfo_class()=='TButton' and child.cget('text')=='Import':child.invoke();return True
                    if accept(child):return True
                return False
            accept(self.a.import_units_window)
        self.root.after(30,respond)
    def test_defaults_and_cancel(self):
        for unit in ('in','mm','cm','ft'):
            self.a.doc.set_display_unit(unit);self.choose();self.assertEqual(self.a.choose_dxf_import_units(),'mm' if unit in ('mm','cm') else 'in')
        self.choose(cancel=True);self.assertIsNone(self.a.choose_dxf_import_units())
    @unittest.skipUnless(ezdxf,'Install requirements-dxf.txt')
    def test_chosen_units_import_and_cancel_without_changes(self):
        a=self.a;a.doc.set_display_unit('in')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'sample.DXF';d=ezdxf.new();d.units=1;d.modelspace().add_line((0,0),(25.4,0));d.saveas(path)
            with patch('draft.filedialog.askopenfilename',return_value=str(path)),patch('draft.messagebox.showinfo'):
                before=a.doc.state();self.choose(cancel=True);a.import_drawing();self.assertEqual(a.doc.state(),before)
                self.choose('mm');a.import_drawing();self.assertAlmostEqual(a.objects[-1]['b'][0],1)
                self.assertEqual(a.doc.display_unit,'in');a.doc.undo();self.assertEqual(a.doc.state(),before)
