"""Independent DXF groups, entity expansion, and library-copy round trips."""
import copy
from pathlib import Path
import tempfile
import unittest
try:import ezdxf
except ImportError:ezdxf=None
import cad_dxf,cad_import
from cad_document import Document
from cad_library import placed

@unittest.skipUnless(ezdxf,'Install requirements-dxf.txt')
class DXFGroupTests(unittest.TestCase):
    def fixture(self,path):
        d=ezdxf.new('R2018');d.units=1
        d.layers.new('Bat');d.layers.new('Mechanism')
        m=d.modelspace()
        bat=[m.add_line((0,0),(2,0),dxfattribs={'layer':'Bat'}),m.add_line((2,0),(2,1),dxfattribs={'layer':'Bat'})]
        mech=[m.add_circle((0,0),.2,dxfattribs={'layer':'Mechanism'}),m.add_line((-1,-1),(1,-1),dxfattribs={'layer':'Mechanism'})]
        m.add_line((4,0),(4,1),dxfattribs={'layer':'Bat'})
        d.groups.new('Bat').set_data(bat);d.groups.new('Mechanism').set_data(mech);d.saveas(path)
        return d
    def test_library_copies_select_and_rotate_bat_independently_and_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'flipper.dxf';self.fixture(path);source,warnings=cad_import.read_dxf(path)
            self.assertEqual(warnings,[]);self.assertNotEqual(source.objects[0]['group'],source.objects[2]['group'])
            self.assertNotIn('group',source.objects[4])
            before=copy.deepcopy(source.payload());d=Document()
            cad_import.merge(d,placed(source,[10,20],0));cad_import.merge(d,placed(source,[30,40],45))
            self.assertEqual(len({o['group'] for o in d.objects if o.get('group')}),4)
            self.assertEqual(d.group_members({0}),{0,1});self.assertEqual(d.group_members({2}),{2,3})
            stationary=copy.deepcopy(d.objects[2:]);d.selected={0};d.transform_selected('Rotate',pivot=[10,20],angle=90)
            self.assertEqual(d.objects[2:],stationary);self.assertAlmostEqual(d.objects[0]['b'][1],22)
            self.assertEqual(source.payload(),before)
            out=Path(folder)/'out.dxf';cad_dxf.export_dxf(out,cad_dxf.snapshot_drawing(d))
            loaded,notes=cad_import.read_dxf(out);self.assertEqual(notes,[])
            self.assertEqual(loaded.group_members({0}),{0,1});self.assertEqual(loaded.group_members({2}),{2,3})
            self.assertNotIn('group',loaded.objects[4]);self.assertFalse(ezdxf.readfile(out).audit().has_errors)
            d.selected={0,1};cad_dxf.export_dxf(out,cad_dxf.snapshot_drawing(d),selected_only=True)
            selected=ezdxf.readfile(out);self.assertEqual(len(selected.groups),1);self.assertEqual(len(selected.modelspace()),2)
    def test_expanded_spline_entities_all_keep_group(self):
        d=Document();d.add([dict(type='spline',method='through',closed=False,points=[[0,0],[1,2],[2,0],[3,1]],group='bat'),dict(type='circle',center=[0,0],radius=1,group='bat')])
        exported,_=cad_dxf.build_dxf(cad_dxf.snapshot_drawing(d))
        self.assertEqual(len(exported.groups),1)
        members=list(next(iter(exported.groups))[1]);self.assertGreater(len(members),2)
        self.assertEqual(len(members),len(exported.modelspace()))
    def test_grouped_insert_expansion_and_overlapping_groups(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'insert.dxf';d=ezdxf.new();d.units=1;b=d.blocks.new('Part')
            b.add_line((0,0),(1,0));b.add_circle((0,0),.2)
            ins=d.modelspace().add_blockref('Part',(3,4));line=d.modelspace().add_line((0,0),(2,0))
            d.groups.new('One').set_data([ins,line]);d.groups.new('Two').set_data([line]);d.saveas(path)
            loaded,warnings=cad_import.read_dxf(path)
            self.assertEqual(loaded.group_members({0}),{0,1,2});self.assertTrue(any('Overlapping' in w for w in warnings))
