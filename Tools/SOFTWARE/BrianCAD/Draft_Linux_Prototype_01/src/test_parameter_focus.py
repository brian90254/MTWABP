import os
import unittest
import tkinter as tk
from types import SimpleNamespace
from draft import Draft

@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires display')
class ParameterFocusTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk()
        self.a=Draft(self.root)
        self.root.update()
        self.root.focus_force()
        self.a.snap.set(False)
        self.a.grid_snap.set(False)

    def tearDown(self):
        self.root.destroy()

    def click(self,point):
        x,y=self.a.screen(point)
        self.a.click(SimpleNamespace(x=x,y=y,state=0))
        self.root.update()

    def test_line_start_and_resize(self):
        a=self.a
        a.family.set('Lines');a.family_changed()
        self.click([1,1])
        self.assertEqual(self.root.focus_get(),a.parameter_entries['x'])
        a.params['x'].set('1+1')
        a.parameter_entries['x'].event_generate('<Tab>')
        self.root.update()
        self.assertEqual(self.root.focus_get(),a.parameter_entries['y'])
        self.assertEqual(a.points[0],[2,1])
        self.click([5,5])
        self.assertEqual(self.root.focus_get(),a.parameter_entries['length'])
        self.assertTrue(a.parameter_entries['length'].selection_present())
        a.params['length'].set('10')
        a.parameter_entries['length'].event_generate('<Return>')
        self.root.update()
        self.assertEqual(len(a.objects),1)
        self.assertEqual(a.objects[0]['a'],[2,1])
        for actual,expected in zip(a.objects[0]['b'],[8,9]):
            self.assertAlmostEqual(actual,expected)
        a.undo()
        self.assertEqual(a.objects[0]['b'],[5,5])

    def test_circle_diameter_focus_and_enter(self):
        a=self.a
        a.family.set('Circles');a.family_changed()
        self.click([2,3])
        self.assertEqual(self.root.focus_get(),a.parameter_entries['diameter'])
        a.params['diameter'].set('6+4')
        a.parameter_entries['diameter'].event_generate('<Return>')
        self.root.update()
        self.assertEqual(len(a.objects),1)
        self.assertEqual(a.objects[0]['center'],[2,3])
        self.assertEqual(a.objects[0]['radius'],5)
