from dataclasses import dataclass
from typing import cast

from overpy import Element, Node, Way

from overpass_parser import OverpassParser

from math import sin, cos, sqrt, atan2, radians


@dataclass
class GeoPoint:
    lat: float
    lon: float

    @staticmethod
    def fromElement(element: Element, overpassParser: OverpassParser):
        if type(element) == Node:
            node = cast(Node, element)
            return GeoPoint(lat=node.lat, lon=node.lon)
        if type(element) == Way:
            way = cast(Way, element)
            nodes = [node for node in overpassParser.ways[way.id].nodes]
            centerLat = sum(map(lambda x: x.lat, nodes)) / len(nodes)
            centerLon = sum(map(lambda x: x.lon, nodes)) / len(nodes)
            return GeoPoint(lat=centerLat, lon=centerLon)


def distance(point: GeoPoint, other: GeoPoint) -> float:
    R = 6373.0
    lon1, lat1, lon2, lat2 = map(radians, [point.lon, point.lat, other.lon, other.lat])

    deltaLon = lon2 - lon1
    deltaLat = lat2 - lat1
    a = (sin(deltaLat / 2)) ** 2 + cos(lat1) * cos(lat2) * (sin(deltaLon / 2)) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return int(R * c * 1000)
