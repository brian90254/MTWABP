"""Recent object snaps: bounded unique history and zoom-independent guides."""
import unittest
from snap_tracking import SnapHistory, OBJECT_SNAPS


class SnapTrackingTests(unittest.TestCase):
    def test_four_distinct_points_most_recent_first(self):
        h=SnapHistory()
        for i in range(5): h.remember([i,i+10],'quadrant')
        self.assertEqual(h.points,[[4,14],[3,13],[2,12],[1,11]])
        h.remember([2,12],'tangent')
        self.assertEqual(h.points,[[2,12],[4,14],[3,13],[1,11]])
        h.clear(); self.assertEqual(h.points,[])

    def test_eligible_snaps_only_and_copy_coordinates(self):
        h=SnapHistory()
        for label in OBJECT_SNAPS:
            point=[2,3]; h.remember(point,label); point[0]=99
            self.assertEqual(h.points,[[2,3]])
        for label in ['line/grid intersection','origin','grid intersection','horizontal grid line','vertical',
                      'horizontal','align x','align y','align x + align y','45°','on line','on curve','on object','']:
            h.remember([10,20],label)
            self.assertEqual(h.points,[[2,3]])

    def test_snap_preserves_free_axis_and_combines_coordinates(self):
        h=SnapHistory(); h.remember([2,7],'endpoint'); h.remember([5,3],'quadrant')
        self.assertEqual(h.snap([2.04,9],100),([2,9],'align x'))
        self.assertEqual(h.snap([9,3.04],100),([9,3],'align y'))
        self.assertEqual(h.snap([2.04,3.04],100),([2,3],'align x + align y'))
        self.assertIsNone(h.snap([2.04,3.04],200))
        h.remember([2.05,9],'endpoint')
        self.assertEqual(h.snap([2.04,4],100),([2.05,4],'align x'))

    def test_generator_priority_toggle_and_excluded_sources(self):
        from test_grid import editor
        a=editor(); a.snap_history=SnapHistory()
        a.snap_history.remember([.27,4],'endpoint')
        self.assertEqual(a.snap_point([.26,.51]),([.27,.5],'align x / grid intersection'))
        a.snap.set(False)
        self.assertEqual(a.snap_point([.26,.51]),([.25,.5],'grid intersection'))
        a.snap.set(True)
        a.doc.add([{'type':'line','a':[.28,.52],'b':[2,2]}])
        self.assertEqual(a.snap_point([.26,.51]),([.28,.52],'endpoint'))
        self.assertEqual(a.snap_history.snap([.26,.51],100,exclude=[[.27,4]]),None)
        self.assertEqual(a.snap_history.guides([.26,.51],100,exclude=[[.27,4]]),[])

    def test_axes_tolerance_zoom_dedup_and_no_cursor(self):
        h=SnapHistory(); h.remember([2,3],'endpoint'); h.remember([2,8],'endpoint')
        self.assertEqual(h.guides([2.04,3.04],100),[(0,2),(1,3)])
        self.assertEqual(h.guides([2.04,3.04],200),[])
        self.assertEqual(h.guides([2,8],100),[(0,2),(1,8)])
        self.assertEqual(h.guides(None,100),[])


if __name__=='__main__': unittest.main()
