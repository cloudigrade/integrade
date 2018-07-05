#!/bin/bash
set -euvo pipefail

curl -L -s -o /tmp/sc.tar.gz https://saucelabs.com/downloads/sc-4.4.12-linux.tar.gz

tar zxvf /tmp/sc.tar.gz -C /tmp
mkdir -p "${HOME}/.local/bin"
mv /tmp/sc-4.4.12-linux/bin/sc "${HOME}/.local/bin/"
