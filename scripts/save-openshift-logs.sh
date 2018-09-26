#!/bin/sh

if [[ ${OPENSHIFT_PREFIX:-} ]]; then
    API_CONTAINER_NAME="${OPENSHIFT_PREFIX}cloudigrade-api"
    CELERY_BEAT_CONTAINER_NAME="${OPENSHIFT_PREFIX}cloudigrade-celery-beat"
    CELERY_WORKER_CONTAINER_NAME="${OPENSHIFT_PREFIX}cloudigrade-celery-worker"
else
    API_CONTAINER_NAME="cloudigrade-api"
    CELERY_BEAT_CONTAINER_NAME="cloudigrade-celery-beat"
    CELERY_WORKER_CONTAINER_NAME="cloudigrade-celery-worker"
fi

# we print out just the first running pod, which
# helps if there is a terminating pod kicking around or if we are
# running with multiple api pods
API_POD="$(oc get pods -o jsonpath='{.items[*].metadata.name}' --show-all=false -l name=${API_CONTAINER_NAME} | awk '{ print $1 }')"
CELERY_BEAT_POD="$(oc get pods -o jsonpath='{.items[*].metadata.name}' --show-all=false -l name=${CELERY_BEAT_CONTAINER_NAME} | awk '{ print $1 }')"
CELERY_WORKER_POD="$(oc get pods -o jsonpath='{.items[*].metadata.name}' --show-all=false -l name=${CELERY_WORKER_CONTAINER_NAME} | awk '{ print $1 }')"

if [[ ! "${API_POD}" ]]; then
    echo "Not able to find any pod for ${API_CONTAINER_NAME}"
    exit 1;
fi
if [[ ! "${CELERY_BEAT_POD}" ]]; then
    echo "Not able to find any pod for ${CELERY_BEAT_CONTAINER_NAME}"
    exit 1;
fi
if [[ ! "${CELERY_WORKER_POD}" ]]; then
    echo "Not able to find any pod for ${CELERY_WORKER_CONTAINER_NAME}"
    exit 1;
fi

# Save the logs
oc logs po/$CELERY_WORKER_POD -c $CELERY_WORKER_CONTAINER_NAME > "${REPORT_NAME:-$(date +"%Y-%M-%d")}-celery-worker.log"
oc logs po/$CELERY_BEAT_POD -c $CELERY_BEAT_CONTAINER_NAME > "${REPORT_NAME:-$(date +"%Y-%M-%d")}-celery-beat.log"
oc logs po/$API_POD -c $API_CONTAINER_NAME > "${REPORT_NAME:-$(date +"%Y-%M-%d")}-api.log"
