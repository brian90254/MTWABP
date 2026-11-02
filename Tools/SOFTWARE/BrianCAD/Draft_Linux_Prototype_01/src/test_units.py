"""Unit conversion, bounded math expressions, physical invariants and persistence."""
import copy
import math
import unittest
from cad_units import parse_number,format_value
from cad_document import Document
from cad_properties import apply_changes,values
from cad_divide import segment_count
from cad_import import merge

class UnitTests(unittest.TestCase):
    def test_arithmetic_fraction_and_suffix_conversion(self):
        for text,unit,expected in [('6+4','in',10),('5/8','in',.625),('12mm','in',12/25.4),
            ('12"','mm',12),('5/8"','mm',.625),('1 1/2"','mm',1.5),('2*(3+4)mm','in',14/25.4),
            ('2in + 12mm','mm',2+12/25.4),('-2cm','in',-2/2.54),('1ft','mm',12),('5/8e3','in',.000625),
            ('(10-2)/4','mm',2/25.4),('1e-3m','in',1/25.4),('12 MM','in',12/25.4)]:
            with self.subTest(text=text,unit=unit):self.assertAlmostEqual(parse_number(text,unit),expected,places=10)
        self.assertEqual(format_value(parse_number('12"','mm'),'mm'),'304.8')
    def test_counts_angles_and_invalid_expressions(self):
        self.assertEqual(parse_number('2*3',kind='scalar'),6);self.assertEqual(segment_count('2+3'),5)
        self.assertAlmostEqual(parse_number('1rad',kind='angle'),180/math.pi)
        self.assertEqual(parse_number('45+45deg',kind='angle'),90)
        for text in ('2mm','2in'):
            with self.assertRaises(ValueError):parse_number(text,kind='scalar')
        for text in ('','1/0','6+','2**100','__import__("os")','float("nan")','1e309','2;3','(1+2','2unknown','2 3','('*40+'1'+')'*40):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):parse_number(text)
    def test_switch_does_not_resize_geometry_or_grid_and_native_roundtrip(self):
        d=Document();d.add([dict(type='circle',center=[1,2],radius=3)]);objects=copy.deepcopy(d.objects)
        before=d.state();history=len(d.history);d.set_display_unit('mm')
        self.assertEqual(d.objects,objects);self.assertEqual(d.grid_spacing,1);self.assertEqual(d.grid_spacing/d.grid_subdivisions,.25)
        self.assertEqual(len(d.history),history+1);self.assertEqual(d.display_unit,'mm')
        loaded=Document.from_payload(d.payload());self.assertEqual(loaded.display_unit,'mm');self.assertEqual(loaded.objects,objects);self.assertFalse(loaded.dirty)
        legacy=d.payload();legacy.pop('display_unit');self.assertEqual(Document.from_payload(legacy).display_unit,'in')
        d.undo();self.assertEqual(d.state(),before);d.redo();self.assertEqual(d.display_unit,'mm')
        target=Document();target.set_display_unit('cm');merge(target,loaded);self.assertEqual(target.display_unit,'cm');self.assertEqual(target.objects,objects)
    def test_editor_values_and_length_angle_point_expressions(self):
        d=Document();d.add([dict(type='line',a=[0,0],b=[2,0])]);line=d.objects[0]
        self.assertAlmostEqual(values(line,'mm')['bx'],50.8)
        obj=apply_changes(line,{'bx':'12"','weight':'0.5mm'},'mm')
        self.assertAlmostEqual(obj['b'][0],12);self.assertAlmostEqual(obj['weight'],.5/25.4)
        o=dict(type='spline',method='bezier',points=[[0,0],[1,2],[3,0]],closed=False)
        obj=apply_changes(o,{'points':'0,0; 1in,2mm; 3/2in,0'},'mm')
        self.assertAlmostEqual(obj['points'][-1][0],1.5);self.assertEqual(obj['points'][-1][1],0);self.assertAlmostEqual(obj['points'][1][1],2/25.4)
        with self.assertRaises(ValueError):apply_changes(o,{'points':'0,0,0; 1,1'},'mm')
