from dataclasses import dataclass
from typing import List

import httpx
from starsep_utils import GeoPoint


@dataclass(frozen=True)
class Station(GeoPoint):
    name: str
    ref: str
    capacity: int


class MevoParser:
    def downloadNetwork(self) -> List[Station]:
        # https://rowermevo.pl/open-data/realtime
        data = httpx.get(
            "https://gbfs.urbansharing.com/rowermevo.pl/station_information.json",
            headers={"Client-Identifier": "starsep-mevoosm"},
        ).json()
        stations: List[Station] = []
        for station in data["data"]["stations"]:
            # if station["is_virtual_station"]:
            #     continue
            stations.append(
                Station(
                    name=station["name"],
                    lat=station["lat"],
                    lon=station["lon"],
                    ref=station["station_id"],
                    capacity=station["capacity"],
                )
            )
        return stations
