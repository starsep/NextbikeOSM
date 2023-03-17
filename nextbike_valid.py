import argparse
import dataclasses
import difflib as SC
import json
from dataclasses import dataclass
from pathlib import Path
from time import localtime, strftime
from typing import List, Optional, Tuple

from jinja2 import Environment, PackageLoader
from overpy import Element, Way

import feed_gen as FG
import nextbike_parser as NP
from distance import GeoPoint, distance
from overpass_parser import OverpassParser

__VERSION__ = "3.0.0"


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

    def toCSV(self) -> str:
        return f"name={self.name},ref={self.ref},capacity={self.capacity}"


@dataclass
class MapFeature(GeoPoint):
    tags: MapFeatureTags

    @staticmethod
    def fromMatch(match: Match):
        return MapFeature(
            lat=match.nextbike.lat,
            lon=match.nextbike.lon,
            tags=MapFeatureTags(
                name=match.nextbike.name,
                ref=match.nextbike.num,
                capacity=match.nextbike.stands,
            ),
        )

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
        bestDistance = 10000000
        for element in self.osmParser.elements:
            if "ref" in element.tags and element.tags["ref"] == nextbikeRef:
                point = GeoPoint.fromElement(element, self.osmParser)
                dist = distance(place, point)
                if dist < bestDistance:
                    bestDistance = dist
                    result = element
        return result, bestDistance

    def matchViaDistance(self, place: NP.Place) -> Tuple[Optional[Element], float]:
        bestDistance = 100000000
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
        distanceThreshold = 50.0
        csvPath = outputPath.with_suffix(".csv")
        with outputPath.open("w", encoding="utf-8") as f:
            context = {
                "matches": matches,
                "timestamp": timestamp,
                "VERSION": __VERSION__,
                "distanceThreshold": distanceThreshold,
                "mapLink": str(mapPath.name),
                "csvLink": str(csvPath.name),
            }
            f.write(template.render(context))
        if mapPath is not None:
            mapFeatures = list(
                map(
                    MapFeature.fromMatch,
                    filter(lambda m: m.distance > distanceThreshold, matches),
                ),
            )
            mapFeaturesDict = list(map(dataclasses.asdict, mapFeatures))
            mapTemplate = self.envir.get_template("map.html")
            with mapPath.open("w", encoding="utf-8") as f:
                context = {"featuresJson": json.dumps(mapFeaturesDict)}
                f.write(mapTemplate.render(context))
            networkTags = dict(
                amenity="bicycle_rental",
                operator="Nextbike Polska",
            )
            if outputPath.name.startswith("warszawa"):  # TODO: move logic
                networkTags["bicycle_rental"] = "dropoff_point"
                networkTags["brand"] = "Veturilo"
                networkTags["brand:wikidata"] = "Q3847868"
                networkTags["network"] = "Veturilo"
                networkTags["network:wikidata"] = "Q3847868"
            networkTagsCSV = ",".join(
                [f"{key}={value}" for key, value in networkTags.items()]
            )
            with csvPath.open("w") as f:
                for feature in mapFeatures:
                    f.write(feature.toCSV() + "," + networkTagsCSV + "\n")
        # NEXT vs osm
        # uid  !=     iD
        # lat         lat
        # lon         lon
        # name        name {tags}
        # num         ref {tags}
        # stands      capacity {tags}++

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


def main(
    update: bool,
    network: str,
    osmAreaName: str,
    outputPath: Path,
    feed: bool,
    nextbikeParser: NP.NextbikeParser,
    mapPath: Optional[Path] = None,
):
    if update:
        NP.NextbikeParser.update()
        nextbikeParser.get_uids()
    data = OverpassParser(osmAreaName)
    validator = NextbikeValidator(nextbikeParser, data)
    if network.isnumeric():
        d = nextbikeParser.find_city(network)
    else:
        d = nextbikeParser.find_network(network)
    if validator.containsData(outputPath):
        validator.pair(d)
        validator.generateHtml(outputPath, mapPath)
        if feed:
            feed = FG.Feed(args.auto[2].rstrip(".html"), data.nodes, data.ways, d)
            feed.new_db()
            feed.check_db()
            feed.make_feeds()
            feed.create_feed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        "--auto",
        action="store",
        nargs=3,
        metavar=("NETWORK", "OSM_AREA_NAME", "HTML_PATH"),
        help="NETWORK is uid or name to be found in nextbike_uids.txt",
        required=True,
    )
    parser.add_argument(
        "-u",
        "--update",
        action="store_true",
        help="updates manually nextbike .xml file and .set file with uids",
    )
    parser.add_argument(
        "-f", "--feed", action="store_true", help="runs feed creation (only with -a!)"
    )
    args = parser.parse_args()
    main(
        update=args.update,
        network=args.auto[0],
        osmAreaName=args.auto[1],
        outputPath=Path(args.auto[2]),
        feed=args.feed,
        nextbikeParser=NP.NextbikeParser(),
    )
