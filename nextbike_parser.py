import os
import urllib.request as urllib
import xml.etree.ElementTree as XML
from dataclasses import dataclass
from typing import List

from distance import GeoPoint


@dataclass
class Place(GeoPoint):
    uid: str
    name: str
    num: int
    stands: str


@dataclass
class City:
    uid: str
    name: str
    places: List[Place]


@dataclass
class Network:
    name: str
    countryCode: str
    cities: List[City]


class NextbikeParser:
    def __init__(self):
        path = "https://nextbike.net/maps/nextbike-official.xml"
        if "nextbike.xml" in os.listdir():
            pass
        else:
            urllib.urlretrieve(path, "nextbike.xml")

        file = XML.parse("nextbike.xml")
        root = file.getroot()

        C_list = []

        singleBikePlaceTypes = ["12", "20", "22", "24"]

        for network in root:
            cities_list = []

            networkName = network.attrib["name"]
            countryCode = network.attrib["country"]

            for city in network:
                place_list = []

                cityId = city.attrib["uid"]
                cityName = city.attrib["name"]

                for place in city:
                    place_attrib = place.attrib
                    uid = place_attrib["uid"]
                    lat = float(place_attrib["lat"])
                    lon = float(place_attrib["lng"])
                    name = place_attrib["name"]
                    place_type = place_attrib["place_type"]
                    if name.startswith("BIKE") or place_type in singleBikePlaceTypes:
                        continue
                    num = place_attrib["number"] if "number" in place_attrib else 0
                    stands = (
                        int(place_attrib["bike_racks"])
                        if "bike_racks" in place_attrib
                        else "None"
                    )
                    if "terminal_type" in place_attrib:
                        terminal_type = place_attrib["terminal_type"]
                        if terminal_type == "sign" and type(stands) == int and cityName == "Warszawa":
                            # TODO: move logic somewhere else?
                            stands = stands * 2
                    stands = str(stands)
                    place_list.append(
                        Place(
                            uid=uid, lat=lat, lon=lon, name=name, num=num, stands=stands
                        )
                    )
                # if countryCode == "PL" and len(place_list) > 0:
                #     print(networkName, countryCode, cityId, cityName)
                cities_list.append(City(cityId, cityName, place_list))
            C_list.append(Network(networkName, countryCode, cities_list))
        self.countries = C_list

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

    def find_city(self, cityId: str):
        """Returns data for city only"""
        for i in self.countries:
            for city in i.cities:
                if city.uid == cityId:
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
                a = ci.uid
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
        path = "https://nextbike.net/maps/nextbike-live.xml"
        urllib.urlretrieve(path, "nextbike.xml")
