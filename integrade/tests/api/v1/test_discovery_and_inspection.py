"""Tests for cloud accounts.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import gzip
import json
import operator
import os
import random
import sys
import time
from collections import namedtuple
from copy import deepcopy
from datetime import datetime, timezone
from pprint import pformat
from time import sleep
from urllib.parse import urlparse

import boto3

import click

import pytest

from integrade import api, config, exceptions
from integrade.constants import (
    CLOUD_ACCESS_AMI_NAME,
    MARKETPLACE_AMI_NAME,
)
from integrade.exceptions import MissingConfigurationError
from integrade.tests import aws_utils, urls
from integrade.tests.aws_utils import aws_image_config_needed
from integrade.tests.constants import AWS_ACCOUNT_TYPE
from integrade.tests.utils import drop_account_data, get_auth

ImageData = namedtuple(
    'ImageData',
    'image_type image_name source_image instance_id'
)
"""Object to assist in passing around data shared by tests using an image."""

BadEvent = namedtuple('BadEvent', 'name data gzipped')
"""Object for describing what type of bad event data to place in s3 bucket."""

power_on_events = [
    'RunInstances',
    'StartInstances',
    'StartInstance'
]
"""List of possible power on events for use in mock cloudtrail event data."""


bad_events = [
    BadEvent('textfile', b'bad!', False),
    BadEvent('badjson', b'"{}', True),
    BadEvent('badinstanceid', None, True),
    BadEvent('badawsaccount', None, True),
]
"""List of types of bad events that in the past have caused bugs."""

power_off_events = [
    'TerminateInstances',
    'StopInstances',
    'TerminateInstanceInAutoScalingGroup'
]
"""List of possible power off events for use in mock cloudtrail event data."""

image_test_matrix = [
    ('owned', 'rhel-extra-detection-methods', 'inspected'),
    ('owned', 'rhel-openshift-extra-detection-methods', 'inspected'),
    ('owned', 'centos', 'inspected'),
    ('owned', 'centos-openshift', 'inspected'),
    ('owned', 'rhel', 'inspected'),
    ('owned', 'rhel-openshift', 'inspected'),
    ('community', 'ubuntu', 'inspected'),
    ('community', 'windows', 'inspected'),
    ('community', 'fedora', 'inspected'),
    ('community', 'opensuse', 'inspected'),
    ('marketplace', 'rhel', 'inspected'),
    ('marketplace', 'ubuntu', 'inspected'),
    ('marketplace', 'windows', 'inspected'),
    ('private-shared', 'rhel', 'inspected'),
    ('private-shared', 'centos', 'inspected'),
    ('private-shared', 'centos-openshift', 'inspected'),
    ('private-shared', 'ubuntu-openshift', 'inspected'),
    ('private-shared', 'centos', 'inspected'),
]
"""List of images categorized by ownership as well as expected terminal status.
Could be expanded in the future to include images we expect errors for.
To add images here, the corresponding information must be present in the aws
config file. See the README.md in the root integrade directory for more
information."""

bypass_inspection_matrix = [
    ('private-shared', CLOUD_ACCESS_AMI_NAME, 'inspected'),
    ('private-shared', MARKETPLACE_AMI_NAME, 'inspected'),
]
"""List of images that should automatically bypass inspection process due to
the fact that they have either 'Access2' or 'hourly2' in their name and belong
to a specific account."""

IMAGES_TO_TEST = [
    random.choice(bypass_inspection_matrix),
    random.choice(image_test_matrix),
]
POWER_ON_EVENT_TO_TEST = random.choice(power_on_events)
POWER_OFF_EVENT_TO_TEST = random.choice(power_off_events)
BAD_EVENT_TO_TEST = random.choice(bad_events)


@pytest.fixture(params=power_on_events,
                ids=power_on_events)
def power_on_event(request):
    """Provide power on event to test."""
    if request.param == POWER_ON_EVENT_TO_TEST:
        return request.param
    else:
        pytest.skip(f'Testing only {POWER_ON_EVENT_TO_TEST}')


@pytest.fixture(params=power_off_events,
                ids=power_off_events)
def power_off_event(request):
    """Provide power off event to test."""
    if request.param == POWER_OFF_EVENT_TO_TEST:
        return request.param
    else:
        pytest.skip(f'Testing only {POWER_OFF_EVENT_TO_TEST}')


@pytest.fixture(params=bad_events,
                ids=[e.name for e in bad_events])
def bad_event(request):
    """Provide bad event to place in s3 bucket to test."""
    if request.param == BAD_EVENT_TO_TEST:
        return request.param
    else:
        pytest.skip(f'Testing only {BAD_EVENT_TO_TEST}')


@pytest.fixture(params=[config.get_config()['aws_profiles'][0]],
                ids=operator.itemgetter('name'), scope='module')
def aws_profile(request):
    """Provide the aws profile to use to test."""
    return request.param


@pytest.fixture(
    params=[IMAGES_TO_TEST],
    ids=[''],
    scope='module'
)
def image_fixture(request, aws_profile):
    """Power on instances for each image and terminate after tests."""
    images = []
    for image_to_test in request.param:
        aws_profile_name = aws_profile['name']
        # Create some instances to detect on creation, random choice from every
        # configured image type (private, owned, marketplace, community)
        image_type, image_name, expected_state = image_to_test
        source_images = [
            image for image in aws_profile['images'][image_type]
            if image['name'] == image_name
        ]
        assert source_images, f'Found no images from profile! {aws_profile}'
        source_image = source_images[0]
        # Run an instance
        instance_id = aws_utils.run_instances_by_name(
            aws_profile_name, image_type, image_name, count=1)[0]

        def terminate_instance():
            aws_utils.terminate_instance((aws_profile_name, instance_id))
        request.addfinalizer(terminate_instance)

        final_image_data = ImageData(image_type,
                                     image_name,
                                     source_image,
                                     instance_id)
        images.append(final_image_data)

    yield images


def get_s3_bucket_name():
    """Get the cloudigrade bucket name and raise an exception if not found."""
    bucket_name = config.get_config()['cloudigrade_s3_bucket']
    if not bucket_name:
        raise MissingConfigurationError(
            'Need to know the name of cloudigrade\'s s3'
            ' bucket to mock events!'
        )
    return bucket_name


def create_event(instance_id, aws_profile, event_type, time=None,
                 data=None, gzipped=True):
    """Create an event and place it in the cloudigrade s3 bucket."""
    bucket_name = get_s3_bucket_name()
    s3 = boto3.resource('s3')
    cloudi_bucket = s3.Bucket(bucket_name)
    if not time:
        time = datetime.now(timezone.utc).astimezone().isoformat()
    # create event
    if data is None:
        mock_cloudtrail_event = {
            'Records': [
                {
                    'userIdentity': {
                        'accountId': aws_profile['account_number']},
                    'awsRegion': os.environ.get('AWS_DEFAULT_REGION',
                                                'us-east-1'),
                    'eventSource': 'ec2.amazonaws.com',
                    'eventName': event_type,
                    'eventTime': time,
                    'responseElements': {
                        'instancesSet': {
                            'items': [
                                {
                                    'instanceId': instance_id
                                }
                            ]
                        }
                    }
                }
            ]
        }
        data = bytes(json.dumps(mock_cloudtrail_event), encoding='utf-8')
    aws_profile_name = aws_profile['name']
    upload_file = f'{aws_profile_name}-{event_type}-{instance_id}.json.gz'
    if gzipped:
        with gzip.open(upload_file, 'wb') as f:
            f.write(data)
    else:
        with open(upload_file, 'wb') as f:
            f.write(data)
    path = f'AWSLogs/mock_events/{upload_file}'
    cloudi_bucket.upload_file(upload_file, path)
    os.remove(upload_file)
    return data


def wait_for_cloudigrade_instance(
        instance_id, auth, timeout=800, sleep_period=15):
    """Wait for image to be inspected and assert on findings.

    :param instance_id: The ec2 instance id you expect to find.
    :param auth: the auth object for using with the server to authenticate as
        the user in question.

    :raises: AssertionError if the image is not inspected or if the results do
        not match the expected results for product identification.
    """
    # Wait, keeping track of what images are inspected
    client = api.Client(authenticate=False, response_handler=api.json_handler)
    start = time.time()
    timepassed = 0
    sys.stdout.write('\n')
    with click.progressbar(
            length=timeout,
            label=f'Waiting for instance {instance_id} to appear in'
            ' cloudigrade'
    ) as bar:
        while True:
            list_instances = client.get(urls.INSTANCE, auth=auth)
            found_instances = [instance['ec2_instance_id']
                               for instance in list_instances['results']]
            if instance_id in found_instances:
                return found_instances
            sleep(sleep_period)
            now = time.time()
            timepassed = now - start
            bar.update(timepassed)
            if timepassed >= timeout:
                return found_instances


def wait_for_inspection(
        source_image, expected_state, auth, timeout=3600, sleep_period=30):
    """Wait for image to be inspected and assert on findings.

    :param source_image: Dictionary with the following information about
        the image::
                {
                 'name': 'centos-openshift',
                 'image_id': 'ami-0f75a482c0696dc99',
                 'is_rhel': False,
                 'is_openshift': True
                 }
    :param auth: the auth object for using with the server to authenticate as
        the user in question.

    :raises: AssertionError if the image is not inspected or if the results do
        not match the expected results for product identification.
    """
    # Wait, keeping track of what images are inspected
    client = api.Client(authenticate=False, response_handler=api.json_handler)
    source_image_id = source_image['image_id']
    start = time.time()
    timepassed = 0
    sys.stdout.write('\n')
    status = 'ABSENT'
    with click.progressbar(
            length=timeout,
            label=f'Waiting for inspection of {source_image["image_id"]}'
    ) as bar:
        while True:
            server_info = client.get(urls.IMAGE, auth=auth)
            if server_info:
                server_info = [
                    image for image in server_info['results'] if
                    image['ec2_ami_id'] == source_image_id
                ]
                if server_info:
                    server_info = server_info[0]
                    status = server_info['status']
                    inspection_json = pformat(server_info['inspection_json'])
            if status == 'error' and expected_state != 'error':
                break
            if status in ['pending', 'preparing', 'inspecting', 'ABSENT']:
                sleep(sleep_period)
                now = time.time()
                timepassed = now - start
                bar.update(timepassed)

            if status == expected_state:
                break
            if timepassed >= timeout:
                break
    # assert the image did reach expected state before timeout
    assert status == expected_state, f'\nState was {status} and inspection ' \
                                     f' json was:\n{inspection_json}'

    fact_keys = [
        'rhel',
        'openshift',
        'rhel_enabled_repos_found',
        'rhel_product_certs_found',
        'rhel_release_files_found',
        'rhel_signed_packages_found'
    ]
    bypass_inspection_names = [
        'Access2',
        'access2',
        'Hourly2',
        'hourly2',
    ]
    bypass = False
    for name in bypass_inspection_names:
        if name in server_info['name']:
            assert server_info['status'] == 'inspected'
            bypass = True
    if not bypass:
        for key in fact_keys:
            server_result = server_info[key]
            known_fact = source_image.get(key)
            if known_fact:
                assert server_result == known_fact, \
                    f'Server result for {key} was {server_result}. This\n' \
                    f' does not match expected result {known_fact} for\n' \
                    f'image id {source_image["image_id"]} named\n' \
                    f'{source_image["name"]}'


def wait_for_instance_event(
        instance_id,
        event_type,
        auth,
        aws_profile_name,
        event,
        timeout=1200,
        sleep_period=30):
    """Wait until an event of the type specified occurs for the instance.

    :raises: integrade.exceptions.EventTimeoutError if no such event is found
        in the time allowed.
    """
    client = api.Client(authenticate=False, response_handler=api.json_handler)
    timepassed = 0
    sys.stdout.write('\n')
    with click.progressbar(
            length=timeout,
            label=f'Waiting for {event_type} event') as bar:
        while True:
            events = client.get('/api/v1/event/', auth=auth).get('results')
            for event in events:
                if event.get('event_type') == event_type:
                    instance_url = event.get('instance')
                    instance_path = urlparse(instance_url).path
                    this_instance_id = client.get(
                        instance_path, auth=auth).get('ec2_instance_id')
                    if this_instance_id == instance_id:
                        return
            sleep(sleep_period)
            timepassed += sleep_period
            bar.update(timeout / timepassed)
            if timepassed >= timeout:
                break
    event = pformat(event)
    raise exceptions.EventTimeoutError(
        f'\nTimed out while waiting for {event_type} event for instance'
        f'\nwith instance id {instance_id} for the aws profile'
        f'\n{aws_profile_name}. The event data was:\n{event}')


@pytest.mark.inspection
@aws_image_config_needed
@pytest.mark.serial_only
@pytest.mark.parametrize('test_case', IMAGES_TO_TEST,
                         ids=[
                             '{}-{}'.format(item[0], item[1])
                             for item in IMAGES_TO_TEST],
                         )
def test_find_running_instances(
        test_case,
        aws_profile,
        cloudtrails_to_delete,
        image_fixture,
):
    """Ensure instances are discovered on account creation.

    :id: 741a0fad-45a8-4aab-9daa-11adad458d34
    :description: Ensure running instances are discovered and the images
        inspected.
    :steps: 1) Create a user and authenticate with their password
        2) Create instances based off of a non-windows image
        3) Send a POST with the cloud account information to 'api/v1/account/'
        4) Send a GET to 'api/v1/instance/' and expect to get the instances we
            created
        5) Send a GET to 'api/v1/image/' and expect to get the image that
            the instances were based off of.
        6) Keep checking to see that the images progress from "pending",
            "preparing", "inspecting", to "inspected"
    :expectedresults:
        1) The server returns a 201 response with the information
            of the created account.
        2) We get 200 responses for our GET requests and information about
            the images includes inspection state information.
        3) The images are eventually inspected.
    """
    image_type, image_name, expected_state = test_case
    bypass_inspection = False
    if image_fixture[0].image_name == test_case[1]:
        image_fixture = image_fixture[0]
        bypass_inspection = True
    else:
        image_fixture = image_fixture[-1]

    source_image = image_fixture.source_image
    source_image_id = source_image['image_id']
    instance_id = image_fixture.instance_id
    if image_name != image_fixture.image_name \
            or image_type != image_fixture.image_type:
        pytest.skip(f'Only testing {IMAGES_TO_TEST}')
    drop_account_data()

    auth = get_auth()
    client = api.Client(authenticate=False, response_handler=api.json_handler)
    aws_profile_name = aws_profile['name']
    aws_utils.delete_cloudtrail(
        (aws_profile_name, aws_profile['cloudtrail_name']))
    aws_utils.clean_cloudigrade_queues()

    # Create cloud account on cloudigrade
    cloud_account = {
        'name': aws_profile['name'],
        'account_arn': aws_profile['arn'],
        'resourcetype': AWS_ACCOUNT_TYPE
    }
    client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )

    # Cleanup cloudtrail after test so events
    # don't keep coming into the cloudigrade s3 bucket
    cloudtrails_to_delete.append(
        (aws_profile['name'], aws_profile['cloudtrail_name'])
    )

    # Look for instances that should have been discovered
    # upon account creation.
    found_instances = wait_for_cloudigrade_instance(instance_id, auth)
    assert instance_id in found_instances

    # Look for images that should have been discovered
    # upon account creation.
    list_images = client.get(urls.IMAGE, auth=auth)
    found_images = [image['ec2_ami_id'] for image in list_images['results']]
    assert source_image_id in found_images
    if bypass_inspection:
        wait_for_inspection(source_image, expected_state, auth, timeout=200)
    else:
        wait_for_inspection(source_image, expected_state, auth)


@pytest.mark.inspection
@aws_image_config_needed
@pytest.mark.serial_only
def test_on_off_events(
    aws_profile,
    cloudtrails_to_delete,
    power_on_event,
    power_off_event,
    bad_event,
    image_fixture,
):
    """Ensure power on and power off events continue to be discovered.

    :id: 5c57b04a-dbe7-4ed7-ac6d-644bfa73d94f
    :description: Ensure power on and power off events are recorded when
        instances are powered on and either stopped or terminated.
    :steps: 1) Create a user and authenticate with their password
        2) Create an instance on AWS and stop it, to ensure we have a valid
            instance to reference.
        2) Send a POST with the cloud account information to 'api/v1/account/'
        3) Mock a power on event in the cloudigrade s3 bucket
        4) Mock a bad event in the cloudigrade bucket to make sure it is
            resilient to bad data also in the bucket.
        5) Keep checking '/api/v1/event/' until a 'power_on' event is found.
        6) Mock a power off event in the cloudigrade s3 bucket
        7) Keep checking '/api/v1/event/' until a 'power_off' event is found.
    :expectedresults:
        1) The server returns a 201 response with the information
            of the created account.
        2) We get 200 responses for our GET requests to the `/api/v1/event`
            endpoint.
        3) The power on events are eventually recorded.
        4) The bad events are ignored.
        5) The power on events events eventually recorded.
    """
    drop_account_data()

    # check and make sure the instance is not running
    client = aws_utils.aws_session(aws_profile['name']).client('ec2')
    reservations = client.describe_instances(Filters=[{
        'Name': 'instance-state-name',
        'Values': [
            'running',
        ]}]).get('Reservations', [])
    running_instances = []
    for reservation in reservations:
        running_instances.extend([inst['InstanceId']
                                  for inst in reservation.get(
                                      'Instances', [])])
    # if it is running, go ahead and stop it so it does not provide
    # a "power_on" event on cloud account registration and circumvent
    # what we are trying to test.
    image_fixture = image_fixture[1]
    if image_fixture.instance_id in running_instances:
        client.stop_instances(InstanceIds=[image_fixture.instance_id])

    auth = get_auth()
    client = api.Client(authenticate=False, response_handler=api.json_handler)
    aws_profile_name = aws_profile['name']
    # Make sure we are working with a clean slate and cloudigrade
    # does not get data from previous registration.
    aws_utils.delete_cloudtrail(
        (aws_profile_name, aws_profile['cloudtrail_name']))
    aws_utils.clean_cloudigrade_queues()
    instance_id = image_fixture.instance_id
    bad_event_instance_id = image_fixture.instance_id
    bad_event_aws_profile = deepcopy(aws_profile)
    # Create cloud account on cloudigrade
    cloud_account = {
        'name': aws_profile['name'],
        'account_arn': aws_profile['arn'],
        'resourcetype': AWS_ACCOUNT_TYPE
    }
    client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )

    # Cleanup cloudtrail after test so events
    # don't keep coming into the cloudigrade s3 bucket
    cloudtrails_to_delete.append(
        (aws_profile['name'], aws_profile['cloudtrail_name'])
    )

    power_on_event = create_event(
        instance_id,
        aws_profile,
        event_type=power_on_event)
    if bad_event.name == 'badawsaccount':
        bad_event_aws_profile['account_number'] = 123
    elif bad_event.name == 'badinstanceid':
        bad_event_instance_id = 'i-123'
    for _ in range(random.randint(1, 10)):
        create_event(
            bad_event_instance_id,
            bad_event_aws_profile,
            event_type='BadEvent',
            data=bad_event.data,
            gzipped=bad_event.gzipped
        )

    wait_for_instance_event(
        instance_id,
        'power_on',
        auth,
        aws_profile_name,
        power_on_event
    )

    power_off_event = create_event(
        instance_id,
        aws_profile,
        event_type=power_off_event)
    wait_for_instance_event(
        instance_id,
        'power_off',
        auth,
        aws_profile_name,
        power_off_event
    )
