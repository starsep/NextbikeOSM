import dataclasses
import difflib as SC
import json
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from time import localtime, strftime
from typing import Dict, List, Optional, Tuple

from jinja2 import Environment, PackageLoader
from overpy import Element, Way
from starsep_utils import GeoPoint, haversine

from mevo_parser import MevoParser, Station
from overpass_parser import OverpassParser

DISTANCE_THRESHOLD_MISMATCH = 100
MAX_DISTANCE = 1000000
OSM_URL = "https://osm.org"
JOSM_URL = "http://localhost:8111"


def mevoNetworkTags():
    # Should match https://nsi.guide/index.html?t=brands&k=amenity&v=bicycle_rental&tt=mevo
    networkTags = dict(
        amenity="bicycle_rental",
        brand="MEVO",
        network="MEVO",
        operator="CityBike Global",
        opening_hours="24/7",
    )
    networkTags["brand:wikidata"] = "Q60860236"
    networkTags["network:wikidata"] = "Q60860236"
    return networkTags


@dataclass
class Match:
    distance: float
    place: Station
    osm: Element
    osmType: str
    ratio: float = 0.0

    @property
    def osmMarkLink(self):
        return f"{OSM_URL}?mlat={self.place.lat}&mlon={self.place.lon}#map=19/{self.place.lat}/{self.place.lon}"

    @property
    def josmAreaLink(self):
        return f"{JOSM_URL}/load_and_zoom?top={self.place.lat}&bottom={self.place.lat}&left={self.place.lon}&right={self.place.lon}"

    @property
    def osmLink(self):
        return f"{OSM_URL}/{self.osmType}/{self.osm.id}"

    @property
    def josmLink(self):
        return f"{JOSM_URL}/load_object?objects={self.osmType[0]}{self.osm.id}"

    @property
    def tags(self) -> dict[str, str]:
        result = mevoNetworkTags()
        result["ref:mevo"] = self.place.ref
        result["ref"] = ""
        result["name"] = "MEVO " + self.place.name
        result["capacity"] = str(self.place.capacity)
        return result

    @property
    def josmTags(self):
        return urllib.parse.quote_plus(
            "|".join([f"{key}={value}" for key, value in self.tags.items()])
        )

    @property
    def addJosmLink(self):
        return f"{JOSM_URL}/add_node?lon={self.place.lon}&lat={self.place.lat}&addtags={self.josmTags}"

    @property
    def updateJosmLink(self):
        result = f"{JOSM_URL}/load_object?objects={self.osmType[0]}{self.osm.id}&lon={self.place.lon}&lat={self.place.lat}&addtags={self.josmTags}"
        if "disused:amenity" in self.osm.tags:
            result += "%7Cdisused:amenity="
        return result


@dataclass
class MapFeatureTags:
    name: str
    extraTags: Dict[str, str]

    def _toTagsDict(self) -> Dict[str, str]:
        result = dict(name=self.name)
        result.update(self.extraTags)
        return result

    def toDescription(self) -> str:
        return "\n".join(self._keyValues())

    def toCSV(self) -> str:
        return ",".join(self._keyValues())

    def _keyValues(self) -> List[str]:
        return [f"{key}={value}" for key, value in self._toTagsDict().items()]


@dataclass(frozen=True)
class MapFeature(GeoPoint):
    tags: MapFeatureTags

    @staticmethod
    def fromMatch(extraTags: Dict[str, str]):
        def foo(match: Match) -> MapFeature:
            return MapFeature(
                lat=match.place.lat,
                lon=match.place.lon,
                tags=MapFeatureTags(
                    name=match.place.name,
                    extraTags=extraTags,
                ),
            )

        return foo

    def toCSV(self) -> str:
        return f"{self.lat},{self.lon},addNode " + self.tags.toCSV()


class MevoComparator:
    def __init__(self, data, osmParser, html=None):
        self.data = data
        self.osmParser: OverpassParser = osmParser
        self.matches: List[Match] = []
        self.html = html
        self.envir = Environment(loader=PackageLoader("mevo_comparator", "templates"))

    def matchViaDistance(self, place: Station) -> Tuple[Optional[Element], float]:
        bestDistance = MAX_DISTANCE
        best: Optional[Element] = None

        for element in self.osmParser.elements:
            if "amenity" not in element.tags:
                continue
            if element.tags["amenity"] not in ["bicycle_rental", "bicycle_parking"]:
                continue
            if element.tags["amenity"] == "bicycle_parking" and (
                "disused:amenity" not in element.tags
                or element.tags["disused:amenity"] != "bicycle_rental"
            ):
                continue
            point = GeoPoint.fromElement(element, self.osmParser)
            dist = haversine(place, point)
            if dist < bestDistance:
                bestDistance = dist
                best = element
        return best, bestDistance

    def pair(self, places: List[Station]):
        data = []
        for place in places:
            matchedElement, dist = self.matchViaDistance(place)
            data.append(
                Match(
                    distance=dist,
                    place=place,
                    osm=matchedElement,
                    osmType="way" if type(matchedElement) is Way else "node",
                )
            )
        self.matches = data

    def generateHtml(self, outputPath: Path, mapPath: Path, cityName: str):
        timestamp = strftime("%a, %d %b @ %H:%M:%S", localtime())
        template = self.envir.get_template("mevo.html")
        matches = []
        for match in self.matches:
            match.ratio = (
                SC.SequenceMatcher(
                    None,
                    match.place.name,
                    match.osm.tags.get("name").replace("MEVO ", ""),
                ).ratio()
                if match.osm.tags.get("name") is not None
                else 0
            )
            matches.append(match)
        csvPath = outputPath.with_suffix(".csv")
        kmlPath = outputPath.with_suffix(".kml")
        mismatches = list(
            filter(lambda m: m.distance > DISTANCE_THRESHOLD_MISMATCH, matches)
        )
        mapFeatures = list(map(MapFeature.fromMatch(mevoNetworkTags()), mismatches))
        with outputPath.open("w", encoding="utf-8") as f:
            context = {
                "matches": matches,
                "timestamp": timestamp,
                "countMismatches": len(mapFeatures),
                "distanceThreshold": DISTANCE_THRESHOLD_MISMATCH,
                "cityName": cityName,
                "mapLink": str(mapPath.name),
                "csvLink": str(csvPath.name),
                "kmlLink": str(kmlPath.name),
            }
            f.write(template.render(context))
        self.generateMap(mapPath, mapFeatures, cityName)
        self.generateCSV(csvPath, mapFeatures)
        self.generateKML(kmlPath, mapFeatures)

    def generateMap(self, mapPath: Path, mapFeatures: List[MapFeature], cityName: str):
        mapFeaturesDict = list(map(dataclasses.asdict, mapFeatures))
        mapTemplate = self.envir.get_template("map.html")
        with mapPath.open("w", encoding="utf-8") as f:
            context = {
                "featuresJson": json.dumps(mapFeaturesDict),
                "cityName": cityName,
            }
            f.write(mapTemplate.render(context))

    @staticmethod
    def generateCSV(csvPath: Path, mapFeatures: List[MapFeature]):
        with csvPath.open("w") as f:
            for feature in mapFeatures:
                f.write(feature.toCSV() + "\n")

    def generateKML(self, kmlPath: Path, mapFeatures: List[MapFeature]):
        kmlTemplate = self.envir.get_template("station.kml")
        with kmlPath.open("w", encoding="utf-8") as f:
            context = {"features": mapFeatures}
            f.write(kmlTemplate.render(context))

    def containsData(self, path: Path):
        timek = strftime("%a, %d %b @ %H:%M:%S", localtime())
        if len(self.osmParser.nodes) == 0 and len(self.osmParser.ways) == 0:
            template = self.envir.get_template("empty.html")
            fill_template = template.render({"last": timek})
            with path.open("w", encoding="utf-8") as f:
                f.write(fill_template)
            print(f"{path}: OSM Data not found!")
            return False
        return True


def _calculateBbox(data: List[Station]) -> Tuple[float, float, float, float]:
    if len(data) == 0:
        return 0, 0, 0, 0
    latLonEpsilon = 0.002
    return (
        min((place.lat for place in data)) - latLonEpsilon,
        min((place.lon for place in data)) - latLonEpsilon,
        max((place.lat for place in data)) + latLonEpsilon,
        max((place.lon for place in data)) + latLonEpsilon,
    )


def mevo_run(
    outputPath: Path,
    mevoParser: MevoParser,
    mapPath: Optional[Path] = None,
):
    overpassParser = OverpassParser()
    validator = MevoComparator(mevoParser, overpassParser)
    mevoData = mevoParser.downloadNetwork()
    name = "województwo pomorskie"
    overpassParser.fetchData(
        placeName=name, bbox=_calculateBbox(mevoData), admin_level=4
    )
    if validator.containsData(outputPath):
        validator.pair(mevoData)
        validator.generateHtml(outputPath, mapPath, name)
