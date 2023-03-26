import dataclasses
import difflib as SC
import json
from dataclasses import dataclass
from pathlib import Path
from time import localtime, strftime
from typing import List, Optional, Tuple

from jinja2 import Environment, PackageLoader
from overpy import Element, Way

import nextbike_parser as NP
from distance import GeoPoint, distance
from overpass_parser import OverpassParser

__VERSION__ = "3.0.0"

DISTANCE_THRESHOLD_MISMATCH = 100
MAX_DISTANCE = 1000000


@dataclass
class Match:
    distance: float
    nextbike: NP.Place
    osm: Element
    osmType: str
    matchedBy: str
    ratio: float = 0.0


@dataclass
class MapFeatureTags:
    name: str
    ref: str
    capacity: str
    extraTags: dict[str, str]

    def _toTagsDict(self) -> dict[str, str]:
        result = dict(name=self.name, ref=self.ref, capacity=self.capacity)
        result.update(self.extraTags)
        return result

    def toDescription(self) -> str:
        return "\n".join(self._keyValues())

    def toCSV(self) -> str:
        return ",".join(self._keyValues())

    def _keyValues(self) -> List[str]:
        return [f"{key}={value}" for key, value in self._toTagsDict().items()]


@dataclass
class MapFeature(GeoPoint):
    tags: MapFeatureTags

    @staticmethod
    def fromMatch(extraTags: dict[str, str]):
        def foo(match: Match) -> MapFeature:
            return MapFeature(
                lat=match.nextbike.lat,
                lon=match.nextbike.lon,
                tags=MapFeatureTags(
                    name=match.nextbike.name,
                    ref=match.nextbike.num,
                    capacity=match.nextbike.stands,
                    extraTags=extraTags,
                ),
            )

        return foo

    def toCSV(self) -> str:
        return f"{self.lat},{self.lon},addNode " + self.tags.toCSV()


class NextbikeValidator:
    def __init__(self, nextbikeData, osmParser, html=None):
        self.nextbikeData = nextbikeData
        self.osmParser: OverpassParser = osmParser
        self.matches: List[Match] = []
        self.html = html
        self.envir = Environment(loader=PackageLoader("nextbike_valid", "templates"))

    def matchViaRef(self, place: NP.Place) -> Tuple[Optional[Element], float]:
        nextbikeRef = place.num
        result = None
        bestDistance = MAX_DISTANCE
        for element in self.osmParser.elements:
            if "ref" in element.tags and element.tags["ref"] == nextbikeRef:
                point = GeoPoint.fromElement(element, self.osmParser)
                dist = distance(place, point)
                if dist < bestDistance:
                    bestDistance = dist
                    result = element
        return result, bestDistance

    def matchViaDistance(self, place: NP.Place) -> Tuple[Optional[Element], float]:
        bestDistance = MAX_DISTANCE
        best: Optional[Element] = None

        for element in self.osmParser.elements:
            if (
                "amenity" not in element.tags
                or element.tags["amenity"] != "bicycle_rental"
            ):
                continue
            point = GeoPoint.fromElement(element, self.osmParser)
            dist = distance(place, point)
            if dist < bestDistance:
                bestDistance = dist
                best = element
        return best, bestDistance

    def pair(self, nextPlaces: List[NP.Place]):
        data = []
        for nextPlace in nextPlaces:
            matchedElement, dist = self.matchViaRef(nextPlace)
            matchedBy = "id"
            if matchedElement is None:
                matchedElement, dist = self.matchViaDistance(nextPlace)
                matchedBy = "di"
            data.append(
                Match(
                    distance=dist,
                    nextbike=nextPlace,
                    osm=matchedElement,
                    osmType="way" if type(matchedElement) == Way else "node",
                    matchedBy=matchedBy,
                )
            )
        self.matches = data

    def generateHtml(self, outputPath: Path, mapPath: Optional[Path] = None):
        timestamp = strftime("%a, %d %b @ %H:%M:%S", localtime())
        template = self.envir.get_template("base.html")
        matches = []
        for match in self.matches:
            match.ratio = (
                SC.SequenceMatcher(
                    None, match.nextbike.name, match.osm.tags.get("name")
                ).ratio()
                if match.osm.tags.get("name") is not None
                else 0
            )
            matches.append(match)
        csvPath = outputPath.with_suffix(".csv")
        kmlPath = outputPath.with_suffix(".kml")
        with outputPath.open("w", encoding="utf-8") as f:
            context = {
                "matches": matches,
                "timestamp": timestamp,
                "VERSION": __VERSION__,
                "distanceThreshold": DISTANCE_THRESHOLD_MISMATCH,
                "mapLink": str(mapPath.name),
                "csvLink": str(csvPath.name),
                "kmlLink": str(kmlPath.name),
            }
            f.write(template.render(context))
        if mapPath is not None:
            networkTags = dict(
                amenity="bicycle_rental",
                operator="Nextbike Polska",
            )
            if "warszawa" in outputPath.name:  # TODO: move logic
                networkTags["bicycle_rental"] = "dropoff_point"
                networkTags["brand"] = "Veturilo"
                networkTags["brand:wikidata"] = "Q3847868"
                networkTags["network"] = "Veturilo"
                networkTags["network:wikidata"] = "Q3847868"
            mismatches = list(
                filter(lambda m: m.distance > DISTANCE_THRESHOLD_MISMATCH, matches)
            )
            mapFeatures = list(map(MapFeature.fromMatch(networkTags), mismatches))
            self.generateMap(mapPath, mapFeatures)
            self.generateCSV(csvPath, mapFeatures)
            self.generateKML(kmlPath, mapFeatures)

    def generateMap(self, mapPath: Path, mapFeatures: List[MapFeature]):
        mapFeaturesDict = list(map(dataclasses.asdict, mapFeatures))
        mapTemplate = self.envir.get_template("map.html")
        with mapPath.open("w", encoding="utf-8") as f:
            context = {"featuresJson": json.dumps(mapFeaturesDict)}
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


def _calculateBbox(data: List[NP.Place]) -> Tuple[float, float, float, float]:
    latLonEpsilon = 0.002
    return (
        min((place.lat for place in data)) - latLonEpsilon,
        min((place.lon for place in data)) - latLonEpsilon,
        max((place.lat for place in data)) + latLonEpsilon,
        max((place.lon for place in data)) + latLonEpsilon,
    )


def main(
    update: bool,
    network: str,
    osmAreaName: str,
    outputPath: Path,
    nextbikeParser: NP.NextbikeParser,
    mapPath: Optional[Path] = None,
):
    if update:
        NP.NextbikeParser.update()
        nextbikeParser.get_uids()
    overpassParser = OverpassParser()
    validator = NextbikeValidator(nextbikeParser, overpassParser)
    if network.isnumeric():
        nextbikeData = nextbikeParser.find_city(network)
    else:
        nextbikeData = nextbikeParser.find_network(network)
    overpassParser.fetchData(placeName=osmAreaName, bbox=_calculateBbox(nextbikeData))
    if validator.containsData(outputPath):
        validator.pair(nextbikeData)
        validator.generateHtml(outputPath, mapPath)
