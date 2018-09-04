#!/bin/bash

if [[ ${DEPLOYMENT_PREFIX:-} ]]; then
    CONTAINER_NAME="${DEPLOYMENT_PREFIX}cloudigrade-api"
else
    CONTAINER_NAME="cloudigrade-api"
fi

# we print out just the first running pod, which
# helps if there is a terminating pod kicking around or if we are
# running with multiple api pods
POD="$(oc get pods -o jsonpath='{.items[*].metadata.name}' --show-all=false -l name=${CONTAINER_NAME} | awk '{ print $1 }')"

if [[ ! "${POD}" ]]; then
    echo "Not able to find any pod for ${CONTAINER_NAME}."
else
    function uuid4() {
        python -c "import uuid;print(uuid.uuid4())"
    }

    export CLOUDIGRADE_BASE_URL="${CLOUDIGRADE_BASE_URL:-test.cloudigra.de}"
    export CLOUDIGRADE_USER=$(uuid4)
    export CLOUDIGRADE_PASSWORD=$(uuid4)

    oc rsh -c "${CONTAINER_NAME}" "${POD}" scl enable rh-python36 -- python manage.py createsuperuser --no-input --username "${CLOUDIGRADE_USER}" --email="${CLOUDIGRADE_USER}@example.com"

    export CLOUDIGRADE_TOKEN=$(oc rsh -c "${CONTAINER_NAME}" "${POD}" scl enable rh-python36 -- python manage.py drf_create_token "${CLOUDIGRADE_USER}" 2>/dev/null | sed -e ':a;N;$!ba;s/.*token \(.*\) for.*/\1/')
cat << EOF | oc rsh -c "${CONTAINER_NAME}" "${POD}" scl enable rh-python36 -- python manage.py shell
from django.contrib.auth.models import User
user = User.objects.get(email="$CLOUDIGRADE_USER@example.com")
user.set_password("$CLOUDIGRADE_PASSWORD")
user.save()
EOF

fi

unset -f uuid4
unset CONTAINER_NAME
