"""Persistent group membership, selection, transforms, polygon explosion and closure."""
import copy
import unittest
try:import shapely
except ImportError:shapely=None
from cad_document import Document
from cad_import import merge
from cad_groups import is_closed
from cad_offset import offset


def rectangle():
    pts=[[0,0],[2,0],[2,2],[0,2]]
    return [dict(type='line',a=a,b=b) for a,b in zip(pts,pts[1:]+pts[:1])]

class GroupTests(unittest.TestCase):
    def drawing(self):
        d=Document();d.add(rectangle());return d
    def test_group_persistence_move_undo_and_copy_identities(self):
        d=self.drawing();before=d.state();d.group_selection();group=d.objects[0]['group']
        self.assertEqual({o['group'] for o in d.objects},{group});self.assertTrue(is_closed(d.objects))
        loaded=Document.from_payload(d.payload());self.assertEqual(loaded.objects,d.objects)
        d.selected={0};d.move_selection(3,4)
        for old,new in zip(before['objects'],d.objects):self.assertEqual(new['a'],[old['a'][0]+3,old['a'][1]+4])
        d.undo();self.assertEqual(d.objects[0]['a'],[0,0])
        d.selected={0};d.transform_selected('Move',copy_objects=True,dx=5,dy=0)
        self.assertEqual(len(d.objects),8);self.assertNotEqual(d.objects[4]['group'],group)
        self.assertEqual(d.group_members({4}),{4,5,6,7});self.assertEqual(d.group_members({0}),{0,1,2,3})
    def test_ungroup_polygons_edges_and_history(self):
        for closed,count in [(True,4),(False,3)]:
            d=Document();d.add([dict(type='polygon',points=[[0,0],[2,0],[2,2],[0,2]],closed=closed,color='#123456',weight=.02)])
            before=d.state();n=len(d.history);self.assertTrue(d.ungroup_selection())
            self.assertEqual(len(d.objects),count);self.assertEqual(len(d.history),n+1)
            self.assertTrue(all(o['type']=='line' and o['color']=='#123456' and o['weight']==.02 and 'group' not in o for o in d.objects))
            self.assertEqual(is_closed(d.objects),closed);d.undo();self.assertEqual(d.state(),before)
            d.redo();self.assertEqual(len(d.objects),count)
    def test_merge_groups_and_ungroup_with_polygon(self):
        d=self.drawing();d.selected={0,1};d.group_selection();d.selected={2,3};d.group_selection()
        d.selected={0,2};d.group_selection();self.assertEqual(len({o['group'] for o in d.objects}),1)
        d.selected={0};self.assertTrue(d.ungroup_selection());self.assertFalse(any(o.get('group') for o in d.objects))
        self.assertEqual(d.selected,{0,1,2,3})
        d.add([dict(type='polygon',points=[[4,0],[5,0],[5,1]],closed=True)])
        d.selected={0,4};d.group_selection();d.ungroup_selection();self.assertEqual(len(d.objects),7)
    def test_native_import_remaps_group_ids_each_time(self):
        source=self.drawing();source.group_selection();target=Document()
        merge(target,source);merge(target,source)
        ids={target.objects[i]['group'] for i in (0,4)}
        self.assertEqual(len(ids),2);self.assertNotIn(source.objects[0]['group'],ids)
        self.assertEqual(target.group_members({0}),{0,1,2,3})
    def test_window_whole_group_and_no_partial_handles(self):
        d=self.drawing();d.group_selection();d.clear_selection()
        d.select_window([-.1,-.1],[2.1,.1]);self.assertFalse(d.selected);self.assertFalse(d.point_selection)
        d.select_window([-.1,-.1],[2.1,2.1]);self.assertEqual(d.selected,{0,1,2,3})
    def test_hidden_members_move_and_locked_member_blocks_whole_group(self):
        d=self.drawing();d.add_layer('Hidden');d.objects[1]['layer']='Hidden';d.group_selection();d.toggle_layer('Hidden')
        d.selected={0};d.move_selection(1,0);self.assertEqual(d.objects[1]['a'],[3,0])
        d.objects[1]['locked']=True;before=d.state();self.assertFalse(d.move_selection(2,0));self.assertEqual(d.state(),before)
        with self.assertRaises(ValueError):d.ungroup_selection()
    def test_closed_is_geometry_based_not_group_flag(self):
        objects=rectangle();self.assertTrue(is_closed(objects));self.assertFalse(is_closed(objects[:-1]))
        objects[1]['a']=[2.01,0];self.assertFalse(is_closed(objects))
        self.assertTrue(is_closed([dict(type='circle',center=[0,0],radius=1)]))
        self.assertFalse(is_closed([dict(type='line',a=[0,0],b=[1,0],group='anything')]))
        self.assertFalse(is_closed(rectangle()+[dict(type='line',a=[0,0],b=[-1,0])]))
        self.assertFalse(is_closed(rectangle()+[dict(o,a=[v+5 for v in o['a']],b=[v+5 for v in o['b']]) for o in rectangle()]))
    @unittest.skipUnless(shapely,'Optional Shapely is required')
    def test_grouped_rectangle_offsets_as_closed_boundary(self):
        d=self.drawing();d.group_selection();result,approx=offset(d.objects,.25,[1,1])
        self.assertFalse(approx);self.assertTrue(result[0]['closed']);self.assertTrue(is_closed(result))
    def test_closed_arcs_and_grouped_chamfer_remain_one_loop(self):
        import math
        arcs=[dict(type='arc',center=[0,0],radius=1,start=start,sweep=math.pi) for start in (0,math.pi)]
        self.assertTrue(is_closed(arcs))
        d=self.drawing();d.group_selection();group=d.objects[0]['group']
        d.chamfer_objects(0,1,[1,0],[2,1],.25)
        self.assertTrue(all(o.get('group')==group for o in d.objects));self.assertTrue(is_closed(d.objects))
    def test_invalid_group_data_and_noop(self):
        d=Document();d.add([dict(type='circle',center=[0,0],radius=1)])
        for invalid in ([],123,''):
            with self.assertRaises(ValueError):d.prepare(dict(d.objects[0],group=invalid))
        before=d.state();self.assertFalse(d.ungroup_selection());self.assertEqual(d.state(),before)
