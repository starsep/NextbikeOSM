import argparse
import difflib as SC
from dataclasses import dataclass
from time import localtime, strftime
from typing import List, Optional, Tuple

from jinja2 import Environment, PackageLoader
from overpy import Element, Way

import feed_gen as FG
import nextbike_parser as NP
from distance import GeoPoint, distance
from overpass_parser import OverpassParser

__VERSION__ = "2.0.1"


@dataclass
class Match:
    distance: float
    nextbike: NP.Place
    osm: Element
    osmType: str
    matchedBy: str
    ratio: float = 0.0


class NextbikeValidator:

    """Analyzer class"""

    def __init__(self, nextbikeData, osmParser, html=None):

        self.nextbikeData = nextbikeData
        self.osmParser: OverpassParser = osmParser
        self.matches: List[Match] = []
        self.html = html
        self.envir = Environment(loader=PackageLoader("nextbike_valid", "templates"))

    def matchViaRef(self, place: NP.Place) -> Optional[Element]:
        nextbikeRef = place.num
        for element in self.osmParser.elements:
            if "ref" in element.tags and element.tags["ref"] == nextbikeRef:
                return element
        return None

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
            matchedElement = self.matchViaRef(nextPlace)
            if matchedElement is not None:
                point = GeoPoint.fromElement(matchedElement, self.osmParser)
                dist = distance(nextPlace, point)
                data.append(
                    Match(
                        distance=dist,
                        nextbike=nextPlace,
                        osm=matchedElement,
                        osmType="way" if type(matchedElement) == Way else "node",
                        matchedBy="id",
                    )
                )
            else:
                matchedElement, dist = self.matchViaDistance(nextPlace)
                data.append(
                    Match(
                        distance=dist,
                        nextbike=nextPlace,
                        osm=matchedElement,
                        osmType="way" if type(matchedElement) == Way else "node",
                        matchedBy="di",
                    )
                )

        self.matches = data

    def html_it(self, filename="nextbikeOSM_results.html"):
        """Produces html with processing data."""

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

        fill_template = template.render(
            {"matches": matches, "timestamp": timestamp, "VERSION": __VERSION__}
        )

        with open(filename, "w", encoding="utf-8") as f:
            f.write(fill_template)

        # NEXT vs osm
        # uid  !=     iD
        # lat         lat
        # lon         lon
        # name        name {tags}
        # num         ref {tags}
        # stands      capacity {tags}++

    def containsData(self, path):

        timek = strftime("%a, %d %b @ %H:%M:%S", localtime())

        if len(self.osmParser.nodes) == 0 and len(self.osmParser.ways) == 0:
            template = self.envir.get_template("empty.html")
            fill_template = template.render({"last": timek})

            with open(path, "w", encoding="utf-8") as f:
                f.write(fill_template)

            print("OSM Data not found!")
            return False
        return True


def main(
    update: bool,
    network: str,
    osmAreaName: str,
    htmlPath: str,
    feed: bool,
    nextbikeParser: NP.NextbikeParser,
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
    if validator.containsData(htmlPath):
        validator.pair(d)
        validator.html_it(htmlPath)
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
        htmlPath=args.auto[2],
        feed=args.feed,
        nextbikeParser=NP.NextbikeParser(),
    )
