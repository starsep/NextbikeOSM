from typing import Dict, List, cast, Tuple

import overpy
from diskcache import Cache

from configuration import OVERPASS_URL, cacheDirectory

overpassApi = overpy.Overpass(url=OVERPASS_URL)
cacheOverpass = Cache(str(cacheDirectory / "overpass"))


@cacheOverpass.memoize()
def fetchOverpassData(placeName: str, bbox: Tuple[float, float, float, float]) -> overpy.Result:
    (minLat, minLon, maxLat, maxLon) = bbox
    query = f"""
    [out:xml][timeout:250];
    area[admin_level=8][name="{placeName}"]->.searchArea;
    (
        nwr[amenity=bicycle_rental](area.searchArea);
        nwr[amenity=bicycle_rental]({minLat}, {minLon}, {maxLat}, {maxLon});
    );
    (._;>;);
    out body;
    """
    return overpassApi.query(query)


class OverpassParser:
    def __init__(self):
        self.ways: Dict[int, overpy.Way] = {}
        self.nodes: Dict[int, overpy.Node] = {}
        self.elements: List[overpy.Element] = []

    def fetchData(self, placeName: str, bbox: Tuple[float, float, float, float]):
        data: overpy.Result = fetchOverpassData(placeName, bbox)
        self.ways = {way.id: way for way in data.ways}
        self.nodes: Dict[int, overpy.Node] = {node.id: node for node in data.nodes}
        self.elements: List[overpy.Element] = cast(
            List[overpy.Element], list(self.nodes.values())
        ) + list(self.ways.values())

    def find(self, iD: int, mode: str = "n"):
        if mode == "n":
            return self.nodes.get(iD)
        elif mode == "w":
            return self.ways.get(iD)
        return None
