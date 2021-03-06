if [[ "$1" ]]; then
    export BRANCH_NAME=$1
else
    export BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
fi
if [ -f ".env-pre-setup" ]; then
    echo source .env-pre-setup
fi
export SHORT_NAME=$(echo $BRANCH_NAME | cut -c 1-29)

# Name of your branch
echo export BRANCH_NAME=${BRANCH_NAME}
echo export SHORT_NAME=$(echo $BRANCH_NAME | cut -c 1-29)

echo export AWS_DEFAULT_REGION=us-east-1

# The rest of the items needed can be derived from above
echo export AWS_QUEUE_PREFIX="${BRANCH_NAME}-"
echo export CLOUDTRAIL_PREFIX="review-${BRANCH_NAME}"
echo export USE_HTTPS=True
echo export CLOUDIGRADE_BASE_URL="review-${BRANCH_NAME}.5a9f.insights-dev.openshiftapps.com"
echo export OPENSHIFT_PREFIX="c-review-${SHORT_NAME}-"
echo export AWS_S3_BUCKET_NAME="${AWS_QUEUE_PREFIX}cloudigrade-s3"

echo
echo "# setup-env.sh expects AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_*******_DEV**CUSTOMER set"
echo "# you may add them to .env-pre-setup"
echo "# to use:  eval \$(scripts/setup-env.sh ${BRANCH_NAME})"