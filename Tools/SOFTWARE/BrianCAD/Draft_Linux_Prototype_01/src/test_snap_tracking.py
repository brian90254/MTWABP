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
                      'horizontal','45°','on line','on curve','on object','']:
            h.remember([10,20],label)
            self.assertEqual(h.points,[[2,3]])

    def test_axes_tolerance_zoom_dedup_and_no_cursor(self):
        h=SnapHistory(); h.remember([2,3],'endpoint'); h.remember([2,8],'endpoint')
        self.assertEqual(h.guides([2.04,3.04],100),[(0,2),(1,3)])
        self.assertEqual(h.guides([2.04,3.04],200),[])
        self.assertEqual(h.guides([2,8],100),[(0,2),(1,8)])
        self.assertEqual(h.guides(None,100),[])


if __name__=='__main__': unittest.main()
