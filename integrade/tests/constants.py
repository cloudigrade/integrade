"""Constants shared by integrade tests."""

AWS_ACCOUNT_TYPE = 'AwsAccount'
"""AWS accounts are specified with this string for cloud account creation."""


EC2_TERMINATED_CODE = 48
"""Terminated EC2 instances have the state code of 48."""

RH_NETWORK_URL = 'https://stage.cloud.redhat.com/api'

QA_URL = 'https://qa.cloud.redhat.com/api/cloudigrade/v2/'

STAGE_URL = 'https://stage.cloud.redhat.com/api/cloudigrade/v2/'

SOURCES_URL = 'https://ci.cloud.redhat.com/api/sources/v1.0/'

SHORT_TIMEOUT = 1
MEDIUM_TIMEOUT = 10
LONG_TIMEOUT = 60
