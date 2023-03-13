from jinja2 import Environment, PackageLoader
from slugify import slugify

from nextbike_valid import main

if __name__ == "__main__":
    networksPoland = [
        (148, "Wrocław"),
        (251, "Lublin"),
        (331, "Świdnik"),
        (255, "Grodzisk Mazowiecki"),
        (422, "Kołobrzeg"),
        (461, "Piaseczno"),
        (496, "Koszalin"),
        (504, "Pobiedziska"),
        (518, "Piotrków Trybunalski"),
        (545, "Konin"),
        (529, "Zielona Góra"),
        (548, "Tarnów"),
        (562, "Koluszki"),
        (563, "Łask"),
        (564, "Łowicz"),
        (565, "Pabianice"),
        (566, "Sieradz"),
        (567, "Skierniewice"),
        (568, "Zduńska Wola"),
        (569, "Zgierz"),
        (570, "Kutno"),
        (571, "Łódź"),
        (650, "Olesno"),
        (727, "Sokołów Podlaski"),
        (812, "Warszawa"),
        (831, "Wolsztyn"),
    ]
    for (networkId, cityName) in networksPoland:
        slug = slugify(cityName)
        main(
            update=False,
            network=str(networkId),
            osmAreaName=cityName,
            htmlPath=f"docs/{slug}.html",
            feed=False,
        )

    environment = Environment(loader=PackageLoader("nextbike_valid", "templates"))
    template = environment.get_template("index.html")
    cities = [(cityName, slugify(cityName)) for (_, cityName) in networksPoland]
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(template.render(dict(cities=cities)))
