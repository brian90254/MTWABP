"""Dimension mouse workflows and retained Canvas/inspector integration."""
import os
import sys
import math
import tkinter as tk
import unittest
from types import SimpleNamespace
from draft import Draft
from cad_document import COLORS

@unittest.skipUnless(os.environ.get('DISPLAY') or sys.platform=='darwin','A graphical display is required')
class DimensionUITests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.a=Draft(self.root);self.root.update()
        self.errors=[];self.callbacks=[];self.a.error=self.errors.append
        self.root.report_callback_exception=lambda *args:self.callbacks.append(args)
        self.a.family.set('Dimension');self.a.family_changed()
    def tearDown(self):
        self.root.destroy()
        self.assertFalse(self.errors,repr(self.errors));self.assertFalse(self.callbacks,repr(self.callbacks))
    def click(self,p):
        x,y=self.a.screen(p)
        self.a.click(SimpleNamespace(x=x,y=y,state=0));self.root.update()
    def test_two_point_snap_creation_select_edit_units_zoom_delete(self):
        a=self.a
        self.click([0,0]);self.assertEqual(len(a.objects),0)
        self.click([3,2]);self.assertEqual(len(a.objects),4)
        self.assertEqual(len(a.canvas.find_withtag('geometry')),sum(len(a.canvas.find_withtag('entity:'+str(i))) for i in range(4)))
        a.return_to_select();a.selected={0};a.edit_dialog();self.root.update()
        self.assertIn('labelx',a.edit_fields);self.assertIn('text_height',a.edit_fields)
        self.assertEqual(a.hit(a.objects[0]['label']),0)
        a.edit_fields['text_height'].set('0.2');a.apply_edit()
        self.assertAlmostEqual(a.objects[0]['text_height'],.2)
        a.doc.set_display_unit('mm');a.draw()
        self.assertTrue(any('mm' in a.canvas.itemcget(item,'text') for item in a.canvas.find_withtag('entity:0') if a.canvas.type(item)=='text'))
        before=len(a.canvas.find_withtag('geometry'))
        a.scale*=1.3;a.draw();self.assertEqual(len(a.canvas.find_withtag('geometry')),before)
        a.origin[0]+=30;a.draw();self.assertEqual(len(a.canvas.find_withtag('geometry')),before)
        a.selected={0};a.delete();self.assertEqual(len(a.objects),3)
        a.undo();self.assertEqual(len(a.objects),4)
        a.redo();self.assertEqual(len(a.objects),3)
        a.fit();a.draw()
    def test_whole_line_circle_arc_and_repeated_measurements(self):
        a=self.a;a.grid_snap.set(False)
        a.doc.add([dict(type='line',a=[-2,-1],b=[2,1])])
        self.click([0,0]);self.assertEqual(len(a.points),1)
        self.click([.8,.4])
        self.assertEqual(len(a.objects),2);self.assertEqual(a.objects[-1]['metric'],'length')
        a.doc.add([dict(type='circle',center=[0,0],radius=1)])
        self.click([math.cos(.7),math.sin(.7)])
        self.assertEqual([o['metric'] for o in a.objects[-2:]],['diameter','circumference'])
        a.doc.add([dict(type='arc',center=[-2,0],radius=1,start=0,sweep=-math.pi)])
        self.click([-2+math.cos(-.8),math.sin(-.8)])
        self.assertEqual([o['metric'] for o in a.objects[-2:]],['radius','arc_length'])
        self.assertTrue(all(o['color']==COLORS['Blue'] for o in a.objects if o['type']=='dimension'))
        a.draw();a.right_click();self.assertEqual(a.family.get(),'Select')
    def test_pending_pair_cancel_and_horizontal_only(self):
        a=self.a
        self.click([0,0]);a.right_click();self.assertEqual(a.points,[]);self.assertEqual(len(a.objects),0)
        a.family.set('Dimension');a.family_changed()
        before=a.doc.state()
        self.click([0,0]);self.click([2,0]);self.assertEqual(len(a.objects),1)
        a.undo();self.assertEqual(a.doc.state(),before)
