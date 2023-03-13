from dataclasses import dataclass
from typing import cast

from overpy import Element, Node, Way
from pyproj import Geod

from overpass_parser import OverpassParser

wgs84Geod = Geod(ellps="WGS84")


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


def distance(pointA: GeoPoint, pointB: GeoPoint):
    return round(
        wgs84Geod.inv(pointA.lon, pointA.lat, pointB.lon, pointB.lat)[2],
        ndigits=2,
    )
