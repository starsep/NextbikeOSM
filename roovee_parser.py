from dataclasses import dataclass

import httpx
from starsep_utils import GeoPoint


@dataclass(frozen=True)
class Place(GeoPoint):
    name: str


@dataclass
class RooveeNetwork:
    tenant: str
    name: str


class RooveeParser:
    def downloadNetwork(self, network: RooveeNetwork) -> list[Place]:
        data = httpx.get(
            f"https://api.roovee.eu/public/bikesAndZones?tenant={network.tenant}"
        ).json()
        places: list[Place] = []
        for zone in data["zones"]:
            zoneType = zone["type"]
            if zoneType == "operationsZone":
                continue
            if zoneType != "preferredBikeReturnZone":
                print(f"Unexpected type = {zoneType}")
                continue
            places.append(
                Place(
                    name=zone["name"],
                    lat=zone["areaCenter"]["lat"],
                    lon=zone["areaCenter"]["lng"],
                )
            )
        return places
