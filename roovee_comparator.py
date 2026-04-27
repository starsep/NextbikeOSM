import dataclasses
import difflib as SC
import json
from dataclasses import dataclass
from pathlib import Path
from time import localtime, strftime

from jinja2 import Environment, PackageLoader
from starsep_utils import Element, GeoPoint, OverpassResult, Way, haversine

from overpass_parser import fetchOverpassData
from roovee_parser import Place, RooveeNetwork, RooveeParser

DISTANCE_THRESHOLD_MISMATCH = 100
MAX_DISTANCE = 1000000


@dataclass
class Match:
    distance: float
    place: Place
    osm: Element
    osmType: str
    ratio: float = 0.0


@dataclass
class MapFeatureTags:
    name: str
    extraTags: dict[str, str]

    def _toTagsDict(self) -> dict[str, str]:
        result = dict(name=self.name)
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


class RooveeComparator:
    def __init__(self, data, overpassResult: OverpassResult, html=None):
        self.data = data
        self.overpassResult = overpassResult
        self.matches: list[Match] = []
        self.html = html
        self.envir = Environment(loader=PackageLoader("roovee_comparator", "templates"))

    def matchViaDistance(self, place: Place) -> tuple[Element | None, float]:
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

    def pair(self, places: list[Place]):
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
        template = self.envir.get_template("base.html")
        matches = []
        for match in self.matches:
            match.ratio = (
                SC.SequenceMatcher(
                    None, match.place.name, match.osm.tags.get("name")
                ).ratio()
                if match.osm.tags.get("name") is not None
                else 0
            )
            matches.append(match)
        csvPath = outputPath.with_suffix(".csv")
        kmlPath = outputPath.with_suffix(".kml")
        networkTags = dict(
            amenity="bicycle_rental",
            operator="Roovee",
        )
        networkTags["operator:wikidata"] = "Q60860205"
        mismatches = list(
            filter(lambda m: m.distance > DISTANCE_THRESHOLD_MISMATCH, matches)
        )
        mapFeatures = list(map(MapFeature.fromMatch(networkTags), mismatches))
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

    def generateMap(self, mapPath: Path, mapFeatures: list[MapFeature], cityName: str):
        mapFeaturesDict = list(map(dataclasses.asdict, mapFeatures))
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


def _calculateBbox(data: list[Place]) -> tuple[float, float, float, float]:
    if len(data) == 0:
        return 0, 0, 0, 0
    latLonEpsilon = 0.002
    return (
        min(place.lat for place in data) - latLonEpsilon,
        min(place.lon for place in data) - latLonEpsilon,
        max(place.lat for place in data) + latLonEpsilon,
        max(place.lon for place in data) + latLonEpsilon,
    )


def roovee_run(
    network: RooveeNetwork,
    outputPath: Path,
    rooveeParser: RooveeParser,
    mapPath: Path | None = None,
):
    rooveeData = rooveeParser.downloadNetwork(network)
    overpassResult = fetchOverpassData(
        placeName=network.name, bbox=_calculateBbox(rooveeData), admin_level=8
    )
    validator = RooveeComparator(rooveeParser, overpassResult)
    if validator.containsData(outputPath):
        validator.pair(rooveeData)
        validator.generateHtml(outputPath, mapPath, network.name)
