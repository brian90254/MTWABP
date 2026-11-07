"""Curve-start directions and control-only transforms, including atomic failure."""
import copy
import math
import unittest
import cad_geometry as g
import cad_guides
import cad_selection as s
from cad_document import Document

class CurveStartGuideTests(unittest.TestCase):
    def parallel(self,a,b):self.assertAlmostEqual(g.cross(g.unit(a),g.unit(b)),0,places=7)
    def test_interior_line_circle_arc_ellipse_and_spline_contacts(self):
        cases=[
            ([1,1],dict(type='line',a=[0,0],b=[2,2]),[1,1]),
            ([1,0],dict(type='circle',center=[0,0],radius=1),[0,1]),
            ([0,-1],dict(type='arc',center=[0,0],radius=1,start=0,sweep=-math.pi),[1,0]),
            ([2,0],dict(type='ellipse',center=[0,0],rx=2,ry=1,angle=0),[0,1]),
            ([0,0],dict(type='spline',method='bezier',closed=False,points=[[0,0],[1,2],[2,0]]),[1,2]),
            ([2,0],dict(type='spline',method='bezier',closed=False,points=[[0,0],[1,2],[2,0]]),[1,-2]),
            ([0,0],dict(type='spline',method='bezier',closed=False,points=[[0,0],[0,0],[1,2],[2,0]]),[1,2]),
        ]
        for point,obj,tangent in cases:
            guides=cad_guides.directions(point,[obj]);self.assertEqual(len(guides),2,obj)
            self.parallel(guides[0][0],tangent);self.parallel(guides[1][0],g.normal(tangent))
        arc=dict(type='arc',center=[0,0],radius=1,start=0,sweep=math.pi/2)
        self.assertFalse(cad_guides.directions([-1,0],[arc]))
        self.assertFalse(cad_guides.directions([0,0],[dict(type='circle',center=[0,0],radius=1)]))
    def test_polygon_vertex_branches_and_guide_intersections(self):
        poly=dict(type='polygon',points=[[0,0],[2,0],[1,1]],closed=True)
        self.assertEqual(len(cad_guides.directions([0,0],[poly])),4)
        # Circle tangent at (1,0) intersects the grid, object and remembered Y.
        start=[1,0];guides=cad_guides.directions(start,[dict(type='circle',center=[0,0],radius=1)])
        hits,projections=cad_guides.targets(start,guides,[1.01,.51],.1,
            [dict(type='line',a=[.5,.5],b=[1.5,.5])],.25,[(1,.5)])
        for label in ('object intersection','grid intersection','alignment intersection'):
            self.assertTrue(any(g.dist(p,[1,.5])<1e-8 and label in name for p,name in hits),label)
        self.assertTrue(any(label=='tangent guide' for _,label in projections))

class PartialModifyTests(unittest.TestCase):
    def doc(self):
        d=Document();d.add([dict(type='line',a=[1,0],b=[2,0]),dict(type='circle',center=[4,0],radius=1)])
        d.clear_selection();return d
    def test_each_transform_leaves_unselected_endpoint_unchanged(self):
        for mode,options,expected in [('Move',dict(dx=2,dy=1),[3,1]),
                ('Rotate',dict(pivot=[0,0],angle=90),[0,1]),
                ('Scale',dict(pivot=[0,0],factor=3),[3,0]),
                ('Mirror',dict(pivot=[0,0],angle=90),[-1,0])]:
            d=self.doc();before=d.state();d.point_selection={0:{'a'}}
            d.transform_selected(mode,**options)
            self.assertLess(g.dist(d.objects[0]['a'],expected),1e-8);self.assertEqual(d.objects[0]['b'],[2,0])
            self.assertEqual(d.objects[1],before['objects'][1]);self.assertEqual(d.point_selection,{0:{'a'}})
            d.undo();self.assertEqual(d.state(),before);d.redo();self.assertLess(g.dist(d.objects[0]['a'],expected),1e-8)
    def test_circle_radius_spline_controls_and_arc_end(self):
        d=self.doc();d.point_selection={1:{'radius'}};d.transform_selected('Move',dx=1,dy=0)
        self.assertEqual(d.objects[1]['radius'],2);self.assertEqual(d.objects[1]['center'],[4,0])
        spline=dict(type='spline',method='bezier',closed=False,points=[[0,0],[1,2],[3,0]])
        changed=s.transform_controls(spline,{'p1'},'Rotate',pivot=[0,0],angle=90)
        self.assertEqual(changed['points'][0],[0,0]);self.assertEqual(changed['points'][2],[3,0])
        self.assertLess(g.dist(changed['points'][1],[-2,1]),1e-8)
        arc=g.arc_three([1,0],[0,1],[-1,0]);old=dict(s.controls(arc))
        changed=s.transform_controls(arc,{'end'},'Move',dx=-1,dy=0);new=dict(s.controls(changed))
        for key in ('start','through'):self.assertLess(g.dist(old[key],new[key]),1e-8)
        self.assertLess(g.dist(new['end'],[-2,0]),1e-8)
    def test_mixed_selection_copy_and_invalid_atomicity(self):
        d=self.doc();d.selected={1};d.point_selection={0:{'a'}};before=d.state();n=len(d.history)
        with self.assertRaises(ValueError):d.transform_selected('Move',dx=1,dy=0)  # collapse line
        self.assertEqual(d.state(),before);self.assertEqual(len(d.history),n)
        d.transform_selected('Move',dx=0,dy=1,copy_objects=True)
        self.assertEqual(d.objects[:2],before['objects']);self.assertEqual(d.selected,{3});self.assertEqual(d.point_selection,{2:{'a'}})
        self.assertEqual(d.objects[2]['a'],[1,1]);self.assertEqual(d.objects[2]['b'],[2,0])
        self.assertEqual(d.objects[3]['center'],[4,1])
    def test_hidden_locked_and_whole_owner_precedence(self):
        d=self.doc();d.objects[0]['locked']=True;d.point_selection={0:{'a'}}
        with self.assertRaises(ValueError):d.transform_selected('Move',dx=1,dy=1)
        d.objects[0]['locked']=False;d.selected={0};d.point_selection={0:{'a'}}
        d.transform_selected('Move',dx=0,dy=1)
        self.assertEqual(d.objects[0]['a'],[1,1]);self.assertEqual(d.objects[0]['b'],[2,1]);self.assertFalse(d.point_selection)

import os
import sys
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import patch
from draft import Draft
from cad_tools import METHODS

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class CurveGuideModifyUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update()
        self.errors=[];self.callbacks=[];self.a.error=self.errors.append
        self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
    def tearDown(self):
        self.root.destroy();self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def tool(self,family,method=None):
        a=self.a;a.family.set(family);a.family_changed()
        if method:a.tool.set(method);a.method_changed()
    def click(self,point):
        x,y=self.a.screen(point);self.a.click(SimpleNamespace(x=x,y=y,state=0));self.root.update()
    def test_method_memory_independent_and_survives_new_drawing(self):
        a=self.a;before=a.doc.state()
        for family,methods in METHODS.items():
            self.tool(family,methods[-1])
        for family,methods in METHODS.items():
            self.tool(family);self.assertEqual(a.tool.get(),methods[-1])
            self.assertEqual(tuple(a.method_box.cget('values')),tuple(methods))
        self.assertEqual(a.doc.state(),before)
        self.tool('Arcs','Three-point arc');a.new();self.tool('Circles');self.tool('Arcs')
        self.assertEqual(a.tool.get(),'Three-point arc')
    def test_curve_guides_across_drawing_tools_and_cached_on_motion(self):
        a=self.a;a.doc.add([dict(type='circle',center=[0,0],radius=1)]);a.doc.clear_selection();a.grid_snap.set(False)
        start=[2**-.5,2**-.5];target=g.add(start,[-.5,.5])
        for family,method in [('Lines','Two points'),('Arcs','Three-point arc'),
                ('Circles','Diameter endpoints'),('Ovals','Opposite corners'),
                ('Polygons','Rectangle corners'),('Splines','Through points')]:
            self.tool(family,method);self.click(start)
            point,label=a.snap_point(g.add(target,[.01,0]))
            self.assertEqual(label,'tangent guide',(family,label));self.assertLess(g.dist(point,target),.02)
            a.mouse=point;a.draw();self.assertTrue(a.canvas.find_withtag('line-guide'))
            with patch('draft.cad_guides.directions',side_effect=AssertionError('directions should be cached')):
                a.snap_point(g.add(target,[.01,.01]))
        self.tool('Lines');self.click([1,0]);a.grid_snap.set(True)
        point,label=a.snap_point([1.01,.51])
        self.assertIn('guide / grid intersection',label);self.assertLess(g.dist(point,[1,.5]),1e-8)
        a.snap.set(False);a.snap_point([1.01,.51]);a.draw();self.assertFalse(a.canvas.find_withtag('line-guide'))
    def test_modify_partial_controls_by_fields_and_mouse_and_snap_exclusion(self):
        a=self.a;a.doc.add([dict(type='line',a=[0,0],b=[2,0])]);a.doc.clear_selection();a.doc.point_selection={0:{'b'}}
        self.tool('Modify','Move');a.params['dx'].set('1');a.params['dy'].set('1');a.apply_parameters()
        self.assertEqual(a.objects[0]['a'],[0,0]);self.assertEqual(a.objects[0]['b'],[3,1])
        self.assertEqual(a.doc.point_selection,{0:{'b'}})
        a.grid_snap.set(False);self.assertEqual(a.snap_point([3,1])[1],'')
        self.tool('Modify','Rotate');self.click([0,0]);self.click([3,1]);self.click([-1,3])
        self.assertLess(g.dist(a.objects[0]['b'],[-1,3]),1e-8);self.assertEqual(a.objects[0]['a'],[0,0])
        a.undo();self.assertEqual(a.objects[0]['b'],[3,1])
