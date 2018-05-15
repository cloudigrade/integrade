#!/bin/bash
export CLOUDIGRADE_USER=$(uuidgen --random)
oc rsh -c cloudigrade $(oc get pods -o jsonpath='{.items[*].metadata.name}' -l name=cloudigrade) scl enable rh-postgresql96 rh-python36 -- python manage.py createsuperuser --no-input --username $CLOUDIGRADE_USER --email="$CLOUDIGRADE_USER@example.com"
export CLOUDIGRADE_TOKEN=$(oc rsh -c cloudigrade $(oc get pods -o jsonpath='{.items[*].metadata.name}' -l name=cloudigrade) scl enable rh-postgresql96 rh-python36 -- python manage.py drf_create_token $CLOUDIGRADE_USER | awk '{print $3}')
