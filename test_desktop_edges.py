import unittest
from desktop_edges import snap_position


class DesktopEdgeTests(unittest.TestCase):
    def test_four_edges_and_center(self):
        area = (0, 0, 1920, 1040)
        for position, expected in [((10, 300), (0, 300, 'left')),
                                   ((1680, 300), (1700, 300, 'right')),
                                   ((700, 12), (700, 0, 'top')),
                                   ((700, 790), (700, 800, 'bottom')),
                                   ((700, 400), (700, 400, None))]:
            self.assertEqual(snap_position(*position, 220, 240, area), expected)

    def test_negative_monitor_and_taskbar(self):
        self.assertEqual(snap_position(-1900, 400, 220, 240, (-1920, 0, 0, 1040)), (-1920, 400, 'left'))
        self.assertEqual(snap_position(-600, 900, 220, 240, (-1920, 0, 0, 1040)), (-600, 800, 'bottom'))

    def test_corner_keeps_previous_pose_and_away_releases(self):
        area = (0, 0, 1920, 1040)
        self.assertEqual(snap_position(0, 0, 220, 240, area, 'top')[2], 'top')
        self.assertIsNone(snap_position(100, 100, 220, 240, area, 'left')[2])

    def test_offscreen_is_recoverable(self):
        x, y, edge = snap_position(-500, -500, 220, 240, (0, 0, 1920, 1040))
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)
