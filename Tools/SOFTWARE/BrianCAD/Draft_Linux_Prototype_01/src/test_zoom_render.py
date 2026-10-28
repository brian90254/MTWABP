"""View transforms reuse native items and cached paths without changing geometry."""
import copy
import os
import sys
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from draft import Draft
import cad_geometry as g

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class ZoomRenderingTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update()
        a=self.a;a.scale=100;a.origin=[250,350]
        a.doc.add([dict(type='line',a=[0,0],b=[2,1],weight=.02),
                   dict(type='circle',center=[3,0],radius=.5),
                   dict(type='spline',method='bezier',points=[[0,2],[1,3],[2,2]],closed=False)])
        a.doc.clear_selection();a.draw()
    def tearDown(self):self.root.destroy()
    def test_zoom_and_pan_keep_items_paths_and_world_coordinates(self):
        a=self.a;c=a.canvas;items=c.find_withtag('geometry');before=a.doc.state()
        with patch('draft.geo.path',side_effect=AssertionError('view changes must not resample retained curves')):
            for i in range(12):a.zoom(SimpleNamespace(x=400,y=250),1.03 if i%2==0 else 1/1.03)
            a.origin[0]+=25;a.origin[1]-=15;a.draw()
        self.assertEqual(c.find_withtag('geometry'),items);self.assertEqual(a.doc.state(),before)
        expected=a.screen([0,0])+a.screen([2,1])
        for x,y in zip(c.coords(items[0]),expected):self.assertAlmostEqual(x,y,places=8)
    def test_handles_stay_fixed_and_line_width_tracks_scale(self):
        a=self.a;c=a.canvas;a.doc.selected={0};a.draw();ids=c.find_withtag('entity:0')
        curve=ids[0];handles=ids[1:]
        for factor in (2,.1,5):
            a.scale*=factor;a.draw();self.assertEqual(c.find_withtag('entity:0'),ids)
            self.assertAlmostEqual(float(c.itemcget(curve,'width')),max(1,min(5,.02*a.scale)))
            for item in handles:
                x,y,xx,yy=c.coords(item);self.assertAlmostEqual(xx-x,8);self.assertAlmostEqual(yy-y,8)
    def test_culling_reentry_uses_cache_and_edit_updates_only_one(self):
        a=self.a;c=a.canvas;ids=c.find_withtag('entity:0');other=c.find_withtag('entity:1')
        with patch('draft.geo.path',side_effect=AssertionError('returning objects should reuse cached paths')):
            a.origin[0]+=10000;a.draw();self.assertFalse(c.find_withtag('geometry'))
            a.origin[0]-=10000;a.draw();self.assertEqual(len(c.find_withtag('geometry')),3)
        other=c.find_withtag('entity:1');old=c.find_withtag('entity:0')
        a.doc.commit_updates({0:dict(a.objects[0],b=[2,.5])});a.draw()
        self.assertEqual(c.find_withtag('entity:1'),other);self.assertNotEqual(c.find_withtag('entity:0'),old)
        a.undo();self.assertEqual(c.find_withtag('entity:1'),other)
        for actual,expected in zip(c.coords(c.find_withtag('entity:0')[0]),a.screen([0,0])+a.screen([2,1])):
            self.assertAlmostEqual(actual,expected)
    def test_fit_uses_bounds_and_cache_has_vertex_budget(self):
        a=self.a
        with patch('draft.geo.path',side_effect=AssertionError('Fit should use bounds and transform existing objects')):a.fit()
        with patch('draft.DISPLAY_PATH_POINT_LIMIT',260):
            for i in range(10):a.object_path(dict(type='circle',center=[i,0],radius=1))
            self.assertLessEqual(a._path_cache_points,260)
