"""Regression checks for retained rendering and hidden-layer work avoidance."""
import copy
import os
import sys
import tkinter as tk
import unittest
from unittest.mock import patch
from cad_document import Document
from draft import Draft

class DirtyTests(unittest.TestCase):
    def test_dirty_does_not_copy_and_detects_nested_changes_and_reverts(self):
        d=Document();d.add([dict(type='line',a=[0,0],b=[1,0])]);d.saved=d.state()
        with patch.object(d,'state',side_effect=AssertionError('dirty must not copy the drawing')):
            self.assertFalse(d.dirty);d.objects[0]['a'][0]=2;self.assertTrue(d.dirty)
            d.objects[0]['a'][0]=0;self.assertFalse(d.dirty)
            d.layers[0]['visible']=False;self.assertTrue(d.dirty);d.layers[0]['visible']=True
            d.grid_subdivisions=8;self.assertTrue(d.dirty)

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class RenderingTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update()
        a=self.a;a.doc.add_layer('Hidden');a.doc.add([
            dict(type='circle',center=[0,0],radius=1),
            dict(type='circle',center=[10000,10000],radius=1),
            dict(type='circle',center=[0,0],radius=2,layer='Hidden')])
        a.doc.toggle_layer('Hidden');a.doc.clear_selection();a.draw()
    def tearDown(self):self.root.destroy()
    def test_mouse_overlay_retains_grid_and_geometry(self):
        a=self.a;c=a.canvas;grid=c.find_withtag('background');geometry=c.find_withtag('geometry')
        self.assertEqual(len(geometry),1)
        with patch('draft.geo.path',side_effect=AssertionError('unchanged scene must not be retessellated')):
            for p in ([.1,.2],[.2,.3],[.3,.4]):a.mouse=list(p);a.marker='endpoint';a.draw()
        self.assertEqual(c.find_withtag('background'),grid);self.assertEqual(c.find_withtag('geometry'),geometry)
        self.assertEqual(len(c.find_withtag('snap-marker')),2)
        a.marker='';a.draw();self.assertFalse(c.find_withtag('snap-marker'))
    def test_geometry_view_layer_selection_and_inplace_edits_invalidate(self):
        a=self.a;c=a.canvas;old=c.find_withtag('geometry')
        a.doc.selected={0};a.draw();self.assertNotEqual(c.find_withtag('geometry'),old)
        self.assertEqual(len(c.find_withtag('geometry')),3)  # curve + center/radius handles
        a.doc.clear_selection();a.objects[0]['radius']=.7;a.draw()
        self.assertEqual(len(c.find_withtag('geometry')),1)
        old=c.coords(c.find_withtag('geometry')[0]);a.origin[0]+=100;a.draw()
        self.assertNotEqual(c.coords(c.find_withtag('geometry')[0]),old)
        a.doc.toggle_layer('Hidden');a.draw();self.assertEqual(len(c.find_withtag('geometry')),2)
        a.doc.toggle_layer('Layer1');a.draw();self.assertEqual(len(c.find_withtag('geometry')),1)
        a.doc.undo();a.draw();self.assertEqual(len(c.find_withtag('geometry')),2)
    def test_hidden_objects_do_not_generate_anchors_or_paths_and_cache_updates(self):
        a=self.a;visible=a.objects[0];hidden=a.objects[2]
        from cad_geometry import anchors,path
        def checked_anchors(o):
            self.assertIsNot(o,hidden);return anchors(o)
        def checked_path(o,*args):
            self.assertIsNot(o,hidden);return path(o,*args)
        with patch('draft.anchors',side_effect=checked_anchors),patch('draft.geo.path',side_effect=checked_path):
            a.snap_point([1,0]);a.mouse=[.1,.2];a.draw()
        before=a.object_anchors(visible);visible['radius']=.6
        self.assertNotEqual(a.object_anchors(visible),before)
        a.draw();geometry=a.canvas.find_withtag('geometry');a.objects=[];a.draw()
        self.assertTrue(geometry);self.assertFalse(a.canvas.find_withtag('geometry'))
