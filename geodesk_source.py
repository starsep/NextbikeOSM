from geodesk import Box, Features


def geodesk_bicycle_rentals(
    place_name: str,
    bbox: tuple[float, float, float, float],
    admin_level: int,
):
    library = Features("geodesk-data/poland.gol")
    places = library(
        f'a[boundary=administrative][admin_level={admin_level}][name="{place_name}"]'
    )
    if places.count == 0:
        return
    place = places.first
    bicycle_rentals = library("*[amenity=bicycle_rental]")
    disused_bicycle_rentals = library(
        '*[amenity=bicycle_parking]["disused:amenity"=bicycle_rental]'
    )
    bicycle_rentals_in_place = bicycle_rentals.within(place)
    disused_bicycle_rentals_in_place = disused_bicycle_rentals.within(place)
    (lat_min, lon_min, lat_max, lon_max) = bbox
    bounds = Box(west=lon_min, south=lat_min, east=lon_max, north=lat_max)
    bicycle_rentals_in_bounds = bicycle_rentals(bounds)
    disused_bicycle_rentals_in_bounds = disused_bicycle_rentals(bounds)
    print(
        place_name,
        bicycle_rentals_in_place.count,
        disused_bicycle_rentals_in_place.count,
        bicycle_rentals_in_bounds.count,
        disused_bicycle_rentals_in_bounds.count,
    )
