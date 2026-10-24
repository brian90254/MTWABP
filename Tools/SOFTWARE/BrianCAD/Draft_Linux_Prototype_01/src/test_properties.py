"""Shared schemas, sparse property updates and atomic mixed-object validation."""
import copy
import unittest
from cad_document import Document
from cad_properties import common, values, apply_changes


class PropertiesTests(unittest.TestCase):
    def setUp(self):
        self.d=Document()
        self.d.add([{'type':'line','a':[0,0],'b':[2,1]},
                    {'type':'circle','center':[3,4],'radius':1},
                    {'type':'arc','center':[5,6],'radius':2,'start':0,'sweep':1}])

    def test_only_shared_properties_and_sparse_style_edits(self):
        line,circle,arc=self.d.objects
        self.assertEqual(set(common([line,circle])),{'layer','color','locked','pattern','weight','controls'})
        self.assertIn('diameter',common([circle,arc])); self.assertNotIn('sweep',common([circle,arc]))
        before=copy.deepcopy(self.d.objects)
        updates={i:apply_changes(o,{'color':'Blue','weight':''}) for i,o in enumerate(before)}
        self.d.commit_updates(updates)
        for original,updated in zip(before,self.d.objects):
            expected=copy.deepcopy(original); expected['color']='#2465d8'
            self.assertEqual(updated,expected)
        self.assertEqual(values(circle)['diameter'],2)

    def test_shared_geometry_preserves_unedited_values_and_noop(self):
        before=self.d.state(); n=len(self.d.history)
        self.assertFalse(self.d.commit_updates({i:apply_changes(o,{}) for i,o in enumerate(self.d.objects)}))
        self.assertEqual(self.d.state(),before); self.assertEqual(len(self.d.history),n)
        updates={i:apply_changes(self.d.objects[i],{'diameter':'6'}) for i in (1,2)}
        self.d.commit_updates(updates)
        self.assertEqual(self.d.objects[1]['radius'],3); self.assertEqual(self.d.objects[2]['radius'],3)
        self.assertEqual(self.d.objects[1]['center'],[3,4]); self.assertEqual(self.d.objects[2]['center'],[5,6])
        self.d.undo(); self.assertEqual(self.d.state(),before)

    def test_invalid_one_of_many_keeps_all_objects_and_history(self):
        d=Document(); d.add([{'type':'polygon','points':[[0,0],[1,0],[0,1]]},
                            {'type':'spline','method':'through','closed':False,'points':[[0,0],[1,1]]}])
        before=d.state(); n=len(d.history)
        updates={i:apply_changes(o,{'points':'0,0; 1,1'}) for i,o in enumerate(d.objects)}
        with self.assertRaises(ValueError): d.commit_updates(updates)
        self.assertEqual(d.state(),before); self.assertEqual(len(d.history),n)


if __name__=='__main__': unittest.main()
