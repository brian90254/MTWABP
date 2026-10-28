"""Exact 24-bit RGB colors across document, properties, DXF and native workflows."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
try: import ezdxf
except ImportError: ezdxf=None
from cad_document import Document,COLORS,rgb_color
from cad_properties import values,apply_changes
from cad_import import merge,read_drawing,read_dxf
from cad_dxf import export_dxf,snapshot_drawing

class RGBTests(unittest.TestCase):
    def test_native_save_import_edits_transforms_and_validation(self):
        d=Document();d.add([dict(type='line',a=[0,0],b=[2,1],color='#12AbEF')])
        self.assertEqual(d.objects[0]['color'],'#12abef');self.assertEqual(values(d.objects[0])['color'],'#12abef')
        updated=d.prepare(apply_changes(d.objects[0],{'weight':'.02'}));self.assertEqual(updated['color'],'#12abef')
        self.assertEqual(apply_changes(updated,{'color':'#A03C91'})['color'],'#a03c91')
        self.assertEqual(apply_changes(updated,{'color':'Blue'})['color'],COLORS['Blue'])
        d.transform_selected('Move',dx=3,dy=2);self.assertEqual(d.objects[0]['color'],'#12abef')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rgb.draft.json';path.write_text(json.dumps(d.payload()))
            source,warnings=read_drawing(path);self.assertFalse(warnings)
            target=Document();merge(target,source);self.assertEqual(target.objects,d.objects)
        before=d.state();history=copy.deepcopy(d.history)
        for bad in ('red','#abc','#12345678','#xx0000',' #112233',None,123):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):d.commit_updates({0:dict(updated,color=bad)})
        self.assertEqual(d.state(),before);self.assertEqual(d.history,history)

    @unittest.skipUnless(ezdxf,'Optional ezdxf is required')
    def test_exact_dxf_colors_entity_layer_block_and_roundtrip(self):
        d=ezdxf.new();d.units=1;m=d.modelspace()
        expected=['#12abef','#000000','#ffffff','#a03c91','#376e25']
        for i,color in enumerate(expected[:3]):m.add_line((i,0),(i,1),dxfattribs={'true_color':int(color[1:],16),'color':1})
        d.layers.new('RGB',dxfattribs={'true_color':int(expected[3][1:],16),'color':2})
        m.add_circle((0,0),1,dxfattribs={'layer':'RGB'})
        block=d.blocks.new('B');block.add_line((0,0),(1,1),dxfattribs={'color':0})
        m.add_blockref('B',(3,3),dxfattribs={'true_color':int(expected[4][1:],16)})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'in.dxf';d.saveas(path);source,warnings=read_dxf(path)
            self.assertFalse(warnings);self.assertEqual([o['color'] for o in source.objects],expected)
            path=Path(folder)/'out.dxf';export_dxf(path,snapshot_drawing(source));out=ezdxf.readfile(path)
            self.assertEqual([e.dxf.true_color for e in out.modelspace()],[int(c[1:],16) for c in expected])
            reloaded,warnings=read_dxf(path);self.assertFalse(warnings)
            self.assertEqual([o['color'] for o in reloaded.objects],expected)
        self.assertEqual(values(source.objects[0])['color'],expected[0])

    @unittest.skipUnless(ezdxf,'Optional ezdxf is required')
    def test_other_aci_colors_keep_their_rgb(self):
        from ezdxf.colors import aci2rgb
        d=ezdxf.new();d.units=1;d.modelspace().add_circle((0,0),1,dxfattribs={'color':30})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'aci.dxf';d.saveas(path);source,warnings=read_dxf(path)
        self.assertFalse(warnings);self.assertEqual(source.objects[0]['color'],'#{:02x}{:02x}{:02x}'.format(*aci2rgb(30)))
