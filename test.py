from dataclasses import dataclass
from unittest import TestCase

from nextbike_valid import measure


@dataclass
class GeoPoint:
    lat: float
    lon: float


class MeasureTestCase(TestCase):
    def test_measure(self):
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
        for (pointA, pointB, distance) in testCases:
            self.assertAlmostEqual(measure(pointA, pointB), distance, places=2)
