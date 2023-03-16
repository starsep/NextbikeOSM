#!/usr/bin/env bash
date=$(/bin/date '+%Y%m%d')
touch .dateOfLastRun
if [[ "$(cat .dateOfLastRun)" != "$date" ]]; then
    rm -rf cache
fi
git pull
rm -rf cache/overpass
source .venv/bin/activate
pip install -r requirements.txt
cd output || return
git pull
cd .. || return
python run.py
cd output || return
git config user.name "NextbikeOSMBot"
git config user.email "<>"
git add .
git commit -m "Update $date"
git push origin gh-pages
cd .. || return
echo "$date" > .dateOfLastRun
