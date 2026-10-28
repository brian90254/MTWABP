"""Import geometry, layers, units and atomic merge behavior."""
import copy
import math
from pathlib import Path
import tempfile
import unittest
try: import ezdxf
except ImportError: ezdxf=None
from cad_document import Document,COLORS
from cad_import import merge,read_drawing,read_dxf,_geometry
from cad_dxf import export_dxf,snapshot_drawing
import cad_geometry as g

class MergeTests(unittest.TestCase):
    def test_native_merge_undo_existing_and_empty_layers(self):
        target=Document(); target.add_layer('Shared'); target.grid_spacing=2
        source=Document(); source.add_layer('Shared'); source.add_layer('New'); source.add_layer('Empty')
        for name in ('Shared','New'):
            source.add([dict(type='line',a=[0,0],b=[1,2],layer=name,color=COLORS['Cyan'])])
        before=target.state(); saved=copy.deepcopy(target.saved); n=len(target.history)
        self.assertEqual(merge(target,source),2)
        self.assertEqual(len(target.history),n+1); self.assertEqual(target.saved,saved)
        self.assertEqual([l['name'] for l in target.layers].count('Shared'),1)
        self.assertNotIn('Empty',[l['name'] for l in target.layers]); self.assertEqual(target.grid_spacing,2)
        self.assertEqual(target.selected,{0,1}); target.undo(); self.assertEqual(target.state(),before)
        target.redo(); self.assertEqual(len(target.objects),2)
    def test_hidden_layers_and_long_names_survive_save(self):
        target=Document();target.add_layer('Shared');target.toggle_layer('Shared')
        source=Document();source.add_layer('Shared');source.add_layer('A'*240)
        source.add([dict(type='circle',center=[0,0],radius=1,layer='Shared'),
                    dict(type='circle',center=[3,0],radius=1,layer='A'*240)])
        source.toggle_layer('A'*240)
        merge(target,source)
        self.assertFalse(target.selected)
        reopened=Document.from_payload(target.payload())
        self.assertEqual(reopened.objects,target.objects)
        self.assertFalse(next(l for l in reopened.layers if l['name']=='Shared')['visible'])
    def test_invalid_import_is_atomic(self):
        target=Document(); source=Document(); source.add([dict(type='circle',center=[0,0],radius=1)])
        source.objects[0]['radius']=-1; before=target.state()
        with self.assertRaises(ValueError): merge(target,source)
        self.assertEqual(target.state(),before); self.assertFalse(target.history)
    def test_native_file_and_palette(self):
        import json
        d=Document()
        for color in COLORS.values(): d.add([dict(type='circle',center=[0,0],radius=1,color=color)])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'native.draft.json'; path.write_text(json.dumps(d.payload()))
            source,warnings=read_drawing(path)
        self.assertEqual(source.objects,d.objects); self.assertFalse(warnings)

@unittest.skipUnless(ezdxf,'Optional ezdxf is required')
class DXFImportTests(unittest.TestCase):
    def read(self,d):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.dxf'; d.saveas(path); return read_dxf(path)
    def test_export_import_all_geometry_and_colors(self):
        d=Document()
        objects=[dict(type='line',a=[0,0],b=[2,1]),dict(type='circle',center=[2,2],radius=1),
                 dict(type='arc',center=[3,3],radius=2,start=6.,sweep=-2.),
                 dict(type='ellipse',center=[5,5],rx=1,ry=3,angle=.7,start=5.9,sweep=-2.),
                 dict(type='spline',method='bezier',points=[[0,0],[1,3],[3,0]],closed=False),
                 dict(type='polygon',points=[[0,0],[1,1],[2,0]],closed=True)]
        for i,o in enumerate(objects): d.add([dict(o,color=list(COLORS.values())[i])])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'out.dxf';export_dxf(path,snapshot_drawing(d));source,warnings=read_dxf(path)
        self.assertFalse(warnings); self.assertEqual(len(source.objects),6)
        for a,b in zip(d.objects,source.objects):
            self.assertEqual(a['color'],b['color']); self.assertEqual(a['layer'],b['layer'])
            pa=g.path(a,64); pb=g.path(b,64)
            if a['type']=='arc': pb.reverse()
            if a['type']=='ellipse': pb.reverse()
            for p,q in zip(pa,pb): self.assertLess(g.dist(p,q),1e-7)
    def test_mm_colors_bylayer_and_empty_layers(self):
        d=ezdxf.new('R2000'); d.units=4; d.layers.new('Cyan',dxfattribs={'color':4}); d.layers.new('Empty')
        m=d.modelspace();m.add_line((0,0),(25.4,0),dxfattribs={'layer':'Cyan'})
        for color in range(1,8):m.add_circle((0,0),25.4,dxfattribs={'color':color})
        source,warnings=self.read(d); self.assertFalse(warnings)
        self.assertAlmostEqual(source.objects[0]['b'][0],1); self.assertEqual(source.objects[0]['color'],COLORS['Cyan'])
        self.assertNotIn('Empty',[l['name'] for l in source.layers]); self.assertEqual(len({o['color'] for o in source.objects[1:]}),7)
    def test_layer_true_color_overrides_aci_and_nested_block_style(self):
        d=ezdxf.new();d.units=1
        d.layers.new('RGB',dxfattribs={'color':1,'true_color':int(COLORS['Cyan'][1:],16)})
        d.modelspace().add_circle((0,0),1,dxfattribs={'layer':'RGB'})
        b=d.blocks.new('Inner');b.add_line((0,0),(1,0),dxfattribs={'color':0,'linetype':'BYBLOCK','lineweight':-2})
        b=d.blocks.new('Outer');b.add_blockref('Inner',(2,0),dxfattribs={'color':0,'linetype':'BYBLOCK','lineweight':-2})
        d.modelspace().add_blockref('Outer',(5,0),dxfattribs={'layer':'RGB','color':6,'linetype':'DASHED','lineweight':50})
        source,warnings=self.read(d);self.assertFalse(warnings)
        self.assertEqual(source.objects[0]['color'],COLORS['Cyan'])
        obj=source.objects[1];self.assertEqual(obj['a'],[7,0]);self.assertEqual(obj['color'],COLORS['Magenta'])
        self.assertEqual(obj['pattern'],'Dashed');self.assertAlmostEqual(obj['weight'],50/2540)
    def test_negative_extrusion_arcs_and_ellipses(self):
        d=ezdxf.new(); d.units=1
        a=d.modelspace().add_arc((2,3),2,350,80,dxfattribs={'extrusion':(0,0,-1)})
        e=d.modelspace().add_ellipse((2,3),(2,1),.4,.3,4.5,dxfattribs={'extrusion':(0,0,-1)})
        for entity in (a,e):
            obj=_geometry(entity,1)[0][0]
            actual=g.path(obj,64)
            pts=list(entity.vertices(entity.angles(len(actual)) if entity.dxftype()=='ARC' else entity.params(len(actual))))
            for p,q in zip(actual,pts):self.assertLess(g.dist(p,(q.x,q.y)),1e-8)
    def test_polylines_bulges_blocks_and_unsupported(self):
        d=ezdxf.new(); d.units=1; m=d.modelspace()
        m.add_lwpolyline([(0,0,1),(2,0,0)],format='xyb')
        m.add_polyline2d([(0,0),(1,1),(2,0)])
        m.add_polyline3d([(0,0,0),(1,0,0)])
        d.layers.new('Block layer',dxfattribs={'color':6})
        block=d.blocks.new('B'); block.add_line((0,0),(1,0),dxfattribs={'color':0})
        m.add_blockref('B',(5,2),dxfattribs={'layer':'Block layer','color':2})
        m.add_text('unhandled'); m.add_line((0,0,1),(1,0,1))
        source,warnings=self.read(d)
        self.assertEqual(len(source.objects),4,repr(warnings))
        self.assertEqual(source.objects[-1]['layer'],'Block layer');self.assertEqual(source.objects[-1]['color'],COLORS['Yellow'])
        self.assertEqual(source.objects[-1]['a'],[5,2]);self.assertIn('TEXT',' '.join(warnings))
    def test_general_spline_and_unitless_warning(self):
        d=ezdxf.new();d.units=0;d.modelspace().add_spline(fit_points=[(0,0),(1,2),(3,1),(5,3)])
        source,warnings=self.read(d)
        self.assertGreater(len(source.objects),4);self.assertTrue(all(o['type']=='line' for o in source.objects))
        self.assertIn('no declared units',' '.join(warnings));self.assertIn('converted',' '.join(warnings))

if __name__=='__main__':unittest.main()
