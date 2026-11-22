"""Origin-based DXF placement and Library panel interaction."""
import copy
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import cad_geometry as geo
import cad_import
from cad_document import Document
from cad_library import placed,LIBRARY_DIR
from draft import Draft


def source():
    doc=Document();doc.add([dict(type='line',a=[1,0],b=[2,0],color='#123456',weight=.02)])
    return doc


class LibraryTests(unittest.TestCase):
    def test_rotation_about_original_origin_styles_layers_and_atomic_merge(self):
        src=source();before=copy.deepcopy(src.payload());dst=Document()
        transformed=placed(src,[10,20],90)
        self.assertAlmostEqual(transformed.objects[0]['a'][0],10)
        self.assertAlmostEqual(transformed.objects[0]['a'][1],21)
        self.assertAlmostEqual(transformed.objects[0]['b'][1],22)
        cad_import.merge(dst,transformed)
        self.assertEqual(dst.objects[0]['color'],'#123456');self.assertEqual(dst.objects[0]['weight'],.02)
        self.assertEqual(src.payload(),before)
        dst.undo();self.assertEqual(dst.objects,[])

    def test_project_example_loads_and_places_twice(self):
        try:import ezdxf
        except ImportError:self.skipTest('ezdxf is optional')
        src,warnings=cad_import.read_dxf(LIBRARY_DIR/'Lenses'/'Arrow_SM.dxf')
        self.assertTrue(src.objects);self.assertEqual(warnings,[])
        dst=Document();cad_import.merge(dst,placed(src,[1,2],45));cad_import.merge(dst,placed(src,[3,4],-90))
        self.assertEqual(len(dst.objects),2*len(src.objects))
        self.assertTrue({o['layer'] for o in src.objects}<={l['name'] for l in dst.layers})
        self.assertEqual(len(dst.selected),len(src.objects));dst.undo();self.assertEqual(len(dst.objects),len(src.objects))


@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class LibraryUITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.config=patch.dict(os.environ,{'XDG_CONFIG_HOME':self.temp.name});self.config.start()
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[]
        self.root.report_callback_exception=lambda *args:self.errors.append(args)
    def tearDown(self):
        self.root.destroy();self.config.stop();self.temp.cleanup();self.assertFalse(self.errors,repr(self.errors))
    def test_click_focus_angle_repeat_enter_and_cancel(self):
        a=self.a;a.begin_library(source(),'Example');self.root.update()
        a.snap.set(False);a.grid_snap.set(False)
        x,y=a.screen([3,4]);a.click(SimpleNamespace(x=x,y=y,state=0));self.root.update()
        self.assertIs(self.root.focus_get(),a.library_entries['angle'])
        self.assertEqual(a.library_entries['angle'].selection_get(),'0')
        a.library_fields['angle'].set('90');a.library_entries['angle'].event_generate('<Return>');self.root.update()
        self.assertEqual(len(a.objects),1);self.assertAlmostEqual(a.objects[0]['a'][0],3);self.assertAlmostEqual(a.objects[0]['a'][1],5)
        self.assertFalse(a._library['fixed'])
        a.library_click([7,8]);a.library_fields['angle'].set('0');a.commit_library()
        self.assertEqual(len(a.objects),2);self.assertEqual(a.objects[1]['a'],[8,8])
        a.right_click();self.assertIsNone(a._library);self.assertEqual(a.family.get(),'Select')
        self.assertFalse(a.canvas.find_withtag('library-preview'))
    def test_typed_units_validation_stationary_preview_and_escape(self):
        a=self.a;a.begin_library(source(),'Example')
        a.library_fields['x'].set('25.4mm');a.library_fields['y'].set('2+3');a.library_fields['angle'].set('1/0')
        a.commit_library();self.assertFalse(a.objects);self.assertTrue(a.library_error.get())
        a.library_fields['angle'].set('45');a.commit_library();self.assertEqual(len(a.objects),1)
        a.library_click([2,3]);a.library_motion([8,9]);self.assertEqual(a._library['point'],[2,3])
        a.change_units('mm');self.assertAlmostEqual(float(a.library_fields['x'].get()),50.8)
        a.escape();self.assertIsNone(a._library);self.assertEqual(len(a.objects),1)
    def test_panel_dock_float_and_refresh(self):
        a=self.a
        with patch('cad_library.LIBRARY_DIR',Path(self.temp.name)):
            a.library_dialog();self.root.update();self.assertIn('library',a.panels.panels)
            a.toggle_panel('library');self.root.update();self.assertIsNotNone(a.panels.panels['library']['top'])
            a.toggle_panel('library');self.root.update();self.assertIsNone(a.panels.panels['library']['top'])
            a.close_library();self.assertNotIn('library',a.panels.panels)
    def test_double_click_places_at_snapped_spot_with_current_angle(self):
        a=self.a;a.begin_library(source(),'Example');a.snap.set(False)
        # Grid snapping stays enabled and rounds a nearby mouse location.
        x,y=a.screen([1.02,2.02]);event=SimpleNamespace(x=x,y=y,state=0)
        a.click(event);a.library_fields['angle'].set('90')
        self.assertEqual(a.double_click(event),'break');self.assertEqual(len(a.objects),1)
        self.assertAlmostEqual(a.objects[0]['a'][0],1);self.assertAlmostEqual(a.objects[0]['a'][1],3)
        self.assertFalse(a._library['fixed']);self.assertEqual(a._library['angle'],90)
        a.library_fields['angle'].set('bad');a.double_click(event)
        self.assertEqual(len(a.objects),1);self.assertTrue(a.library_error.get())
        a.library_fields['angle'].set('0')
        for stamp in (10000,10100):
            a.canvas.event_generate('<ButtonPress-1>',x=round(x),y=round(y),time=stamp)
            a.canvas.event_generate('<ButtonRelease-1>',x=round(x),y=round(y),time=stamp+20)
            self.root.update()
        self.assertEqual(len(a.objects),2)

    def test_load_folders_nonrecursive_deduplicated_and_filename_hints(self):
        a=self.a;folder=Path(self.temp.name);default=folder/'LIBRARY';other=folder/'Other'
        nested=default/'Nested';nested.mkdir(parents=True);other.mkdir()
        for path in (default/'Top.dxf',nested/'Child.dxf',other/'Extra.DXF'):path.write_text('placeholder')
        with patch('cad_library.LIBRARY_DIR',default),patch('cad_library.cad_import.read_dxf',side_effect=lambda p:(source(),[])) as reader:
            a.library_dialog();self.root.update()
            self.assertEqual([Path(call.args[0]).name for call in reader.call_args_list],['Top.dxf'])
            self.assertEqual(len(a.library_icons),1);self.assertEqual(a.library_icons[0].cget('width'),'64')
            self.assertEqual(a.library_hints[0].text,'Top.dxf');self.assertEqual(a.library_hints[0].delay,1000)
            with patch('cad_library.filedialog.askdirectory',return_value=str(nested)) as chooser:a.load_library()
            self.assertEqual(len(a.library_icons),2);self.assertEqual(chooser.call_args.kwargs['initialdir'],str(default))
            with patch('cad_library.filedialog.askdirectory',return_value=str(other)):a.load_library();a.load_library()
            self.assertEqual(len(a.library_icons),3)
            with patch('cad_library.filedialog.askdirectory',return_value=''):a.load_library()
            self.assertEqual(len(a.library_icons),3)
            a.toggle_panel('library');self.root.update();self.assertEqual(len(a.library_icons),3)
            hint=a.library_hints[0];hint.schedule();self.assertIsNone(hint.popup)
            self.root.after(1100,self.root.quit);self.root.mainloop();self.assertIsNotNone(hint.popup)
            a.close_library();self.assertIsNone(hint.popup)

    def test_change_tools_cancels_placement(self):
        a=self.a;a.begin_library(source(),'Example');a.family.set('Lines');a.family_changed()
        self.assertIsNone(a._library);self.assertIn('length',a.params)
