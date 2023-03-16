from unittest import TestCase

from distance import GeoPoint, distance


class DistanceTestCase(TestCase):
    def test_distance(self):
        testCases = [
            (
                GeoPoint(lat=52.263298, lon=21.046161),
                GeoPoint(lat=52.2602571, lon=21.0468360),
                341.49,
            ),
            (
                GeoPoint(lat=52.263298, lon=21.046161),
                GeoPoint(lat=52.263298, lon=21.046161),
                0,
            ),
            (
                GeoPoint(lat=52.2157063, lon=20.9602140),
                GeoPoint(lat=52.205017, lon=21.168801),
                14307.62,
            ),
        ]
        for pointA, pointB, expected in testCases:
            self.assertAlmostEqual(distance(pointA, pointB), expected, places=2)
