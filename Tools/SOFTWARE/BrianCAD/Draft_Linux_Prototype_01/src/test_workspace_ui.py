"""Workspace contexts, dock lifecycle/drafts, saved geometry and keyboard workflows."""
import json
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
from cad_workspace import WorkspacePreferences
from draft import Draft

class WorkspacePreferenceTests(unittest.TestCase):
    def test_validated_persistence_and_bad_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'workspace.json'
            p=WorkspacePreferences(path);p.data.update(width=460,split=.6,open=['layers'])
            p.data['panels']={'properties':{'mode':'float','geometry':'460x650+100+120'}}
            p.save();loaded=WorkspacePreferences(path)
            self.assertEqual(loaded.data,p.data)
            path.write_text(json.dumps({'width':-3,'split':float('nan'),'panels':{
                'properties':{'mode':'bad','geometry':'invalid'},'unknown':{}}}))
            loaded=WorkspacePreferences(path);self.assertEqual(loaded.data['width'],320)
            self.assertEqual(loaded.data['split'],.48);self.assertEqual(loaded.data['panels'],{'properties':{'mode':'dock'}})
            path.write_text('invalid json');self.assertEqual(WorkspacePreferences(path).data['width'],400)

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class WorkspaceUITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.settings=Path(self.temp.name)/'recent.json'
        self.pref=patch('cad_workspace.preferences_path',return_value=self.settings);self.pref.start()
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update();self.errors=[];self.callbacks=[]
        self.a.error=self.errors.append;self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
    def tearDown(self):
        if self.root.winfo_exists():self.root.destroy()
        self.pref.stop();self.temp.cleanup()
        self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def choose(self,family,method=None):
        a=self.a;a.family.set(family);a.family_changed()
        if method:a.tool.set(method);a.method_changed()
        self.root.update()
    def test_tool_tiles_context_and_primary_fields(self):
        a=self.a;self.assertEqual(len(a.tool_buttons),12)
        self.assertTrue(all(b.cget('image') for b in a.tool_buttons.values()))
        a.tool_buttons['Lines'].invoke();self.root.update()
        self.assertTrue(a.tool_buttons['Lines'].instate(['selected']))
        self.assertFalse(a.copy_check.winfo_ismapped());self.assertFalse(a.direction_check.winfo_ismapped())
        visible=[key for key,entry in a.parameter_entries.items() if entry.winfo_ismapped()]
        self.assertEqual(visible,['x','y','length','angle'])
        a.params['x2'].set('12mm');a.more_fields.set(True);a.toggle_more_fields();self.root.update()
        self.assertEqual(sum(e.winfo_ismapped() for e in a.parameter_entries.values()),8)
        a.more_fields.set(False);a.toggle_more_fields();a.focus_parameter('x2');self.root.update()
        self.assertEqual(a.params['x2'].get(),'12mm');self.assertTrue(a.more_fields.get())
        for key,next_key in [('x','y'),('y','length'),('length','angle')]:
            self.assertEqual(a.parameter_entries[key].tk_focusNext(),a.parameter_entries[next_key])
        self.choose('Arcs','Center + start + end');self.assertTrue(a.direction_check.winfo_ismapped())
        self.choose('Arcs','Three-point arc');self.assertFalse(a.direction_check.winfo_ismapped())
        self.choose('Modify');self.assertTrue(a.copy_check.winfo_ismapped())
        self.choose('Select');self.assertFalse(a.method_box.winfo_ismapped())
    def test_dock_float_round_trip_preserves_drawing_selection_and_drafts(self):
        a=self.a;a.doc.add([dict(type='line',a=[0,0],b=[2,1])]);a.draw()
        before=a.doc.state();selected=set(a.selected);a.layers_dialog();self.root.update()
        tall=a.layer_tree.winfo_height();a.edit_dialog();self.root.update()
        self.assertLess(a.layer_tree.winfo_height(),tall)
        self.assertTrue(a.edit_apply.winfo_ismapped())
        self.assertIsNone(self.root.grab_current());self.assertGreater(a.canvas.winfo_width(),200)
        self.assertLess(a.panels.right.winfo_width(),500)
        a.edit_fields['color'].set('Green')
        a.toggle_panel('properties');self.root.update()
        self.assertIsNotNone(a.panels.panels['properties']['top'])
        self.assertEqual(a.edit_fields['color'].get(),'Green');self.assertIn('color',a._edit_dirty)
        top=a.panels.panels['properties']['top'];top.geometry('440x600+60+70');self.root.update()
        a.toggle_panel('properties');self.root.update()
        self.assertIsNone(a.panels.panels['properties']['top'])
        width=a.panels.right.winfo_width()
        for _ in range(2):
            a.toggle_panel('properties');self.root.update();a.toggle_panel('properties');self.root.update()
        self.assertAlmostEqual(a.panels.right.winfo_width(),width,delta=2)
        self.assertEqual(a.doc.state(),before);self.assertEqual(a.selected,selected)
        self.assertEqual(a.edit_fields['color'].get(),'Green')
        a.edit_apply.invoke();self.assertEqual(a.objects[0]['color'],'#198548')
        a.layer_name.set('Pending name');a.toggle_panel('layers');self.root.update()
        self.assertEqual(a.layer_name.get(),'Pending name')
        a.toggle_panel('layers');self.root.update();self.assertEqual(a.layer_name.get(),'Pending name')
        a.close_layers();a.close_edit();self.root.update()
        self.assertEqual(len(a.panels.body.panes()),1);self.assertIsNone(a.edit_window)
        a.edit_dialog();self.root.update();self.assertEqual(a.edit_fields['color'].get(),'Green')
    def test_panel_geometry_and_width_saved_separately_from_drawing(self):
        a=self.a;a.layers_dialog();self.root.update()
        a.panels.body.sashpos(0,a.panels.body.winfo_width()-450);self.root.update();a.panels.remember()
        self.assertAlmostEqual(a.panels.preferences.data['width'],444,delta=12)
        a.toggle_panel('layers');self.root.update()
        top=a.panels.panels['layers']['top'];top.geometry('430x550+70+80');self.root.update()
        before=a.doc.state();a.panels.remember(open_state=True)
        prefs=WorkspacePreferences(self.settings.with_name('workspace.json'))
        self.assertEqual(prefs.data['panels']['layers']['mode'],'float');self.assertEqual(prefs.data['open'],['layers'])
        self.assertIn('430x550',prefs.data['panels']['layers']['geometry'])
        self.assertEqual(a.doc.state(),before)
    def test_panel_keyboard_and_canvas_center_survive_resize(self):
        a=self.a;a.doc.add([dict(type='line',a=[0,0],b=[2,1])]);a.draw()
        center=a.world(a.canvas.winfo_width()/2,a.canvas.winfo_height()/2)
        a.layers_dialog();self.root.update()
        for actual,expected in zip(a.world(a.canvas.winfo_width()/2,a.canvas.winfo_height()/2),center):self.assertAlmostEqual(actual,expected)
        a.edit_dialog();self.root.update()
        a.edit_fields['bx'].set('3');a.edit_widgets['bx'].focus_force();self.root.update()
        a.edit_widgets['bx'].event_generate('<Return>');self.root.update()
        self.assertEqual(a.objects[0]['b'],[3,1])
        a.edit_widgets['bx'].event_generate('<Escape>');self.root.update();self.assertIsNone(a.edit_window)
