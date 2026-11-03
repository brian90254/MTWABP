import unittest
from cad_document import Document

class DuplicateTests(unittest.TestCase):
    def test_layer_copy_and_undo(self):
        d=Document()
        d.add([dict(type='line',a=[1,0],b=[2,0],locked=True,group='source')])
        d.toggle_layer('Layer1')
        before=d.state()
        self.assertEqual(d.duplicate_layer('Layer1'),'Layer1_copy')
        self.assertEqual(d.active,'Layer1_copy')
        self.assertTrue(d.visible(1))
        self.assertFalse(d.visible(0))
        self.assertTrue(d.objects[1]['locked'])
        self.assertNotEqual(d.objects[1]['group'],'source')
        self.assertEqual(d.duplicate_layer('Layer1'),'Layer1_copy2')
        d.undo();d.undo()
        self.assertEqual(d.state(),before)

    def test_polar_total_and_group_identity(self):
        d=Document()
        d.add([dict(type='line',a=[1,0],b=[2,0],group='g'),
               dict(type='circle',center=[3,0],radius=1,group='g')])
        before=d.state()
        d.polar_duplicate([0,0],4)
        self.assertEqual(len(d.objects),8)
        self.assertAlmostEqual(d.objects[2]['a'][0],0)
        self.assertAlmostEqual(d.objects[2]['a'][1],1)
        self.assertEqual(d.objects[2]['group'],d.objects[3]['group'])
        self.assertEqual(len({o['group'] for o in d.objects}),4)
        d.undo()
        self.assertEqual(d.state(),before)
