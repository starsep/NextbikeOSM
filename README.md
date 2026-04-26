# NextbikeOSM
![Demo](https://github.com/starsep/NextbikeOSM/blob/main/demo.png)

This application parses data about bicycle rentals in nextbike public bike-sharing systems like (for more data [see wikipedia](https://en.wikipedia.org/wiki/Nextbike)) from [their website](http://nextbike.net/maps/nextbike-official.xml) and compares with data from [OpenStreetMap](http://www.openstreetmap.org).

## Docker
```
docker build -t nextbikeosm .
docker run --rm \
    -v "$(pwd)/cache:/app/cache" \
    --env GITHUB_USERNAME=example \
    --env GITHUB_TOKEN=12345 \
    --env TZ=Europe/Warsaw \
    -t nextbikeosm
```

## Technical details
1. This script tries to match stations by ref, when impossible looks for closest node using Haversine formula.
***Note that sometimes the closest node is not correct node!***
2. Tags are checked and compared strings in name tag using [python difflib module](https://docs.python.org/3.4/library/difflib.html)
3. HTML output + map + KML is generated


[Copyright (c) 2015 javnik36](https://github.com/javnik36/NextbikeOSM/blob/master/LICENCE)
[Copyright (c) 2023 starsep](https://github.com/starsep/NextbikeOSM/blob/main/LICENCE)

Part of icons from https://icons.getbootstrap.com
