#!/bin/bash
set -euvo pipefail

curl -L -s -o geckodriverrelease https://api.github.com/repos/mozilla/geckodriver/releases/latest

cat > parser.py <<EOF
import sys, json
r = json.load(sys.stdin)
if 'assets' in r:
    print([a for a in r['assets'] if 'linux64' in a['name']][0]['browser_download_url']);
else:
    print('https://github.com/mozilla/geckodriver/releases/download/v0.20.1/geckodriver-v0.20.1-linux64.tar.gz')
EOF

export GECKODRIVER_DOWNLOAD="$(cat geckodriverrelease | python parser.py)"
curl -L -s -o /tmp/geckodriver.tar.gz "${GECKODRIVER_DOWNLOAD}"

mkdir "${HOME}/geckodriver"
tar xvf /tmp/geckodriver.tar.gz -C "${HOME}/geckodriver"
