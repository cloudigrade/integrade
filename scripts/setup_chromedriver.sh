#!/bin/bash
set -euvo pipefail

export LATEST_CHROMEDRIVER="$(curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE)"
curl -L -s -o /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${LATEST_CHROMEDRIVER}/chromedriver_linux64.zip"
mkdir "${HOME}/chromedriver"
unzip /tmp/chromedriver.zip -d "${HOME}/chromedriver"
