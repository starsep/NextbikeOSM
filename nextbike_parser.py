class Place:
    def __init__(self, uid, lat, lon, name, num, stands, bike_numbers=None):
        self.uid = uid
        self.lat = lat
        self.lon = lon
        self.name = name
        self.num = num
        self.stands = stands
        self.bike_numbers = []

    def __str__(self):
        return (
            "#"
            + str(self.uid)
            + ": "
            + str(self.num)
            + ","
            + self.name
            + " with "
            + str(self.stands)
            + " stands. $lat$"
            + str(self.lat)
            + " $lon$"
            + str(self.lon)
            + " $bike_numbers$"
            + str(len(self.bike_numbers))
        )


class City:
    def __init__(self, uid, name, places=None):
        self.uid = uid
        self.name = name
        self.places = []

    def __str__(self):
        return (
            "#"
            + str(self.uid)
            + " @"
            + self.name
            + " with "
            + str(len(self.places))
            + " places."
        )

    def get(self, nr):
        if self.uid == nr:
            return self.places

    def get_uid(self):
        return self.uid


class Country:
    def __init__(self, name, country, cities=None):
        self.name = name
        self.country = country
        self.cities = []

    def __str__(self):
        return (
            "$"
            + self.name
            + " @"
            + self.country
            + " with "
            + str(len(self.cities))
            + " cities."
        )


class NextbikeParser:

    """Aggregates Nextbike country Classes"""

    def __init__(self, countrys=None):
        import xml.etree.ElementTree as XML
        import urllib.request as urllib
        import os

        path = "https://nextbike.net/maps/nextbike-official.xml"
        if "nextbike.xml" in os.listdir():
            pass
        else:
            urllib.urlretrieve(path, "nextbike.xml")

        file = XML.parse("nextbike.xml")
        root = file.getroot()

        C_list = []

        singleBikePlaceTypes = ["12", "20", "22", "24"]

        for country in root:
            cities_list = []

            name = country.attrib["name"]
            countryName = country.attrib["country"]

            C = Country(name, countryName)
            for city in country:
                place_list = []

                uid = city.attrib["uid"]
                name = city.attrib["name"]

                c = City(uid, name)

                for place in city:
                    place_attrib = place.attrib
                    uid = place_attrib["uid"]
                    lat = place_attrib["lat"]
                    lon = place_attrib["lng"]
                    name = place_attrib["name"]
                    place_type = place_attrib["place_type"]
                    if name.startswith("BIKE") or place_type in singleBikePlaceTypes:
                        continue
                    num = place_attrib["number"] if "number" in place_attrib else 0
                    bike_stands = (
                        int(place_attrib["bike_racks"])
                        if "bike_racks" in place_attrib
                        else "None"
                    )
                    if "terminal_type" in place_attrib:
                        terminal_type = place_attrib["terminal_type"]
                        if terminal_type == "sign" and type(bike_stands) == int:
                            # TODO: move logic somewhere else?
                            bike_stands = bike_stands * 2
                    bike_numbers = (
                        place.attrib["bike_numbers"]
                        if "bike_numbers" in place_attrib
                        else None
                    )
                    place_list.append(
                        Place(uid, lat, lon, name, num, bike_stands, bike_numbers)
                    )

                c.places = place_list
                cities_list.append(c)

            C.cities = cities_list
            C_list.append(C)
        self.countries = C_list
        # self.countries = []

    def __str__(self):
        for i in self.countries:
            return i.name

    def find_network(self, name):
        """Returns data for whole network"""
        db = []
        for i in self.countries:
            if i.name == name:
                for city in i.cities:
                    e = city.places
                    db += e
        return db

    def find_city(self, name):
        """Returns data for city only"""
        for i in self.countries:
            for city in i.cities:
                if city.uid == str(name):
                    e = city.places
                    return e

    def check_uids(self, new_uids):
        old_uids = []
        with open("uids.set", "r") as f:
            for line in f.readlines():
                line = line.rstrip()
                old_uids.append(line)

        def diff(a, b):
            b = set(b)
            difr = [aa for aa in a if aa not in b]
            return difr

        removed = diff(old_uids, new_uids)
        new = diff(new_uids, old_uids)

        if len(removed) > 0:
            print("REMOVED UIDS FOUND! {0}".format(str(removed)))
        if len(new) > 0:
            print("NEW UIDS FOUND! {0}".format(str(new)))

    def get_uids(self, cons="n"):
        """Makes file with all uids from xml-file. If cons='y' it's print it to console too."""
        temp = []
        uids = []
        for c in self.countries:
            p = c.name
            temp.append("_______________")
            temp.append(p)
            for ci in c.cities:
                a = ci.get_uid()
                b = str(ci.name)
                c = a + " " + b
                temp.append(c)
                uids.append(a)
        with open("nextbike_uids.txt", "w", encoding="utf-8") as f:
            f.write("Network\nuid<<>>city name\n")
            for i in temp:
                if cons == "y":
                    print(str(i))
                f.write(str(i) + "\n")

        self.check_uids(uids)

        with open("uids.set", "w") as f:
            for i in uids:
                f.write("{0}\n".format(i))

    @staticmethod
    def update():
        """Updates xml manually"""
        import urllib.request as urllib

        path = "https://nextbike.net/maps/nextbike-live.xml"
        urllib.urlretrieve(path, "nextbike.xml")
