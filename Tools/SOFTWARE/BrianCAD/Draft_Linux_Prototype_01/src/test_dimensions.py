"""Dimension arithmetic, persistence, selection and editable measurement controls."""
import copy
import math
import unittest
import cad_dimensions as dim
import cad_geometry as g
import cad_selection as selection
import cad_properties
import cad_clipboard
import cad_groups
from cad_document import Document,COLORS

class DimensionTests(unittest.TestCase):
    def test_diagonal_measurements_and_axis_special_cases(self):
        for end,angle in [([3,4],math.degrees(math.atan2(4,3))),([-3,4],math.degrees(math.atan2(4,-3))),
                          ([3,-4],math.degrees(math.atan2(-4,3))),([-3,-4],math.degrees(math.atan2(-4,-3)))]:
            objects=dim.between([0,0],end)
            self.assertEqual([o['metric'] for o in objects],['length','horizontal','vertical','angle'])
            for obj,value in zip(objects,[5,3,4,angle]):
                g.validate_geometry(obj);self.assertAlmostEqual(dim.measurement(obj),value)
                self.assertTrue(dim.layout(obj));self.assertTrue(all(math.isfinite(v) for path in dim.layout(obj) for p in path for v in p))
        for end in ([0,3],[4,0],[-4,0],[0,-3]):
            objects=dim.between([0,0],end)
            self.assertEqual(len(objects),1);self.assertAlmostEqual(dim.measurement(objects[0]),g.dist([0,0],end))
        with self.assertRaises(ValueError):dim.between([1,1],[1,1])

    def test_whole_object_measurements_and_units(self):
        line=dict(type='line',a=[1,2],b=[4,6])
        self.assertEqual(len(dim.on_object(line,[2,3])),1)
        self.assertEqual(dim.measurement(dim.on_object(line,[2,3])[0]),5)
        circle=dict(type='circle',center=[1,2],radius=2)
        objects=dim.on_object(circle,[3,2])
        self.assertEqual([o['metric'] for o in objects],['diameter','circumference'])
        self.assertEqual(dim.measurement(objects[0]),4);self.assertAlmostEqual(dim.measurement(objects[1]),4*math.pi)
        self.assertEqual(dim.text(objects[0],'mm'),'Ø 101.6 mm')
        for sweep in (-1.5*math.pi,1.5*math.pi):
            objects=dim.on_object(dict(circle,type='arc',start=.3,sweep=sweep),[1,4])
            self.assertEqual([o['metric'] for o in objects],['radius','arc_length'])
            self.assertEqual(dim.measurement(objects[0]),2);self.assertAlmostEqual(dim.measurement(objects[1]),3*math.pi)
        with self.assertRaises(ValueError):dim.on_object(dict(type='spline'),[0,0])

    def test_atomic_layer_creation_color_save_load_and_undo(self):
        d=Document();d.layers=[l for l in d.layers if l['name']!='Dimension'];before=d.state();count=len(d.history)
        d.add_dimensions(dim.between([0,0],[3,4]))
        self.assertEqual(len(d.history),count+1);self.assertEqual(d.active,before['active_layer'])
        self.assertEqual(d.selected,set(range(4)));self.assertTrue(all(o['layer']=='Dimension' and o['color']==COLORS['Blue'] for o in d.objects))
        loaded=Document.from_payload(d.payload());self.assertEqual(loaded.objects,d.objects)
        d.undo();self.assertEqual(d.state(),before);d.redo()
        d.set_layer('Dimension');d.set_layer_color('#123456');d.set_layer('Layer1');d.toggle_layer('Dimension')
        d.add_dimensions(dim.between([0,0],[2,0]))
        self.assertEqual(d.objects[-1]['color'],'#123456');self.assertTrue(d.visible(len(d.objects)-1))
        self.assertEqual(sum(l['name']=='Dimension' for l in d.layers),1)
        before=d.state();invalid=dim.between([0,0],[1,0]);invalid[0]['text_height']=0
        with self.assertRaises(ValueError):d.add_dimensions(invalid)
        self.assertEqual(d.state(),before)

    def test_edit_handles_move_clipboard_and_bounds(self):
        d=Document();d.add_dimensions(dim.between([0,0],[3,4]))
        o=d.objects[0]
        changed=cad_properties.apply_changes(o,{'bx':'6','by':'8','labelx':'1','text_height':'4mm'})
        changed=d.prepare(changed)
        self.assertEqual(dim.measurement(changed),10);self.assertAlmostEqual(changed['text_height'],4/25.4)
        self.assertEqual(selection.nearest_point(o['label'],o),o['label'])
        d.display_unit='mm'
        box=selection.bounds(o,'mm')
        d.select_window(box[:2],box[2:]);self.assertIn(0,d.selected)
        x,y=o['label'];d.select_window([x-.01,y-.01],[x+.01,y+.01])
        self.assertEqual(d.point_selection,{0:{'label'}})
        d.selected=set(range(4));d.point_selection={}
        box=selection.bounds(o);self.assertTrue(selection.wholly_inside(o,box))
        self.assertTrue(selection.in_box(o['label'],box))
        moved=selection.move_controls(o,{'label'},1,2)
        self.assertEqual(moved['a'],o['a']);self.assertEqual(moved['b'],o['b'])
        self.assertEqual(moved['label'],g.add(o['label'],[1,2]))
        scaled=g.transform(o,'Scale',factor=2)
        self.assertEqual(dim.measurement(scaled),10);self.assertAlmostEqual(scaled['text_height'],2*o['text_height'])
        self.assertFalse(cad_groups.is_closed(d.objects))
        snap=cad_clipboard.decode(cad_clipboard.encode(cad_clipboard.snapshot(d,{0})))
        cad_clipboard.place(d,snap,[10,10]);self.assertEqual(len(d.objects),5)
        self.assertEqual(dim.measurement(d.objects[-1]),5)
        d.delete_selected();self.assertEqual(len(d.objects),4)

    def test_validation_and_label_gaps(self):
        o=dim.between([0,0],[4,0])[0]
        for patch in ({'metric':'invalid'},{'a':[float('nan'),0]},{'b':[0,0]},{'sweep':0},{'text_height':-1}):
            with self.assertRaises(ValueError):g.validate_geometry(dict(o,**patch))
        box=dim.label_bounds(o)
        for path in dim.layout(o):
            a,b=path;mid=g.mul(g.add(a,b),.5)
            self.assertFalse(box[0]+1e-10<mid[0]<box[2]-1e-10 and box[1]+1e-10<mid[1]<box[3]-1e-10)

    def test_collapsed_projections_and_zero_angle_do_not_break_rendering(self):
        for o in dim.between([0,0],[3,4]):
            o['b']=[0,3] if o['metric']=='horizontal' else [3,0]
            g.validate_geometry(o);dim.layout(o);selection.bounds(o)
        for o in dim.on_object(dict(type='circle',center=[0,0],radius=1),[1,0]):
            o['label']=list(o['b']);dim.layout(o);selection.bounds(o)

try:import ezdxf
except ImportError:ezdxf=None

@unittest.skipUnless(ezdxf,'Optional ezdxf is required')
class DimensionDXFTests(unittest.TestCase):
    def test_annotations_export_as_strokes_and_centered_text(self):
        from cad_dxf import build_dxf,snapshot_drawing
        d=Document();d.add_dimensions(dim.between([0,0],[3,4]));d.display_unit='mm'
        before=d.state();drawing,report=build_dxf(snapshot_drawing(d))
        labels=list(drawing.modelspace().query('TEXT'))
        self.assertEqual(len(labels),4);self.assertEqual(labels[0].dxf.text,'127 mm')
        self.assertTrue(all(e.dxf.layer==report['layer_names']['Dimension'] for e in labels))
        self.assertEqual(labels[0].dxf.halign,1);self.assertEqual(labels[0].dxf.valign,2)
        self.assertTrue(drawing.modelspace().query('LWPOLYLINE'));self.assertEqual(d.state(),before)
        import tempfile
        from pathlib import Path
        import ezdxf
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'dimensions.dxf';drawing.saveas(path);loaded=ezdxf.readfile(path)
            self.assertEqual(len(loaded.modelspace().query('TEXT')),4)
            self.assertFalse(loaded.audit().has_errors)
