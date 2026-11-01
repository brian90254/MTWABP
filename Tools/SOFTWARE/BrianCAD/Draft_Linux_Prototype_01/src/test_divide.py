"""Equal-length, shape-preserving division and atomic replacement of selections."""
import copy
import math
import unittest
import cad_geometry as g
import cad_selection as s
from cad_divide import divide_object,segment_count,CurveLength
from cad_document import Document


def endpoints(o):
    from cad_groups import endpoints as points
    return points(o)

class DivideTests(unittest.TestCase):
    def test_lines_circle_and_clockwise_arc(self):
        for o in [dict(type='line',a=[-1,2],b=[5,10]),
                  dict(type='circle',center=[2,3],radius=2,handle_angle=.7),
                  dict(type='arc',center=[2,3],radius=2,start=6.1,sweep=-4.8)]:
            o.update(color='#123456',weight=.023,pattern='Dashed',layer='Layer1',group='old')
            before=copy.deepcopy(o);sections=divide_object(o,4);self.assertEqual(len(sections),4)
            lengths=[]
            for parts in sections:
                self.assertEqual(len(parts),1);part=parts[0]
                self.assertNotIn('group',part);self.assertEqual(part['color'],'#123456');self.assertEqual(part['weight'],.023)
                lengths.append(g.length(part))
                if o['type']!='line':self.assertEqual(part['type'],'arc')
                if o['type']=='arc':self.assertLess(part['sweep'],0)
            for a,b in zip(sections,sections[1:]):self.assertLess(g.dist(endpoints(a[-1])[1],endpoints(b[0])[0]),1e-10)
            self.assertAlmostEqual(max(lengths),min(lengths));self.assertEqual(o,before)
            if o['type']=='circle':self.assertLess(g.dist(endpoints(sections[-1][-1])[1],g.polar(o['center'],o['radius'],.7)),1e-10)
    def test_ellipse_full_and_trimmed_equal_arc_lengths(self):
        for sweep in (g.TAU,-4.7):
            o=dict(type='ellipse',center=[1,2],rx=4,ry=.8,angle=.6,start=.37,sweep=sweep)
            sections=divide_object(o,5);lengths=[CurveLength(parts[0]).total for parts in sections]
            self.assertLess(max(lengths)-min(lengths),1e-7)
            for a,b in zip(sections,sections[1:]):self.assertLess(g.dist(endpoints(a[0])[1],endpoints(b[0])[0]),1e-9)
            self.assertAlmostEqual(sum(parts[0]['sweep'] for parts in sections),sweep)
    def test_bezier_exact_geometry_and_nonuniform_parameter_speed(self):
        for points in [[[0,0],[0,0],[4,0]],[[0,0],[0,4],[3,-2],[5,1]]]:
            o=dict(type='spline',method='bezier',points=points,closed=False)
            sections=divide_object(o,4);lengths=[CurveLength(parts[0]).total for parts in sections]
            self.assertLess(max(lengths)-min(lengths),1e-7)
            self.assertEqual(len(sections),4)
            for a,b in zip(sections,sections[1:]):self.assertLess(g.dist(endpoints(a[0])[1],endpoints(b[0])[0]),1e-9)
            measure=CurveLength(o);cuts=[0.]+[measure.parameter(measure.total*i/4) for i in range(1,4)]+[1.]
            for i,parts in enumerate(sections):
                piece=parts[0]
                for u in (0,.2,.5,.8,1):
                    p=s._bezier_point(piece['points'],u);q=s._bezier_point(o['points'],cuts[i]+(cuts[i+1]-cuts[i])*u)
                    self.assertLess(g.dist(p,q),1e-9)
            if points[-1]==[4,0]:self.assertAlmostEqual(sections[0][0]['points'][-1][0],1,places=8)
    def test_open_and_closed_through_spline_sections_are_independent_groups(self):
        for closed in (False,True):
            o=dict(type='spline',method='through',points=[[0,0],[1,3],[4,1],[5,2],[6,0]],closed=closed,group='source')
            sections=divide_object(o,3);self.assertEqual(len(sections),3)
            lengths=[sum(CurveLength(p).total for p in parts) for parts in sections]
            self.assertLess(max(lengths)-min(lengths),1e-7)
            groups=[]
            for parts in sections:
                if len(parts)>1:
                    group=parts[0]['group'];groups.append(group);self.assertNotEqual(group,'source')
                    self.assertTrue(all(p.get('group')==group for p in parts))
                for a,b in zip(parts,parts[1:]):self.assertLess(g.dist(endpoints(a)[1],endpoints(b)[0]),1e-9)
            self.assertEqual(len(groups),len(set(groups)))
            self.assertAlmostEqual(sum(lengths),CurveLength(o).total,places=7)
    def test_polygon_equal_perimeter_sections_preserve_vertices(self):
        for closed in (False,True):
            o=dict(type='polygon',points=[[0,0],[3,0],[3,1],[0,1]],closed=closed)
            sections=divide_object(o,3);lengths=[sum(g.length(p) for p in parts) for parts in sections]
            self.assertAlmostEqual(max(lengths),min(lengths))
            self.assertAlmostEqual(sum(lengths),g.length(o))
            for parts in sections:self.assertTrue(all(not p.get('closed',False) for p in parts))
    def test_multi_selection_independent_replace_and_undo_save(self):
        d=Document();d.add([dict(type='line',a=[0,0],b=[4,0]),dict(type='circle',center=[0,0],radius=1),
                          dict(type='line',a=[10,0],b=[11,0])]);d.selected={0,1};before=d.state();n=len(d.history)
        self.assertEqual(d.divide_objects({0,1},4),8);self.assertEqual(len(d.objects),9);self.assertEqual(d.selected,set(range(8)))
        self.assertEqual(d.objects[-1],before['objects'][-1]);self.assertEqual(len(d.history),n+1)
        self.assertEqual(Document.from_payload(d.payload()).objects,d.objects)
        d.undo();self.assertEqual(d.state(),before);d.redo();self.assertEqual(len(d.objects),9)
    def test_object_limit_is_checked_before_replacing_sources(self):
        d=Document();obj=d.prepare(dict(type='line',a=[0,0],b=[1,0]));d.objects=[obj]*99999
        with self.assertRaisesRegex(ValueError,'100000'):d.divide_objects({0},3)
        self.assertEqual(len(d.objects),99999);self.assertFalse(d.history)
    def test_atomic_invalid_counts_locked_hidden_too_small_and_limits(self):
        for value in ('',1,0,-1,2.5,True,'nan',1001):
            with self.assertRaises(ValueError):segment_count(value)
        d=Document();d.add([dict(type='line',a=[0,0],b=[2,0]),dict(type='line',a=[0,0],b=[g.EPS,0])])
        before=d.state();history=copy.deepcopy(d.history)
        with self.assertRaises(ValueError):d.divide_objects({0,1},2)
        self.assertEqual(d.state(),before);self.assertEqual(d.history,history)
        d.objects[0]['locked']=True
        with self.assertRaises(ValueError):d.divide_objects({0},2)
        d.objects[0]['locked']=False;d.layers[-1]['visible']=False
        with self.assertRaises(ValueError):d.divide_objects({0},2)
