"""Tests for instances reports.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import random

import pytest

from integrade import api, config
from integrade.injector import inject_aws_cloud_account, inject_instance_data
from integrade.tests import urls, utils


API_DATETIME_FORMAT = '%Y-%m-%dT%H:%MZ'
REPORT_START_DATE = utils.utc_dt(2018, 1, 7).strftime(API_DATETIME_FORMAT)
REPORT_END_DATE = utils.utc_dt(2018, 1, 16).strftime(API_DATETIME_FORMAT)
EXPECTED_REPORT_DATA = {
    'daily_usage': [
        {
            'date': '2018-01-07T00:00:00Z',
            'openshift_instances': 1,
            'openshift_runtime_seconds': 86400.0,
            'openshift_memory_seconds': 86400.0,
            'openshift_vcpu_seconds': 86400.0,
            'rhel_instances': 0,
            'rhel_runtime_seconds': 0.0,
            'rhel_memory_seconds': 0.0,
            'rhel_vcpu_seconds': 0.0,
        },
        {
            'date': '2018-01-08T00:00:00Z',
            'openshift_instances': 1,
            'openshift_runtime_seconds': 86400.0,
            'openshift_memory_seconds': 86400.0,
            'openshift_vcpu_seconds': 86400.0,
            'rhel_instances': 1,
            'rhel_runtime_seconds': 68400.0,
            'rhel_memory_seconds': 68400.0,
            'rhel_vcpu_seconds': 68400.0,
        },
        {
            'date': '2018-01-09T00:00:00Z',
            'openshift_instances': 2,
            'openshift_runtime_seconds': 140400.0,
            'openshift_memory_seconds': 140400.0,
            'openshift_vcpu_seconds': 140400.0,
            'rhel_instances': 2,
            'rhel_runtime_seconds': 140400.0,
            'rhel_memory_seconds': 140400.0,
            'rhel_vcpu_seconds': 140400.0,
        },
        {
            'date': '2018-01-10T00:00:00Z',
            'openshift_instances': 2,
            'openshift_runtime_seconds': 172800.0,
            'openshift_memory_seconds': 172800.0,
            'openshift_vcpu_seconds': 172800.0,
            'rhel_instances': 2,
            'rhel_runtime_seconds': 104400.0,
            'rhel_memory_seconds': 104400.0,
            'rhel_vcpu_seconds': 104400.0,
        },
        {
            'date': '2018-01-11T00:00:00Z',
            'openshift_instances': 3,
            'openshift_runtime_seconds': 234000.0,
            'openshift_memory_seconds': 234000.0,
            'openshift_vcpu_seconds': 234000.0,
            'rhel_instances': 2,
            'rhel_runtime_seconds': 97200.0,
            'rhel_memory_seconds': 97200.0,
            'rhel_vcpu_seconds': 97200.0,
        },
        {
            'date': '2018-01-12T00:00:00Z',
            'openshift_instances': 3,
            'openshift_runtime_seconds': 259200.0,
            'openshift_memory_seconds': 259200.0,
            'openshift_vcpu_seconds': 259200.0,
            'rhel_instances': 2,
            'rhel_runtime_seconds': 162000.0,
            'rhel_memory_seconds': 162000.0,
            'rhel_vcpu_seconds': 162000.0,
        },
        {
            'date': '2018-01-13T00:00:00Z',
            'openshift_instances': 3,
            'openshift_runtime_seconds': 190800.0,
            'openshift_memory_seconds': 190800.0,
            'openshift_vcpu_seconds': 190800.0,
            'rhel_instances': 1,
            'rhel_runtime_seconds': 86400.0,
            'rhel_memory_seconds': 86400.0,
            'rhel_vcpu_seconds': 86400.0,
        },
        {
            'date': '2018-01-14T00:00:00Z',
            'openshift_instances': 2,
            'openshift_runtime_seconds': 118800.0,
            'openshift_memory_seconds': 118800.0,
            'openshift_vcpu_seconds': 118800.0,
            'rhel_instances': 1,
            'rhel_runtime_seconds': 32400.0,
            'rhel_memory_seconds': 32400.0,
            'rhel_vcpu_seconds': 32400.0,
        },
        {
            'date': '2018-01-15T00:00:00Z',
            'openshift_instances': 1,
            'openshift_runtime_seconds': 86400.0,
            'openshift_memory_seconds': 86400.0,
            'openshift_vcpu_seconds': 86400.0,
            'rhel_instances': 0,
            'rhel_runtime_seconds': 0.0,
            'rhel_memory_seconds': 0.0,
            'rhel_vcpu_seconds': 0.0,
        },
    ],
    'instances_seen_with_openshift': 3,
    'instances_seen_with_rhel': 3
}


@pytest.fixture(scope='module')
def instances_report_data():
    """Create instance usage data for the instance report tests.

    Create two cloud accounts and create some instance data for each of them.
    """
    user1 = utils.create_user_account()
    user2 = utils.create_user_account()
    auth1 = utils.get_auth(user1)
    auth2 = utils.get_auth(user2)
    plain_ami_id = str(random.randint(100000, 999999999999))
    rhel_ami_id = str(random.randint(100000, 999999999999))
    openshift_ami_id = str(random.randint(100000, 999999999999))
    rhel_openshift_ami_id = str(random.randint(100000, 999999999999))
    accounts1 = [
        inject_aws_cloud_account(
            user1['id'],
            name='greatest account ever',
        ),
        inject_aws_cloud_account(
            user1['id'],
            name='just another account',
        )
    ]

    # Run an unmetered instance from 3AM Jan 9th to 3AM the 11th
    inject_instance_data(
        accounts1[0]['id'],
        '',
        [
            utils.utc_dt(2018, 1, 9, 3, 0, 0),
            utils.utc_dt(2018, 1, 11, 3, 0, 0),
        ],
        ec2_ami_id=plain_ami_id,
    )
    # Run an OCP instance from 7AM Jan 11th to 5AM the 13th
    inject_instance_data(
        accounts1[0]['id'],
        'openshift',
        [
            utils.utc_dt(2018, 1, 11, 7, 0, 0),
            utils.utc_dt(2018, 1, 13, 5, 0, 0),
        ],
        ec2_ami_id=openshift_ami_id,
    )
    # Run an OCP instance from 4AM Jan 1st to 9PM the 31st
    inject_instance_data(
        accounts1[0]['id'],
        'openshift',
        [
            utils.utc_dt(2018, 1, 1, 4, 0, 0),
            utils.utc_dt(2018, 1, 31, 21, 0, 0),
        ],
        ec2_ami_id=openshift_ami_id,
    )
    # Run a RHEL instance with multiple runtime durations
    # Dec 24th to 29th
    # Jan 8th to 10th
    # Jan 11th on and off multiple times
    # Jan 20th to 23rd
    inject_instance_data(
        accounts1[0]['id'],
        'rhel',
        [
            utils.utc_dt(2017, 12, 24, 3, 0, 0),
            utils.utc_dt(2017, 12, 29, 3, 0, 0),
            utils.utc_dt(2018, 1, 8, 5, 0, 0),
            utils.utc_dt(2018, 1, 10, 5, 0, 0),
            
            utils.utc_dt(2018, 1, 11, 5, 0, 0),
            utils.utc_dt(2018, 1, 11, 6, 0, 0),
            utils.utc_dt(2018, 1, 11, 7, 0, 0),
            utils.utc_dt(2018, 1, 11, 8, 0, 0),
            utils.utc_dt(2018, 1, 11, 9, 0, 0),
            utils.utc_dt(2018, 1, 11, 10, 0, 0),

            utils.utc_dt(2018, 2, 20, 5, 0, 0),
            utils.utc_dt(2018, 2, 23, 5, 0, 0),
        ],
        ec2_ami_id=rhel_ami_id,
    )
    # Run a RHEL instance with multiple runtime durations,
    # on a different account
    inject_instance_data(
        accounts1[1]['id'],
        'rhel',
        [
            utils.utc_dt(2018, 1, 12, 0, 0, 0),
            utils.utc_dt(2018, 1, 12, 6, 0, 0),
            utils.utc_dt(2018, 1, 12, 7, 0, 0),
            utils.utc_dt(2018, 1, 12, 8, 0, 0),
            utils.utc_dt(2018, 1, 12, 9, 0, 0),
            utils.utc_dt(2018, 1, 12, 23, 0, 0),
        ],
        ec2_ami_id=rhel_ami_id,
    )
    # Run a RHEL+OCP instance from Jan 9th at 9AM to the 14th at 9AM
    inject_instance_data(
        accounts1[1]['id'],
        'rhel,openshift',
        [
            utils.utc_dt(2018, 1, 9, 9, 0, 0),
            utils.utc_dt(2018, 1, 14, 9, 0, 0),
        ],
        ec2_ami_id=rhel_openshift_ami_id,
    )

    return user1, user2, auth1, auth2, accounts1


def test_instances_report(instances_report_data):
    """Test that instances report provides expected results.

    :id: 7dd5ac11-7429-4030-9996-dbf3684f39e1
    :description: Test that regular users can retrieve their own instances
        report.
    :steps:
        1) Add a cloud account for a regular user
        2) Add some instance usage data for the following images: blank, RHEL,
           OpenShift and RHEL + OpenShift
        3) Generate an instances report for a given period.
        4) Ensure the report only shows information about the usage on the
           given period.
    :expectedresults:
        An instances report can be generated and the information provided is
        accurate.
    """
    user1, user2, auth1, auth2, accounts1 = instances_report_data
    client = api.Client(response_handler=api.json_handler)

    response = client.get(
        urls.REPORT_INSTANCES,
        params={
            'start': REPORT_START_DATE,
            'end': REPORT_END_DATE,
        },
        auth=auth1
    )

    for i, exp_data in enumerate(EXPECTED_REPORT_DATA['daily_usage']):
        seen_day = response['daily_usage'][i]
        vcpu = seen_day['rhel_vcpu_seconds']
        runtime = seen_day['rhel_runtime_seconds']
        assert exp_data == seen_day, (runtime - vcpu) / 60 / 60  # seen_day['date']


def test_superuser_instances_report(instances_report_data):
    """Test that a superuser can retrieves a regular user's instances report.

    :id: d222617b-9304-4081-9b95-f1a193412b6e
    :description: Test that a superuser can retrieve a regular user's instances
        report.
    :steps:
        1) Add a cloud account for a regular user
        2) Add some instance usage data for the following images: blank, RHEL,
           OpenShift and RHEL + OpenShift
        3) As a superuser, generate an instances report for a given period
           providing a regular user ID.
        4) Ensure the report only shows information about the usage on the
           given period.
    :expectedresults:
        An instances report can be generated by a superuser impersonating a
        regular user and the information provided is accurate.
    """
    user1, user2, auth1, auth2, accounts1 = instances_report_data
    cfg = config.get_config()
    superuser_auth = api.TokenAuth(cfg.get('superuser_token'))
    client = api.Client(response_handler=api.json_handler)

    response = client.get(
        urls.REPORT_INSTANCES,
        params={
            'start': REPORT_START_DATE,
            'end': REPORT_END_DATE,
            'user_id': user1['id'],
        },
        auth=superuser_auth
    )

    assert response == EXPECTED_REPORT_DATA, response


def test_another_users_instances_report(instances_report_data):
    """Test that a regular can't retrieve another regular user's instances report.

    :id: abc19456-327d-4707-b8d6-7a99a6151c1e
    :description: Test that a regular user can't retrieve a regular user's
        instances report.
    :steps:
        1) Create two regular users
        2) Add a cloud account for each user.
        3) Add some instance usage data for one of the regular users, using the
           following images: blank, RHEL, OpenShift and RHEL + OpenShift
        4) As the regular user that does not have the usage data, generate its
           instances report and ensure it is blank.
        5) As the regular user that does not have the usage data, try to
           impersonate the other regular user and generate an instances report.
        6) Ensure that a regular user can't impersonate another regular user
           and retrieve their instances report. And its own instances report
           will be returned.
    :expectedresults:
        An instances report cannot be generated by a regular impersonating
        another regular user. A regular user will always retrieve its own
        instances report, even when trying to impersonate another regular user.
    """
    user1, user2, auth1, auth2, accounts1 = instances_report_data
    client = api.Client(response_handler=api.json_handler)

    # Ensure that the second user's instances report is empty
    response = client.get(
        urls.REPORT_INSTANCES,
        params={
            'start': REPORT_START_DATE,
            'end': REPORT_END_DATE,
        },
        auth=auth2
    )
    assert response['instances_seen_with_openshift'] == 0, response
    assert response['instances_seen_with_rhel'] == 0, response
    for usage in response['daily_usage']:
        assert usage['openshift_instances'] == 0
        assert usage['openshift_runtime_seconds'] == 0
        assert usage['rhel_instances'] == 0
        assert usage['rhel_runtime_seconds'] == 0

    # Try to impersonate the first user and retrieve their instances report
    impersonate_response = client.get(
        urls.REPORT_INSTANCES,
        params={
            'start': REPORT_START_DATE,
            'end': REPORT_END_DATE,
            'user_id': user1['id'],
        },
        auth=auth2
    )
    assert impersonate_response == response
