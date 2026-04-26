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
    shutil.copy(templatesDirectory / "index.js", outputDirectory / "index.js")


def mevo_main():
    mevoParser = MevoParser()
    mevo_run(
        outputPath=outputDirectory / "mevo.html",
        mapPath=outputDirectory / "map-mevo.html",
        mevoParser=mevoParser,
    )

    _environment = Environment(loader=PackageLoader("main", "templates"))
    shutil.copy(templatesDirectory / "index.js", outputDirectory / "index.js")
    shutil.copy(libsDirectory / "sorttable.js", outputDirectory / "sorttable.js")
    shutil.copy(staticDirectory / "josm.svg", outputDirectory / "josm.svg")


if __name__ == "__main__":
    healthchecks("/start")  # TODO: multiple healthchecks?
    outputDirectory.mkdir(exist_ok=True)
    try:
        nextbike_main()
    except Exception as e:
        logging.exception("Nextbike failed", e)
    try:
        mevo_main()
    except Exception as e:
        logging.exception("Mevo failed", e)
    healthchecks()
