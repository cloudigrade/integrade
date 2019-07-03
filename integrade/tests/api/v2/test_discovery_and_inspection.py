"""Tests for cloud accounts.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import functools
import logging
from collections import namedtuple
from datetime import datetime, timedelta
from time import sleep
from uuid import uuid4

import pytest

from integrade import api, config
from integrade.tests import aws_utils
from integrade.tests.constants import (
    LONG_TIMEOUT,
    MEDIUM_TIMEOUT,
)
from integrade.tests.utils import delete_preexisting_accounts


_logger = logging.getLogger(__name__)

ImageData = namedtuple(
    'ImageData',
    'image_type image_name source_image instance_id'
)
"""Object to assist in passing around data shared by tests using an image."""


def all_the_images():
    """Provide a list of all available images to test."""
    aws_profile = config.get_config()['aws_profiles'][0]
    all_images = []
    image_types = aws_profile['images'].keys()
    for image_type in image_types:
        for image in aws_profile['images'][image_type]:
            all_images.append((image_type, image['name'], 'inspected'))
    return all_images


def _get_object_with_timeout(client, path, timeout):
    """
    Repoll a cloudigrade path until some data is returned.

    Args:
      client: An API client
      path (string): An enpoint located at /v2/{path}
      timeout (int): timeout time in minutes
    """
    start_time = datetime.now()
    data = []
    while datetime.now() < start_time+timedelta(minutes=timeout):
        objects = client.request('get', path).json()
        count = objects['meta']['count']
        if count != 0:
            data.extend(objects['data'])
            while objects['links']['next'] is not None:
                objects = client.request(
                    'get', objects['links']['next']).json()
                data.extend(objects['data'])
            return data
        else:
            sleep(5)

    _logger.info('No objects at %s were found before timeout.', path)


def _get_instance_id_with_ec2_instance_id(ec2_instance_id, instances):
    """
    Get the instance id of a given ec2 instance with ec2_instance_id.

    Return None if no ec2_instance_id matches given id.

    Args:
      ec2_instance_id (string): the ec2 instance id to look for
      instances [Instance]: instance data from cloudigrade's /v2/instances/
        endpoint.
    """
    for instance in instances:
        if instance['content_object']['ec2_instance_id'] == ec2_instance_id:
            return instance['content_object']['ec2_instance_id']
    return None


def _image_id_with_ec2_image_id(ec2_image_id, images):
    """
    Get the image id of a given ec2 ami with ec2_image_id.

    Return None if no ec2_image_id matches given id.

    Args:
      images [MachineImage]: images data from cloudigrade's /v2/images/
        endpoint.

    """
    for image in images:
        if image['content_object']['ec2_ami_id'] == ec2_image_id:
            return image['content_object']['ec2_ami_id']
    return None


def _aws_image_id(ec2_image_id, images):
    """Get AWS image id of an image by its ec2 id."""
    for image in images:
        if image['content_object']['ec2_ami_id'] == ec2_image_id:
            return image['content_object']['id']
    return None


def _get_image_data(item, ec2_ami_id):
    """Find the response data for a specific image."""
    if item['content_object']['ec2_ami_id'] == ec2_ami_id:
        return item


def _wait_for_inspection_with_timeout(
        client, image_id, timeout, expected_state):
    """
    Repoll a cloudigrade path until some data is returned.

    Args:
      client: An API client
      ec2_ami_id (string): The image id that is being inspected
      timeout (int): timeout time in minutes
      expected_state (string): The expected state of the inspection
    """
    start_time = datetime.now()
    time_lapsed = 0
    status = 'ABSENT'
    message = 'Waiting...'
    complete_status = [
        'inspected',
        'unavailable',
        'error']
    incomplete_status = [
        'pending',
        'preparing',
        'inspecting',
        'ABSENT',
        'unavailable',
        ]

    if expected_state in complete_status:
        complete_status.remove(expected_state)
    if expected_state in incomplete_status:
        incomplete_status.remove(expected_state)

    # Watch for inspection process to work
    while datetime.now() < start_time+timedelta(minutes=timeout):

        # Get the image specific image.
        images = _get_object_with_timeout(client, 'images/', MEDIUM_TIMEOUT)
        image = _aws_image_id(image_id, images)

        response = client.request('get', f'images/{image}/')
        if response.status_code == 404:
            _logger.info(
                'Image {}, id: {} does not exist, was it deleted?',
                image_id,
                image)
            return False
        image_data = response.json()

        # Watch image status
        if image_data is not None:
            status = image_data['status']
            if status == expected_state:
                print(
                    f"\nStatus is '{status}'. (◎≧v≦)人(≧v≦●)")
                return True
            elif status in complete_status:
                print(f'Inspection complete with unexpected status: {status}')
                return False
            elif status in incomplete_status:

                time_lapsed += 100
                if time_lapsed == 200:
                    message = '♪~ ᕕ(ᐛ)ᕗ Still waiting.'
                elif time_lapsed == 300:
                    message = 'And here we are. ( ͡~ ͜ʖ ͡°) Still waiting'
                elif time_lapsed == 400:
                    message = '(´･_･`) You should probably leave.'
                elif time_lapsed == 500:
                    message = 'ᕙ(⇀｡↼‶)ᕗ  I need a nap.'
                elif time_lapsed == 600:
                    message = '(☞ﾟヮﾟ)☞ ☜(ﾟヮﾟ☜) You still here? Ya, me too ಠ_ಠ'
                elif time_lapsed == 700:
                    message = 'Come ON aws. ಠ╭╮ಠ Get this show on the road!'
                elif time_lapsed == 800:
                    message = 'щ（ﾟДﾟщ） < "Dear god why‽ )'
                elif time_lapsed == 900:
                    message = '(ノಠ益ಠ)ノ彡┻━┻ '
                if status != 'preparing':
                    message = 'This looks like progress ┬┴┤( ͡⚆ل͜├┬┴┬'
                print(f"\nStatus is '{status}'. {message}")
                print(f'time lapsed: {time_lapsed}sec.')
                sleep(100)
            if status == expected_state:
                print(
                    f"\nStatus is '{status}'. (◎≧v≦)人(≧v≦●)")
                return True
    _logger.info('Image %s not inspected before timeout.', image_id)
    return False


# Run test against all of the images
IMAGES_TO_TEST = all_the_images()
# IMAGES_TO_TEST = [(
#     'private-shared', 'ubuntu', 'inspected'
# )]
# (maybe not every time? Uncomment to use just first image)
# IMAGES_TO_TEST = []
# IMAGES_TO_TEST.append(all_the_images()[0])
# Run test against one of the images. Uncomment more as needed
IMAGES_TO_INSPECT = [
    ('private-shared', 'rhel', 'inspected'),
    ('community', 'ubuntu', 'inspected'),
    ('marketplace', 'rhel', 'inspected')
]


@pytest.mark.parametrize('test_case', IMAGES_TO_TEST,
                         ids=[
                             '{}-{}'.format(item[0], item[1])
                             for item in IMAGES_TO_TEST
                             ],
                         )
def test_discovery(test_case, request):
    """Ensure instances are discovered on account creation.

    :id: 509260DA-9980-4F9D-85D9-54C30B99DA56
    :description: Ensure running instances are discovered.
    :steps: 1) Run an image in AWS
        2) Create an account in Cloudigrade - send a POST with the cloud
            account information to '/api/cloudigrade/v2/'
        4) Send a GET to '/api/cloudigrade/v2/instances/' and expect to get the
            instances we created
        5) Send a GET to '/api/cloudigrade/v2/images/' and expect to get the
            image that the instances were based off of.
    :expectedresults:
        1) The server returns a 201 response with the information
            of the created account.
        2) We get 200 responses for our GET requests and information about
            the images includes inspection state information.
    """
    aws_profile = config.get_config()['aws_profiles'][0]
    aws_profile_name = aws_profile['name']
    # Delete any preexisting accounts in cloudigrade
    delete_preexisting_accounts(aws_profile)
    # Purge leftover sqs messages in _ready_volumes queue
    aws_utils.purge_queue_messages()
    # Run an instance
    image_type, image_name, expected_state = test_case
    ec2_ami_id = ''
    for image in aws_profile['images'][image_type]:
        if image_name == image['name']:
            ec2_ami_id = image['image_id']

    # Start an instance for initial discovery
    instance_id = aws_utils.run_instances_by_name(
        aws_profile_name, image_type, image_name, count=1)[0]

    print(f'Instance id: {instance_id}')
    print(f'Image_id: {ec2_ami_id}')

    request.addfinalizer(functools.partial(
        aws_utils.terminate_instance,
        (aws_profile_name, instance_id)
    ))

    # Add AWS account to cloudigrade
    arn = aws_profile['arn']
    client = api.ClientV2()
    acct_data_params = {
        'account_arn': arn,
        'name': uuid4(),
        'cloud_type': 'aws',
    }

    # Create an account
    add_acct_response = client.request(
        'post', 'accounts/', data=acct_data_params)
    assert add_acct_response.status_code == 201

    # Validate that started instance is in cloudigrade
    acct_id = add_acct_response.json()['account_id']
    acct_image = client.request('get', f'accounts/{acct_id}/')
    arn = acct_image.json()['content_object']['account_arn']
    instances = _get_object_with_timeout(
        client,
        'instances/',
        MEDIUM_TIMEOUT,
    )
    assert _get_instance_id_with_ec2_instance_id(instance_id, instances) is \
        not None

    images = _get_object_with_timeout(
        client, 'images/', MEDIUM_TIMEOUT)
    assert _image_id_with_ec2_image_id(ec2_ami_id, images) is not None


@pytest.mark.parametrize('test_case', IMAGES_TO_INSPECT,
                         ids=[
                             '{}-{}'.format(item[0], item[1])
                             for item in IMAGES_TO_INSPECT
                         ],
                         )
def test_inspection(test_case, request):
    """Ensure instances are inspected.

    :id: 45BBB27E-F38D-415F-B64F-B2543D1132DE
    :description: Ensure images are inspected for all running instances.
    :steps: 1) Create a cloud account
        2) Run instances based off of a non-windows image
        3) Send a GET to '/api/cloudigrade/v2/instances/' with a timeout and
            expect to get the instances we created
        4) Send a GET to '/api/cloudigrade/v2/images/' and expect to get the
            image that the instances were based off of.
        5) Keep checking to see that the images progress from "pending",
            "preparing", "inspecting", to "inspected"
    :expectedresults:
        1) We get 200 responses for our GET requests and information about
            the images includes inspection state information.
        2) The images are eventually inspected.
    """
    aws_profile = config.get_config()['aws_profiles'][0]
    aws_profile_name = aws_profile['name']

    # Purge leftover sqs messages in _ready_volumes queue
    aws_utils.purge_queue_messages()
    # Make sure clusters are scaled down at start of inspection
    aws_utils.scale_down_houndigrade()

    # Delete any preexisting accounts in cloudigrade
    delete_preexisting_accounts(aws_profile)

    # Add AWS account to cloudigrade
    arn = aws_profile['arn']
    client = api.ClientV2()
    acct_data_params = {
        'account_arn': arn,
        'name': uuid4(),
        'cloud_type': 'aws',
    }

    # Create an account
    add_acct_response = client.request(
        'post', 'accounts/', data=acct_data_params)
    assert add_acct_response.status_code == 201

    # Start an instance for initial discovery
    image_type, image_name, expected_state = test_case
    ec2_ami_id = ''
    for image in aws_profile['images'][image_type]:
        if image_name == image['name']:
            ec2_ami_id = image['image_id']

    instance_id = aws_utils.run_instances_by_name(
        aws_profile_name, image_type, image_name, count=1)[0]
    request.addfinalizer(functools.partial(
        aws_utils.terminate_instance,
        (aws_profile_name, instance_id)
    ))

    instances = _get_object_with_timeout(
        client, 'instances/', MEDIUM_TIMEOUT)
    images = _get_object_with_timeout(client, 'images/', MEDIUM_TIMEOUT)

    # Check that images and instances show up in Cloudigrade account
    assert _get_instance_id_with_ec2_instance_id(instance_id, instances) is \
        not None

    image_id = _image_id_with_ec2_image_id(ec2_ami_id, images)
    assert image_id is not None

    # Check that Cloudigrade eventually inspects images.
    inspection_results = _wait_for_inspection_with_timeout(
        client, image_id, LONG_TIMEOUT, expected_state)
    assert inspection_results is True
