import asyncio
from typing import Dict, List, Tuple, cast

import overpy
from diskcache import Cache
from starsep_utils import downloadOverpassData

from configuration import OVERPASS_URL, cacheDirectory

overpassApi = overpy.Overpass(url=OVERPASS_URL)
cacheOverpass = Cache(str(cacheDirectory / "overpass"))


@cacheOverpass.memoize()
def fetchOverpassData(
    placeName: str,
    bbox: Tuple[float, float, float, float],
    admin_level: int,
) -> overpy.Result:
    (minLat, minLon, maxLat, maxLon) = bbox
    query = f"""
    [out:xml][timeout:250];
    area[admin_level={admin_level}][name="{placeName}"]->.searchArea;
    (
        nwr[amenity=bicycle_rental](area.searchArea);
        nwr[amenity=bicycle_rental]({minLat}, {minLon}, {maxLat}, {maxLon});
        nwr[amenity=bicycle_parking]["disused:amenity"=bicycle_rental](area.searchArea);
        nwr[amenity=bicycle_parking]["disused:amenity"=bicycle_rental]({minLat}, {minLon}, {maxLat}, {maxLon});
    );
    (._;>;);
    out body;
    """
    # TODO: remove overpy
    # overpassResult = asyncio.run(
    #     downloadOverpassData(
    #         query=query, overpassUrl=OVERPASS_URL, userAgent="starsep/NextbikeOSM"
    #     ),
    # )
    return overpassApi.query(query)


class OverpassParser:
    def __init__(self):
        self.ways: Dict[int, overpy.Way] = {}
        self.nodes: Dict[int, overpy.Node] = {}
        self.elements: List[overpy.Element] = []

    def fetchData(
        self, placeName: str, bbox: Tuple[float, float, float, float], admin_level: int
    ):
        data: overpy.Result = fetchOverpassData(placeName, bbox, admin_level)
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
