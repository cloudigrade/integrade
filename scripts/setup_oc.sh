#!/bin/bash
set -euvo pipefail

curl -L -s -o /tmp/oc.tar.gz https://github.com/openshift/origin/releases/download/v3.9.0/openshift-origin-client-tools-v3.9.0-191fece-linux-64bit.tar.gz

tar zxvf /tmp/oc.tar.gz -C /tmp
mkdir "${HOME}/oc"
mv /tmp/openshift-origin-client-tools*/oc "${HOME}/oc/"
