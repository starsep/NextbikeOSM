import asyncio

from diskcache import Cache
from starsep_utils import OverpassResult, downloadOverpassData

from configuration import OVERPASS_URL, cacheDirectory

cacheOverpass = Cache(str(cacheDirectory / "overpass"))


@cacheOverpass.memoize()
def fetchOverpassData(
    placeName: str,
    bbox: tuple[float, float, float, float],
    admin_level: int,
) -> OverpassResult:
    (minLat, minLon, maxLat, maxLon) = bbox
    query = f"""
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
    return asyncio.run(
        downloadOverpassData(
            query=query, overpassUrl=OVERPASS_URL, userAgent="starsep/NextbikeOSM"
        ),
    )
