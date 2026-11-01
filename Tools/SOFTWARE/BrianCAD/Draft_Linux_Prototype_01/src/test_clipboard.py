"""Clipboard snapshots, anchor-relative copies and atomic layer/group placement."""
import copy
import json
import unittest
from cad_document import Document
from cad_clipboard import snapshot,encode,decode,place

class ClipboardTests(unittest.TestCase):
    def source(self):
        d=Document();d.add_layer('Ramps');d.add([dict(type='line',a=[1,2],b=[4,2],layer='Ramps',color='#123456',weight=.02),
                  dict(type='circle',center=[4,4],radius=1,layer='Ramps')]);d.group_selection();return d
    def test_snapshot_anchor_is_frozen_and_does_not_edit_source(self):
        d=self.source();before=d.state();history=copy.deepcopy(d.history);selection=set(d.selected)
        data=snapshot(d,{0},[4.01,2.01]);self.assertEqual(data['anchor'],[4,2]);self.assertEqual(len(data['drawing']['objects']),2)
        self.assertEqual(d.state(),before);self.assertEqual(d.history,history);self.assertEqual(d.selected,selection)
        d.objects[0]['a']=[999,999];self.assertEqual(data['drawing']['objects'][0]['a'],[1,2])
        self.assertEqual(decode(encode(data))['anchor'],[4,2])
    def test_place_layers_styles_groups_independent_each_time_and_undo(self):
        source=self.source();data=decode(encode(snapshot(source,{0},[1,2])));target=Document()
        before=target.state();saved=copy.deepcopy(target.saved);n=len(target.history)
        self.assertEqual(place(target,data,[10,20]),2)
        self.assertEqual(target.objects[0]['a'],[10,20]);self.assertEqual(target.objects[1]['center'],[13,22])
        self.assertEqual(target.objects[0]['color'],'#123456');self.assertEqual(target.objects[0]['weight'],.02)
        self.assertEqual(target.objects[0]['layer'],'Ramps');self.assertIn('Ramps',[l['name'] for l in target.layers])
        self.assertNotEqual(target.objects[0]['group'],source.objects[0]['group']);self.assertEqual(target.saved,saved)
        self.assertEqual(len(target.history),n+1);target.undo();self.assertEqual(target.state(),before)
        target.redo();first=target.objects[0]['group'];place(target,data,[0,0]);self.assertNotEqual(first,target.objects[2]['group'])
        self.assertEqual(target.group_members({2}),{2,3})
    def test_partial_owner_invalid_clipboard_and_failed_placement(self):
        d=Document();d.add([dict(type='line',a=[0,0],b=[2,0])]);d.selected=set();d.point_selection={0:{'a'}}
        data=snapshot(d,set(d.point_selection));self.assertEqual(len(data['drawing']['objects']),1)
        for text in ('plain text','{}',json.dumps({'format':'briancad-clipboard-1','anchor':[0,0],'drawing':{}})):
            with self.assertRaises(ValueError):decode(text)
        target=Document();before=target.state()
        with self.assertRaises(ValueError):place(target,data,[float('nan'),0])
        self.assertEqual(target.state(),before);self.assertFalse(target.history)
    def test_existing_layer_visibility_is_preserved(self):
        d=self.source();target=Document();target.add_layer('Ramps');target.toggle_layer('Ramps')
        place(target,decode(encode(snapshot(d,{0}))),[0,0])
        self.assertFalse(next(l for l in target.layers if l['name']=='Ramps')['visible'])
        self.assertEqual([l['name'] for l in target.layers].count('Ramps'),1)
