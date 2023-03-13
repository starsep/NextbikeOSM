from typing import List, Dict

from diskcache import Cache
import overpy
from configuration import OVERPASS_URL, cacheDirectory

overpassApi = overpy.Overpass(url=OVERPASS_URL)
cacheOverpass = Cache(str(cacheDirectory / "overpass"))


@cacheOverpass.memoize()
def fetchOverpassData(placeName: str) -> overpy.Result:
    query = f"""
    [out:xml][timeout:250];
    area[admin_level=6][name="{placeName}"]->.searchArea;
    (
        nwr[amenity=bicycle_rental](area.searchArea);
    );
    (._;>;);
    out body;
    """
    return overpassApi.query(query)


class OverpassParser:
    def __init__(self, placeName: str):
        self.data: overpy.Result = fetchOverpassData(placeName)
        self.ways: Dict[int, overpy.Way] = {way.id: way for way in self.data.ways}
        self.nodes: Dict[int, overpy.Node] = {node.id: node for node in self.data.nodes}
        self.elements: List[overpy.Element] = list(self.nodes.values()) + list(
            self.ways.values()
        )

    def find(self, iD: int, mode: str = "n"):
        if mode == "n":
            return self.nodes.get(iD)
        elif mode == "w":
            return self.ways.get(iD)
        return None
