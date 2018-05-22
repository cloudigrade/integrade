#!/bin/bash
set -euvo pipefail

curl -L -s -o /tmp/oc.tar.gz https://github.com/openshift/origin/releases/download/v3.7.2/openshift-origin-client-tools-v3.7.2-282e43f-linux-64bit.tar.gz

tar zxvf /tmp/oc.tar.gz -C /tmp
mkdir "${HOME}/oc"
mv /tmp/openshift-origin-client-tools*/oc "${HOME}/oc/"
