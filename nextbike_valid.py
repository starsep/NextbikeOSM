import difflib as SC
import json
from dataclasses import dataclass
from pathlib import Path
from time import localtime, strftime
from typing import cast

from jinja2 import Environment, PackageLoader
from starsep_utils import Element, GeoPoint, OverpassResult, Way, haversine

import nextbike_parser as NP
from geodesk_source import geodesk_bicycle_rentals
from overpass_parser import fetchOverpassData

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

    def _keyValues(self) -> list[str]:
        return [f"{key}={value}" for key, value in self._toTagsDict().items()]


@dataclass(frozen=True)
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

    def toJSON(self) -> dict:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "tags": self.tags._toTagsDict(),
        }


class NextbikeValidator:
    def __init__(self, nextbikeData, overpassResult: OverpassResult, html=None):
        self.nextbikeData = nextbikeData
        self.overpassResult = overpassResult
        self.matches: list[Match] = []
        self.html = html
        self.envir = Environment(loader=PackageLoader("nextbike_valid", "templates"))
        self.refMatches = dict()

    def matchViaRef(self, place: NP.Place) -> tuple[Element | None, float]:
        nextbikeRef = place.num
        if nextbikeRef not in self.refMatches:
            self.refMatches[nextbikeRef] = list()
        result = None
        bestDistance = MAX_DISTANCE
        for element in self.overpassResult.allElements():
            if "ref" in element.tags and element.tags["ref"] == nextbikeRef:
                self.refMatches[nextbikeRef].append(
                    [element, "way" if type(element) is Way else "node"]
                )
                point = element.center(self.overpassResult)
                dist = haversine(place, point)
                if dist < bestDistance:
                    bestDistance = dist
                    result = element
        return result, bestDistance

    def matchViaDistance(self, place: NP.Place) -> tuple[Element | None, float]:
        bestDistance = MAX_DISTANCE
        best: Element | None = None

        for element in self.overpassResult.allElements():
            if (
                "amenity" not in element.tags
                or element.tags["amenity"] != "bicycle_rental"
            ):
                continue
            point = element.center(self.overpassResult)
            dist = haversine(place, point)
            if dist < bestDistance:
                bestDistance = dist
                best = element
        return best, bestDistance

    def pair(self, nextPlaces: list[NP.Place]):
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
                    osmType="way" if type(matchedElement) is Way else "node",
                    matchedBy=matchedBy,
                )
            )
        self.matches = data

    def generateHtml(self, outputPath: Path, mapPath: Path, cityName: str):
        timestamp = strftime("%a, %d %b @ %H:%M:%S", localtime())
        template = self.envir.get_template("nextbike.html")
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
        with outputPath.open("w", encoding="utf-8") as f:
            context = {
                "matches": matches,
                "timestamp": timestamp,
                "countMismatches": len(mapFeatures),
                "VERSION": __VERSION__,
                "distanceThreshold": DISTANCE_THRESHOLD_MISMATCH,
                "cityName": cityName,
                "mapLink": str(mapPath.name),
                "csvLink": str(csvPath.name),
                "kmlLink": str(kmlPath.name),
                "refDuplicates": {
                    ref: duplicates
                    for ref, duplicates in self.refMatches.items()
                    if len(duplicates) > 1
                },
            }
            f.write(template.render(context))
        self.generateMap(mapPath, mapFeatures, cityName)
        self.generateCSV(csvPath, mapFeatures)
        self.generateKML(kmlPath, mapFeatures)

    def generateMap(self, mapPath: Path, mapFeatures: list[MapFeature], cityName: str):
        mapFeaturesDict = list(map(lambda q: q.toJSON(), mapFeatures))
        mapTemplate = self.envir.get_template("map.html")
        with mapPath.open("w", encoding="utf-8") as f:
            context = {
                "featuresJson": json.dumps(mapFeaturesDict),
                "cityName": cityName,
            }
            f.write(mapTemplate.render(context))

    @staticmethod
    def generateCSV(csvPath: Path, mapFeatures: list[MapFeature]):
        with csvPath.open("w") as f:
            for feature in mapFeatures:
                f.write(feature.toCSV() + "\n")

    def generateKML(self, kmlPath: Path, mapFeatures: list[MapFeature]):
        kmlTemplate = self.envir.get_template("station.kml")
        with kmlPath.open("w", encoding="utf-8") as f:
            context = {"features": mapFeatures}
            f.write(kmlTemplate.render(context))

    def containsData(self, path: Path):
        timek = strftime("%a, %d %b @ %H:%M:%S", localtime())
        if len(self.overpassResult.nodes) == 0 and len(self.overpassResult.ways) == 0:
            template = self.envir.get_template("empty.html")
            fill_template = template.render({"last": timek})
            with path.open("w", encoding="utf-8") as f:
                f.write(fill_template)
            print(f"{path}: OSM Data not found!")
            return False
        return True


def _calculateBbox(data: list[NP.Place]) -> tuple[float, float, float, float]:
    latLonEpsilon = 0.002
    return (
        min(place.lat for place in data) - latLonEpsilon,
        min(place.lon for place in data) - latLonEpsilon,
        max(place.lat for place in data) + latLonEpsilon,
        max(place.lon for place in data) + latLonEpsilon,
    )


def nextbike_run(
    update: bool,
    network: str,
    cityName: str,
    outputPath: Path,
    nextbikeParser: NP.NextbikeParser,
    mapPath: Path | None = None,
):
    if update:
        NP.NextbikeParser.update()
        nextbikeParser.get_uids()
    if network.isnumeric():
        nextbikeData = nextbikeParser.find_city(network)
    else:
        nextbikeData = nextbikeParser.find_network(network)
    geodesk_bicycle_rentals(
        place_name=cityName, bbox=_calculateBbox(nextbikeData), admin_level=8
    )  # TODO: use geodesk result
    overpassResult = fetchOverpassData(
        placeName=cityName, bbox=_calculateBbox(nextbikeData), admin_level=8
    )
    validator = NextbikeValidator(nextbikeParser, overpassResult)
    if validator.containsData(outputPath):
        validator.pair(nextbikeData)
        validator.generateHtml(outputPath, mapPath, cityName)
