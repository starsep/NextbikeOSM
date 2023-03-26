import shutil
from pathlib import Path

from jinja2 import Environment, PackageLoader
from slugify import slugify

from nextbike_parser import NextbikeParser
from nextbike_valid import main

if __name__ == "__main__":
    templatesDirectory = Path("templates")
    outputDirectory = Path("output")
    outputDirectory.mkdir(exist_ok=True)
    nextbikeParser = NextbikeParser()

    networksPoland = []
    for country in nextbikeParser.countries:
        if country.countryCode == "PL":
            for city in country.cities:
                if len(city.places) > 0:
                    networksPoland.append((city.uid, city.name.removesuffix(" (RL)")))
    for networkId, cityName in networksPoland:
        slug = slugify(cityName)
        main(
            update=False,
            network=str(networkId),
            cityName=cityName,
            outputPath=outputDirectory / f"{slug}.html",
            mapPath=outputDirectory / f"map-{slug}.html",
            nextbikeParser=nextbikeParser,
        )

    environment = Environment(loader=PackageLoader("nextbike_valid", "templates"))
    template = environment.get_template("index.html")
    cities = sorted([(cityName, slugify(cityName)) for (_, cityName) in networksPoland], key=lambda x: x[0])
    with (outputDirectory / "index.html").open("w", encoding="utf-8") as f:
        f.write(template.render(dict(cities=cities)))
    shutil.copy(templatesDirectory / "index.js", outputDirectory / "index.js")
