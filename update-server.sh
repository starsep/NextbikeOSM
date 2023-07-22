#!/usr/bin/env bash
set -eu
date=$(/bin/date '+%Y%m%d')
mkdir -p cache
touch cache/dateOfLastRun
if [[ "$(cat cache/dateOfLastRun)" != "$date" ]]; then
    rm -f cache/nextbike.xml
fi
rm -rf cache/overpass
git clone https://$GITHUB_USERNAME:$GITHUB_TOKEN@github.com/starsep/NextbikeOSM --depth 1 --branch gh-pages output
python run.py
(
    cd output || exit 1
    git config user.name "NextbikeOSMBot"
    git config user.email "<>"
    git add .
    git commit -m "Update $date"
    git push origin gh-pages
)
echo "$date" > cache/dateOfLastRun
