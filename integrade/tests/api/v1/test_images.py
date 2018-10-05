"""Tests for images.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import random
from urllib.parse import urljoin

import pytest

from integrade import api, config
from integrade.injector import inject_aws_cloud_account, inject_instance_data
from integrade.tests import urls, utils
from integrade.utils import uuid4


def usertype(superuser):
    """Generate a test id based on the user type."""
    return 'superuser' if superuser else 'regularuser'


@pytest.fixture(scope='module')
def images_data():
    """Create test data for the tests on this module.

    To be able to verify that the image API endpoing works we need:

    * One super user acccount
    * Two regular user account
    * Image data for each user
    """
    utils.drop_image_data()

    user1 = utils.create_user_account()
    user2 = utils.create_user_account()
    auth1 = utils.get_auth(user1)
    auth2 = utils.get_auth(user2)

    # user1 will have 2 images
    images1 = [
        {
            'ec2_ami_id': str(random.randint(100000, 999999999999)),
            'rhel': True,
            'rhel_detected': True,
            'openshift': False,
            'openshift_detected': False,
        },
        {
            'ec2_ami_id': str(random.randint(100000, 999999999999)),
            'rhel': False,
            'rhel_detected': False,
            'openshift': True,
            'openshift_detected': True,
        },
    ]

    # user2 will have 3 images
    images2 = [
        {
            'ec2_ami_id': str(random.randint(100000, 999999999999)),
            'rhel': True,
            'rhel_detected': True,
            'openshift': False,
            'openshift_detected': False,
        },
        {
            'ec2_ami_id': str(random.randint(100000, 999999999999)),
            'rhel': True,
            'rhel_detected': True,
            'openshift': True,
            'openshift_detected': True,
        },
        {
            'ec2_ami_id': str(random.randint(100000, 999999999999)),
            'rhel': False,
            'rhel_detected': False,
            'openshift': True,
            'openshift_detected': True,
        },
    ]

    for user, images in zip((user1, user2), (images1, images2)):
        account = inject_aws_cloud_account(
            user['id'],
            name=uuid4(),
        )

        for image in images:
            if image['rhel'] and image['openshift']:
                image_type = 'rhel,openshift'
            elif image['rhel'] and not image['openshift']:
                image_type = 'rhel'
            elif not image['rhel'] and image['openshift']:
                image_type = 'openshift'
            else:
                raise ValueError('Not a valid image type.')

            image['id'] = inject_instance_data(
                account['id'],
                image_type,
                [random.randint(0, 20)],
                ec2_ami_id=image['ec2_ami_id'],
            )['image_id']

    return user1, user2, auth1, auth2, images1, images2


@pytest.mark.parametrize('superuser', (False, True), ids=usertype)
def test_list_all_images(images_data, superuser):
    """Test if images can be listed.

    :id: 9b103387-4868-4f30-ab61-47fc54e2f41f
    :description: Check if a regular user can fetch all of its images and if a
        superuser can fetch all images on the system or filter the images by
        any user.
    :steps:
        1. List all images using a regular user. Check if the returned images
           are only the ones that belong to the user.
        2. List all images on the system using a superuser. Also check if a
           superuser can filter the list of images by user.
    :expectedresults:
        A regular user can only list its images and a superuser can fetch all
        images or filter by user.
    """
    user1, user2, auth1, auth2, images1, images2 = images_data
    client = api.Client(authenticate=superuser)
    start, end = utils.get_time_range()
    params = None
    if superuser:
        # fisrt check if superuser is able to fetch all images
        response = client.get(urls.IMAGE).json()
        assert response['count'] == len(images1) + len(images2), response
        images = response['results']
        for image, expected in zip(images, images1 + images2):
            for key, value in expected.items():
                assert image[key] == value, images

        # Now restrict the results to an specific user
        params = {'user_id': user1['id']}
    response = client.get(urls.IMAGE, auth=auth1, params=params).json()

    assert len(images1) == response['count']
    images = response['results']

    for image, expected in zip(images, images1):
        for key, value in expected.items():
            assert image[key] == value, images


def test_list_specific_image(images_data):
    """Test if a specific image can be fetched.

    :id: 99aaec58-6053-476d-9674-ee650ffa33a9
    :description: Check if a regular user can fetch one of its images. Check if
        a superuser can fetch all images. Check if a regular user can't fetch
        an image that belongs to another user.
    :steps:
        1. Fetch all images
        2. For each image, check if its owner and a superuser can fetch each.
           Also check if another user can't fetch it.
    :expectedresults:
        A regular user can only fetch its images and a superuser can fetch all
        images.
    """
    user1, user2, auth1, auth2, images1, images2 = images_data
    cfg = config.get_config()
    superuser_auth = api.TokenAuth(cfg.get('superuser_token'))
    client = api.Client(authenticate=False)
    start, end = utils.get_time_range()

    response = client.get(urls.IMAGE, auth=superuser_auth).json()
    assert response['count'] == len(images1) + len(images2), response
    all_images = response['results']
    ec2_ami_ids1 = [image['ec2_ami_id'] for image in images1]
    ec2_ami_ids2 = [image['ec2_ami_id'] for image in images2]

    for image in all_images:
        if image['ec2_ami_id'] in ec2_ami_ids1:
            auth = auth1
            other_auth = auth2
        elif image['ec2_ami_id'] in ec2_ami_ids2:
            auth = auth2
            other_auth = auth1
        else:
            raise ValueError(
                f'{image} not in {ec2_ami_ids1} or {ec2_ami_ids2}')
        image_url = urljoin(urls.IMAGE, str(image['id']))

        # Ensure superuser can fetch it
        response = client.get(image_url, auth=superuser_auth).json()
        assert response == image

        # Ensure the image owner can fetch it
        response = client.get(image_url, auth=auth).json()
        assert response == image

        # Ensure any other user can't fetch it
        old_handler = client.response_handler
        client.response_handler = api.echo_handler
        response = client.get(image_url, auth=other_auth)
        client.response_handler = old_handler
        assert response.status_code == 404
        assert response.json()['detail'] == 'Not found.'


@pytest.mark.parametrize('superuser', [True, False], ids=['super', 'regular'])
@pytest.mark.parametrize('method', ['put', 'patch'])
def test_challenge_image(superuser, method):
    """Test if a challenge flags for RHEL and OS can be changed.

    :id: ec5fe0b6-9852-48db-a2ba-98d01aeaac28
    :description: Try to change challenge flags on an image and ensure that
        change is reflected afterwards.
    :steps:
        1. Create an image in a known account and make sure the challenge
           flags are false by default.
        2. Use both PUT and PATCH forms of the image endpoint to set a flag to
           true
    :expectedresults:
        The image data now reflects this change.
    """
    cfg = config.get_config()
    user = utils.create_user_account()
    auth = utils.get_auth(user)

    client = api.Client(authenticate=False)
    account = inject_aws_cloud_account(
            user['id'],
            name=uuid4(),
        )
    image_type = ''
    ec2_ami_id = str(random.randint(100000, 999999999999))

    image_id = inject_instance_data(
        account['id'],
        image_type,
        [random.randint(0, 20)],
        ec2_ami_id=ec2_ami_id,
    )['image_id']

    if superuser:
        auth = api.TokenAuth(cfg.get('superuser_token'))

    image_url = urljoin(urls.IMAGE, str(image_id)) + '/'

    # Ensure the image owner can fetch it
    response = client.get(image_url, auth=auth).json()

    assert response['rhel_challenged'] is False
    assert response['openshift_challenged'] is False

    for tag in ('rhel', 'openshift'):
        if method == 'put':
            response[f'{tag}_challenged'] = True
            response = client.put(image_url, response, auth=auth).json()
        elif method == 'patch':
            data = {
                'resourcetype': 'AwsMachineImage',
                f'{tag}_challenged': True,
            }
            response = client.patch(image_url, data, auth=auth).json()
        else:
            pytest.fail(f'Unknown method "{method}"')
        assert response[f'{tag}_challenged'] is True

    # Make sure the change is reflected in new responses
    response = client.get(image_url, auth=auth).json()
    response[f'{tag}_challenged'] = True

    # Ensure any other user can't fetch it
    response = client.get(image_url, auth=auth)
    assert response.status_code == 200
    assert response.json()[f'{tag}_challenged']
