#!/bin/bash
alias uuid4='python -c "import uuid;print(uuid.uuid4())"'
export CLOUDIGRADE_BASE_URL="${CLOUDIGRADE_BASE_URL:-test.cloudigra.de}"
export CLOUDIGRADE_USER=$(uuid4)
export CLOUDIGRADE_PASSWORD=$(uuid4)
if [ $DEPLOYMENT_PREFIX = "" ]; then
	export CLOUDIGRADE_POD_NAME=cloudigrade-api
else
	export CLOUDIGRADE_POD_NAME=${DEPLOYMENT_PREFIX}-cloudigrade-api
fi
oc rsh -c ${CLOUDIGRADE_POD_NAME} $(oc get pods -o jsonpath='{.items[*].metadata.name}' -l name=${CLOUDIGRADE_POD_NAME}) scl enable rh-postgresql96 rh-python36 -- python manage.py createsuperuser --no-input --username $CLOUDIGRADE_USER --email="${CLOUDIGRADE_USER}@example.com"
export CLOUDIGRADE_TOKEN=$(oc rsh -c ${CLOUDIGRADE_POD_NAME} $(oc get pods -o jsonpath='{.items[*].metadata.name}' -l name=${CLOUDIGRADE_POD_NAME}) scl enable rh-postgresql96 rh-python36 -- python manage.py drf_create_token $CLOUDIGRADE_USER | awk '{print $3}')
cat << EOF | oc rsh -c ${CLOUDIGRADE_POD_NAME} $(oc get pods -o jsonpath='{.items[*].metadata.name}' -l name=${CLOUDIGRADE_POD_NAME}) scl enable rh-postgresql96 rh-python36 -- python manage.py shell
from django.contrib.auth.models import User
user = User.objects.get(email="$CLOUDIGRADE_USER@example.com")
user.set_password("$CLOUDIGRADE_PASSWORD")
user.save()
EOF
