#!/usr/bin/env -S uv run python
import logging
import shutil
from pathlib import Path

from jinja2 import Environment, PackageLoader
from slugify import slugify
from starsep_utils import healthchecks

from mevo_comparator import mevo_run
from mevo_parser import MevoParser
from nextbike_parser import NextbikeParser
from nextbike_valid import nextbike_run
from roovee_comparator import roovee_run
from roovee_parser import RooveeNetwork, RooveeParser

templatesDirectory = Path("templates")
libsDirectory = Path("libs")
staticDirectory = Path("static")
outputDirectory = Path("output")


def nextbike_main():
    nextbikeParser = NextbikeParser()
    networksPoland = []
    for country in nextbikeParser.countries:
        if country.countryCode == "PL":
            for city in country.cities:
                if len(city.places) > 0:
                    networksPoland.append((city.uid, city.name.removesuffix(" (RL)")))
    for networkId, cityName in networksPoland:
        slug = slugify(cityName)
        nextbike_run(
            update=False,
            network=str(networkId),
            cityName=cityName,
            outputPath=outputDirectory / f"{slug}.html",
            mapPath=outputDirectory / f"map-{slug}.html",
            nextbikeParser=nextbikeParser,
        )

    environment = Environment(loader=PackageLoader("nextbike_valid", "templates"))
    template = environment.get_template("index.html")
    cities = sorted(
        [(cityName, slugify(cityName)) for (_, cityName) in networksPoland],
        key=lambda x: x[0],
    )
    with (outputDirectory / "index.html").open("w", encoding="utf-8") as f:
        f.write(template.render(dict(cities=cities)))


def mevo_main():
    mevoParser = MevoParser()
    mevo_run(
        outputPath=outputDirectory / "mevo.html",
        mapPath=outputDirectory / "map-mevo.html",
        mevoParser=mevoParser,
    )

    _environment = Environment(loader=PackageLoader("main", "templates"))


# TODO: GeoJSON output
def roovee_main():
    roovee_networks = [
        RooveeNetwork(tenant="bikes", name="Szczecin"),
        RooveeNetwork(tenant="brom", name="Bolesławiec"),
        RooveeNetwork(tenant="chromek", name="Chodzież"),
        RooveeNetwork(tenant="czeladz", name="Czeladź"),
        RooveeNetwork(tenant="duszniki", name="Duszniki-Zdrój"),
        RooveeNetwork(tenant="gliwice", name="Gliwice"),
        RooveeNetwork(tenant="gniezno", name="Gniezno"),
        # RooveeNetwork(tenant="grom", name="Giżycko"),
        RooveeNetwork(tenant="kielce", name="Kielce"),
        RooveeNetwork(tenant="krotower", name="Krotoszyn"),
        RooveeNetwork(tenant="naklo", name="Nakło nad Notecią"),
        RooveeNetwork(tenant="ndm", name="Nowy Dwór Mazowiecki"),
        RooveeNetwork(tenant="olesnica", name="Oleśnica"),
        RooveeNetwork(tenant="ostro", name="Ostrołęka"),
        # RooveeNetwork(tenant="polkowice", name="Polkowice"),
        RooveeNetwork(tenant="rawicz", name="Rawicz"),
        RooveeNetwork(tenant="skarzysko", name="Skarżysko-Kamienna"),
        RooveeNetwork(tenant="srm", name="Ścinawa"),
        RooveeNetwork(tenant="suwalki", name="Suwałki"),
        RooveeNetwork(tenant="swmr", name="Stalowa Wola"),
        RooveeNetwork(tenant="suchylas", name="Suchy Las"),
        RooveeNetwork(tenant="srem", name="Śrem"),
        RooveeNetwork(tenant="wagrowiec", name="Wągrowiec"),
        RooveeNetwork(tenant="zabrze", name="Zabrze"),
        RooveeNetwork(tenant="zary", name="Żary"),
        RooveeNetwork(tenant="zmigrod", name="Żmigród"),
    ]
    rooveeParser = RooveeParser()
    for network in roovee_networks:
        slug = slugify(network.name)
        roovee_run(
            network=network,
            outputPath=outputDirectory / f"{slug}.html",
            mapPath=outputDirectory / f"map-{slug}.html",
            rooveeParser=rooveeParser,
        )

    environment = Environment(loader=PackageLoader("main", "templates"))
    template = environment.get_template("index.html")
    cities = sorted(
        [(network.name, slugify(network.name)) for network in roovee_networks],
        key=lambda x: x[0],
    )
    with (outputDirectory / "index.html").open("w", encoding="utf-8") as f:
        f.write(template.render(dict(cities=cities)))


if __name__ == "__main__":
    healthchecks("/start")  # TODO: multiple healthchecks?
    outputDirectory.mkdir(exist_ok=True)
    shutil.copy(templatesDirectory / "index.js", outputDirectory / "index.js")
    shutil.copy(libsDirectory / "sorttable.js", outputDirectory / "sorttable.js")
    shutil.copy(staticDirectory / "josm.svg", outputDirectory / "josm.svg")
    try:
        nextbike_main()
    except Exception as e:
        logging.exception("Nextbike failed", e)
    try:
        mevo_main()
    except Exception as e:
        logging.exception("Mevo failed", e)
    try:
        roovee_main()
    except Exception as e:
        logging.exception("Roovee failed", e)
    healthchecks()
