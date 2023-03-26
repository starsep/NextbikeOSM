# NextbikeOSM
![Demo](https://github.com/starsep/NextbikeOSM/blob/main/demo.png)

This application parses data about bicycle rentals in nextbike public bike-sharing systems like (for more data [see wikipedia](https://en.wikipedia.org/wiki/Nextbike)) from [their website](http://nextbike.net/maps/nextbike-official.xml) and compares with data from [OpenStreetMap](http://www.openstreetmap.org).

## How to run this?
You need to have [Python 3](https://www.python.org/downloads/) installed
1. Download all files from this project
2. Install dependencies with `pip install -r requirements.txt`
3. Run file run.py

## Technical details
This script tries to match stations by ref, when impossible looks for closest node using Haversine formula. ***Note that sometimes the closest node is not correct node!*** Then checks tags and compares strings in name tag using [GESTALT.C (Ratcliff/Obershelp Pattern Recognition Algorithm)](http://collaboration.cmc.ec.gc.ca/science/rpn/biblio/ddj/Website/articles/DDJ/1988/8807/8807c/8807c.htm) built-in [python difflib module](https://docs.python.org/3.4/library/difflib.html). And of course...it make html from it :)

## More
Note that this application is suitable for quality assurance only. You should make changes in osm base very carefully and I don't take any responsibility!<br>
If you want to help me and add something to code or see any bug just call an issue or make pull request!

[Copyright (c) 2015 javnik36](https://github.com/javnik36/NextbikeOSM/blob/master/LICENCE)
[Copyright (c) 2023 starsep](https://github.com/starsep/NextbikeOSM/blob/main/LICENCE)
