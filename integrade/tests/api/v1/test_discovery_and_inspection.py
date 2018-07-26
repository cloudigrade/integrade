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
from datetime import datetime, timezone
from time import sleep
from urllib.parse import urlparse

import boto3

import pytest

from integrade import api, config, exceptions
from integrade.tests import aws_utils, urls
from integrade.tests.aws_utils import aws_image_config_needed
from integrade.tests.constants import AWS_ACCOUNT_TYPE
from integrade.tests.utils import get_auth

cloudigrade_bucket_needed = pytest.mark.skipif(
        config.get_config()['cloudigrade_s3_bucket'] == '',
        reason='Cloudigrade s3 bucket name missing.'
        )


def create_event(instance_id, aws_profile, event_type, time=None):
    """Create an event and place it in the cloudigrade s3 bucket."""
    bucket_name = config.get_config()['cloudigrade_s3_bucket']
    if not bucket_name:
        pytest.skip(
            reason='Need to know the name of cloudigrade\'s s3'
            ' bucket to mock events!')
    s3 = boto3.resource('s3')
    cloudi_bucket = s3.Bucket(bucket_name)
    if not time:
        time = datetime.now(timezone.utc).astimezone().isoformat()
    # create event
    mock_cloudtrail_event = {
        'Records': [
            {
                'userIdentity': {
                    'accountId': aws_profile['account_number']},
                'awsRegion': os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
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
    aws_profile_name = aws_profile['name']
    gzip_file = f'{aws_profile_name}-{event_type}-{instance_id}.json.gz'
    with gzip.open(gzip_file, 'wb') as f:
        f.write(bytes(json.dumps(mock_cloudtrail_event), encoding='utf-8'))
    path = f'AWSLogs/mock_events/{gzip_file}'
    cloudi_bucket.upload_file(gzip_file, path)
    os.remove(gzip_file)


def wait_for_inspection(source_image, auth, timeout=2400):
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
    while True:
        status = client.get(urls.IMAGE,
                            params={'ec2_ami_id': source_image_id},
                            auth=auth)['results'][0]['status']
        if status in ['pending', 'preparing', 'inspecting']:
            sleep(60)
            timeout -= 60
        if status == 'inspected' or timeout < 0:
            break

    # assert the image did get inspected before the timeout
    assert status == 'inspected'

    server_info = client.get(urls.IMAGE,
                             params={'ec2_ami_id': source_image_id},
                             auth=auth)['results'][0]
    is_rhel = server_info['rhel']
    is_openshift = server_info['openshift']
    assert is_rhel == source_image.get('is_rhel', False)
    assert is_openshift == source_image.get('is_openshift', False)


def wait_for_instance_event(
        instance_id,
        event_type,
        auth,
        aws_profile_name,
        timeout=2400):
    """Wait until an event of the type specified occurs for the instance.

    :raises: integrade.exceptions.EventTimeoutError if no such event is found
        in the time allowed.
    """
    client = api.Client(authenticate=False, response_handler=api.json_handler)
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
        sleep(60)
        timeout -= 60
        if timeout < 0:
            break
    raise exceptions.EventTimeoutError(
        f'Timed out while waiting for {event_type} event for instance'
        f' with instance id {instance_id} for the aws profile'
        f' {aws_profile_name}')


image_to_test = [random.choice([
    ('owned', 'centos'),
    ('community', 'ubuntu'),
])]


@pytest.mark.run_first
@aws_image_config_needed
@pytest.mark.serial_only
@pytest.mark.parametrize('image_to_run', image_to_test, ids=[
                         '{}-{}'.format(item[0], item[1])
                         for item in image_to_test]
                         )
@pytest.mark.parametrize('aws_profile',
                         [config.get_config()['aws_profiles'][0]],
                         ids=operator.itemgetter('name'))
def test_find_running_instances(drop_account_data,
                                cloudtrails_to_delete,
                                image_to_run,
                                instances_to_terminate,
                                aws_profile
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
    auth = get_auth()
    client = api.Client(authenticate=False, response_handler=api.json_handler)
    aws_profile_name = aws_profile['name']
    aws_utils.delete_cloudtrail(
        (aws_profile_name, aws_profile['cloudtrail_name']))
    aws_utils.clean_cloudigrade_queues()
    # Create some instances to detect on creation, random choice from every
    # configured image type (private, owned, marketplace, community)
    image_type, image_name = image_to_run
    source_image = [
        image for image in aws_profile['images'][image_type]
        if image['name'] == image_name
    ][0]
    source_image_id = source_image['image_id']
    # Run an instance
    instance_id = aws_utils.run_instances_by_name(
        aws_profile_name, image_type, image_name, count=1)[0]

    # Add new instances to list of instances to terminate after test
    instances_to_terminate.append((aws_profile_name, instance_id))

    # Create cloud account on cloudigrade
    cloud_account = {
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
    list_instances = client.get(urls.INSTANCE, auth=auth)
    found_instances = [instance['ec2_instance_id']
                       for instance in list_instances['results']]
    assert instance_id in found_instances

    # No need for the instance to run any longer
    aws_utils.stop_instance((aws_profile_name, instance_id))

    # Look for images that should have been discovered
    # upon account creation.
    list_images = client.get(urls.IMAGE, auth=auth)
    found_images = [image['ec2_ami_id'] for image in list_images['results']]
    assert source_image_id in found_images
    wait_for_inspection(source_image, auth)


power_on_event_to_test = [random.choice([
    'RunInstances',
    'StartInstances',
    # see https://gitlab.com/cloudigrade/cloudigrade/issues/447
    # 'StartInstance'
])]

power_off_event_to_test = [random.choice([
    'TerminateInstances',
    'StopInstances',
    # see https://gitlab.com/cloudigrade/cloudigrade/issues/447
    # 'TerminateInstanceInAutoScalingGroup'
])]


@pytest.mark.run_first
@aws_image_config_needed
@cloudigrade_bucket_needed
@pytest.mark.serial_only
@pytest.mark.parametrize('power_off_event', power_off_event_to_test)
@pytest.mark.parametrize('power_on_event', power_on_event_to_test)
@pytest.mark.parametrize('image_to_run', image_to_test, ids=[
                         '{}-{}'.format(item[0], item[1])
                         for item in image_to_test]
                         )
@pytest.mark.parametrize('aws_profile',
                         [config.get_config()['aws_profiles'][0]],
                         ids=operator.itemgetter('name'))
def test_on_off_events(
    aws_profile,
    cloudtrails_to_delete,
    power_on_event,
    power_off_event,
    image_to_run,
    instances_to_terminate,
    drop_account_data,
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
        6) Keep checking '/api/v1/event/' until a 'power_on' event is found.
        7) Mock a power off event in the cloudigrade s3 bucket
        8) Keep checking '/api/v1/event/' until a 'power_off' event is found.
    :expectedresults:
        1) The server returns a 201 response with the information
            of the created account.
        2) We get 200 responses for our GET requests to the `/api/v1/event`
            endpoint.
        3) The events are eventually recorded.
    """
    auth = get_auth()
    client = api.Client(authenticate=False, response_handler=api.json_handler)
    aws_profile_name = aws_profile['name']
    # Make sure we are working with a clean slate and cloudigrade
    # does not get data from previous registration.
    # see
    # https://gitlab.com/cloudigrade/cloudigrade/issues/452#unrecognized-aws-account
    aws_utils.delete_cloudtrail(
        (aws_profile_name, aws_profile['cloudtrail_name']))
    aws_utils.clean_cloudigrade_queues()
    image_type, image_name = image_to_run
    source_image = [
        image for image in aws_profile['images'][image_type]
        if image['name'] == image_name
    ][0]
    # Run an instance
    instance_id = aws_utils.run_instances_by_name(
        aws_profile_name, image_type, image_name, count=1)[0]
    # Let it run for a short while and then stop it, we just
    # need for it to have existed for some amount of time to
    # create events for it in the future.
    sleep(30)
    aws_utils.stop_instance((aws_profile_name, instance_id))
    # Add new instances to list of instances to terminate after test
    instances_to_terminate.append((aws_profile_name, instance_id))

    # Create cloud account on cloudigrade
    cloud_account = {
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

    create_event(instance_id, aws_profile, event_type=power_on_event)

    wait_for_instance_event(
        instance_id,
        'power_on',
        auth,
        aws_profile_name
    )

    create_event(instance_id, aws_profile, event_type=power_off_event)
    wait_for_instance_event(
        instance_id,
        'power_off',
        auth,
        aws_profile_name
    )

    wait_for_inspection(source_image, auth)
