from pyproj import Geod

import osm_parser as OP
import nextbike_parser as NP

__VERSION__ = "2.0.1"

wgs84Geod = Geod(ellps="WGS84")


def measure(point_next, point_osm):
    return round(
        wgs84Geod.inv(point_next.lon, point_next.lat, point_osm.lon, point_osm.lat)[2],
        ndigits=2,
    )


class NextbikeValidator:

    """Analyzer class"""

    def __init__(self, next_data, osm_data, pair_bank=None, html=None):
        from jinja2 import PackageLoader, Environment

        self.next_data = next_data
        self.osm_data = osm_data
        self.pair_bank = []
        self.html = html
        self.envir = Environment(loader=PackageLoader("nextbike_valid", "templates"))

    def via_id(self, place):
        """Return osm feature by ref matching"""
        # input: next_place (nextbike Place)
        nextb_ref = place.num
        for i in self.osm_data.nodes:
            for k, v in i.tags.items():
                if k == "ref":
                    if v == nextb_ref:
                        return i
                    else:
                        pass
        return None

    def via_distance(self, place):
        """Return osm feature by distance matching"""
        dist = 10000000
        nearest = 0
        for i in self.osm_data.nodes:
            meas = measure(place, i)
            if meas < dist:
                dist = meas
                nearest = i
            elif meas > dist:
                continue
        return [nearest, dist]

    def pair(self, next_places):
        """Makes a pair of OSM and Nextbike features by their distance."""
        # input: list of next_places from city & osm
        dane = []
        for i in next_places:
            id_match = self.via_id(i)
            if id_match is not None:
                meas = measure(i, id_match)

                fway = self.osm_data.find(id_match.iD, "w")
                if fway is not None:
                    d1 = (meas, i, fway, "w", "id")
                else:
                    d1 = (meas, i, id_match, "n", "id")
                dane.append(d1)
            else:
                data = self.via_distance(i)
                obj = data[0]
                meas = data[1]

                fway = self.osm_data.find(obj.iD, "w")
                if fway is not None:
                    d1 = (meas, i, fway, "w", "di")
                else:
                    d1 = (meas, i, obj, "n", "di")
                dane.append(d1)

        self.pair_bank = dane

    def html_it(self, filename="nextbikeOSM_results.html"):
        """Produces html with processing data."""
        import difflib as SC
        from time import localtime, strftime

        timek = strftime("%a, %d %b @ %H:%M:%S", localtime())

        template = self.envir.get_template("base.html")

        dane = []
        timestamp = "Updated: {0}".format(timek)

        for i in self.pair_bank:
            i_dict = {
                "distance": i[0],
                "nxtb": i[1],
                "osm": i[2],
                "type": i[3],
                "match": i[4],
            }

            nextb = i[1]
            osm = i[2]
            try:
                prob = SC.SequenceMatcher(
                    None, nextb.name, osm.tags.get("name")
                ).ratio()
            except:
                prob = 0

            i_dict["prob"] = prob

            dane.append(i_dict)

        fill_template = template.render(
            {"items": dane, "timek": timestamp, "VERSION": __VERSION__}
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

    def is_whatever(self, path):
        from time import localtime, strftime
        import sys

        timek = strftime("%a, %d %b @ %H:%M:%S", localtime())

        if self.osm_data.nodes == [] and self.osm_data.ways == []:
            template = self.envir.get_template("empty.html")
            fill_template = template.render({"last": timek})

            with open(path, "w", encoding="utf-8") as f:
                f.write(fill_template)

            print("OSM Data not found!")
            sys.exit()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        "--auto",
        action="store",
        nargs=3,
        metavar=("NETWORK", "OSM_PATH", "HTML_PATH"),
        help="NETWORK is uid or name to be found in nextbike_uids.txt",
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="runs interactive guide"
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

    if args.update:
        NP.NextbikeParser.update()
        a = NP.NextbikeParser()
        a.get_uids()
    if args.auto:
        a = OP.osmParser(args.auto[1])
        a.fill_ways()
        a.clear_nodes()
        a.fake_all()
        b = NP.NextbikeParser()
        validator = NextbikeValidator(b, a)
        if args.auto[0].isnumeric():
            d = b.find_city(args.auto[0])
        else:
            d = b.find_network(args.auto[0])
        validator.is_whatever(args.auto[2])
        validator.pair(d)
        validator.html_it(args.auto[2])
        if args.feed:
            import feed_gen as FG

            a.remove_fakes()
            feed = FG.Feed(args.auto[2].rstrip(".html"), a.nodes, a.ways, d)
            feed.new_db()
            feed.check_db()
            feed.make_feeds()
            feed.create_feed()

    if args.interactive:
        path_osm = input("Write path to osm file:\n")
        a = OP.osmParser(path_osm)
        a.fill_ways()
        a.clear_nodes()
        a.fake_all()
        b = NP.NextbikeParser()
        place = input(
            "______________\nWhat kind of network\city should I process?\n>If you want particular city please write it's uid number from nextbike_uids.txt\n>>For whole network write it's name(within ''), also from nextbike_uids.txt\n"
        )
        validator = NextbikeValidator(b, a)
        if place.isnumeric():
            d = b.find_city(place)
        else:
            d = b.find_network(place)
        validator.pair(d)
        html = input("______________\nHTML name?\n")
        validator.is_whatever(html)
        validator.html_it(html)
        print("______________\nAll done...thanks!")
