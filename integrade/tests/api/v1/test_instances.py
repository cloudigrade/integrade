"""Tests for cloud accounts.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
from time import sleep

import pytest

from integrade import api, config
from integrade.tests import aws_utils
from integrade.tests.api.v1 import urls
from integrade.tests.api.v1.utils import get_auth
from integrade.tests.aws_utils import aws_image_config_needed
from integrade.tests.constants import AWS_ACCOUNT_TYPE


@aws_image_config_needed
@pytest.mark.serial_only
def test_find_running_instances(drop_account_data, instances_to_terminate):
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
    aws_profile = config.get_config()['aws_profiles'][0]
    aws_profile_name = aws_profile['name']
    # create some instances to detect on creation, random choice from every
    # configured image type (private, owned, marketplace, community)
    created_instance_ids, source_image_ids = aws_utils.create_instances(
        aws_profile_name)
    # add new instances to list of instances to terminate after test
    instances_to_terminate.extend(
        zip(
            [aws_profile_name] * len(created_instance_ids),
            created_instance_ids)
    )
    cloud_account = {
        'account_arn': aws_profile['arn'],
        'resourcetype': AWS_ACCOUNT_TYPE
    }
    client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    list_instances = client.get(urls.INSTANCE, auth=auth)
    found_instances = [instance['ec2_instance_id']
                       for instance in list_instances['results']]
    for inst_id in created_instance_ids:
        assert inst_id in found_instances
    list_images = client.get(urls.IMAGE, auth=auth)
    found_images = [image['ec2_ami_id'] for image in list_images['results']]
    for image_id in source_image_ids:
        assert image_id in found_images

    timeout = 900
    images_to_inspect = source_image_ids
    while images_to_inspect:
        for source_image in images_to_inspect:
            status = client.get(urls.IMAGE,
                                params={'ec2_ami_id': source_image},
                                auth=auth)['results'][0]['status']
            if status in ['pending', 'preparing', 'inspecting']:
                sleep(60)
                timeout -= 60
            if status == 'inspected':
                images_to_inspect.remove(source_image)

    assert images_to_inspect == []
    # TODO: assert on inspection result (rhel found)
