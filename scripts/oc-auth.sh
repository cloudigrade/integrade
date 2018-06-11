#!/bin/bash
export CLOUDIGRADE_BASE_URL="${CLOUDIGRADE_BASE_URL:-test.cloudigra.de}"
export CLOUDIGRADE_USER=$(uuidgen --random)
oc rsh -c cloudigrade-api $(oc get pods -o jsonpath='{.items[*].metadata.name}' -l name=cloudigrade-api) scl enable rh-postgresql96 rh-python36 -- python manage.py createsuperuser --no-input --username $CLOUDIGRADE_USER --email="$CLOUDIGRADE_USER@example.com"
export CLOUDIGRADE_TOKEN=$(oc rsh -c cloudigrade-api $(oc get pods -o jsonpath='{.items[*].metadata.name}' -l name=cloudigrade-api) scl enable rh-postgresql96 rh-python36 -- python manage.py drf_create_token $CLOUDIGRADE_USER | awk '{print $3}')
