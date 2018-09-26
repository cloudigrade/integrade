"""Utility functions for interacting with the AWS API."""

import json
import logging
import os
import random
from multiprocessing import Pool

import boto3

import botocore

import pytest

from integrade import config
from integrade.exceptions import (
    AWSCredentialsNotFoundError,
    ConfigFileNotFoundError,
    MissingConfigurationError
)
from integrade.tests.constants import EC2_TERMINATED_CODE
from integrade.utils import uuid4


def get_image_id_by_name(aws_profile, image_type, image_name):
    """Grab image id from aws image config."""
    cfg = config.get_aws_image_config()
    images = cfg['profiles'].get(
            aws_profile, {}).get('images', {}).get(image_type, [])
    for image in images:
        if image['name'] == image_name:
            return image['image_id']
    # If no matching image was found, raise an error.
    raise MissingConfigurationError(
            f'No image named {image_name} found in the {image_type}'
            f' section of the aws image config for {aws_profile}')


def aws_image_config_missing():
    """Test if aws config is missing and return boolean."""
    try:
        config.get_aws_image_config()
        return False
    except ConfigFileNotFoundError:
        return True


# apply as decorator on top of tests that need AWS config to be present
aws_image_config_needed = pytest.mark.skipif(
    aws_image_config_missing(), reason='AWS configuration missing.')


def wait_until_running(profile_and_id):
    """Wait until an instance is running.

    :params: tuple of (aws_profile_name, instance_id)

    Note: input is taken in as a tuple to facilitate calling this with
        ``multiprocessing.pool.Pool.map``.
    """
    (aws_profile, ec2_instance_id) = profile_and_id
    session = aws_session(aws_profile)
    instance = session.resource('ec2').Instance(ec2_instance_id)
    instance.wait_until_running()


def terminate_instance(profile_and_id):
    """Terminate an instance and wait until it is terminated.

    :params: tuple of (aws_profile_name, instance_id)

    Note: input is taken in as a tuple to facilitate calling this with
        ``multiprocessing.pool.Pool.map``.
    """
    (aws_profile, ec2_instance_id) = profile_and_id
    session = aws_session(aws_profile)
    instance = session.resource('ec2').Instance(ec2_instance_id)
    instance.terminate()
    instance.wait_until_terminated()


def stop_instance(profile_and_id):
    """Stop an instance and wait until it is stopped.

    :params: tuple of (aws_profile_name, instance_id)

    Note: input is taken in as a tuple to facilitate calling this with
        ``multiprocessing.pool.Pool.map``.
    """
    (aws_profile, ec2_instance_id) = profile_and_id
    session = aws_session(aws_profile)
    instance = session.resource('ec2').Instance(ec2_instance_id)
    instance.stop()
    instance.wait_until_stopped()


def delete_s3_bucket(profile_and_bucket_name):
    """Delete an s3 bucket.

    :params: tuple of (aws_profile_name, bucket_name)

    Note: input is taken in as a tuple to facilitate calling this with
        ``multiprocessing.pool.Pool.map``.
    """
    (aws_profile, bucket_name) = profile_and_bucket_name
    session = aws_session(aws_profile)
    s3client = session.client('s3')
    s3resource = session.resource('s3')
    bucket_resource = s3resource.Bucket(bucket_name)
    bucket_resource.objects.all().delete()
    s3client.delete_bucket(Bucket=bucket_name)


def delete_cloudtrail(profile_and_cloudtrail_name):
    """Delete a cloudtrail.

    :params: tuple of (aws_profile_name, cloudtrail_name)

    Note: input is taken in as a tuple to facilitate calling this with
        ``multiprocessing.pool.Pool.map``.
    """
    (aws_profile, cloudtrail_name) = profile_and_cloudtrail_name
    session = aws_session(aws_profile)
    client = session.client('cloudtrail')
    trail_names = [trail['Name']
                   for trail in client.describe_trails()['trailList']]
    if cloudtrail_name in trail_names:
        response = client.delete_trail(Name=cloudtrail_name)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200


def delete_bucket_and_cloudtrail(profile_cloudtrail_bucket):
    """Delete a cloudtrail and bucket in the proper order.

    :params: tuple of (aws_profile_name, cloudtrail_name, bucket_name)

    Note: input is taken in as a tuple to facilitate calling this with
        ``multiprocessing.pool.Pool.map``.
    """
    (aws_profile, cloudtrail_name, bucket_name) = profile_cloudtrail_bucket
    delete_cloudtrail((aws_profile, cloudtrail_name))
    delete_s3_bucket((aws_profile, bucket_name))


def create_instances(
        aws_profile,
        count=1,
        instance_type='t2.micro'):
    """Create instances from a named image.

    :param aws_profile: (string) Name of profile as defined in config file
    :param instance_type: (string) Name of instance type on aws.

    :returns: (tuple of lists) (instance_ids, image_ids) The first list is of
        the instance ids created, and the second is of the images ids used
        to create the instances.

    The instances will be created using a random choice of AMIs listed in the
    config file for the given profile, one from each section.

    ``create_instances`` waits to return until the instances are all
    running.

    The profile must be named and have its credentials stored in
    $XDG_CONFIG_HOME/integrade/.
    The images are associated with the profiles in
    $XDG_CONFIG_HOME/integrade/aws_image_config.yaml in the following manner:

    aws:
      profiles:
        CUSTOMER1:  # name of profile
                    # Should match env variables for AWS keys and Role ARNs
          images:
            name_of_image:
              is_rhel: True
              image_id: ami-123456789
              other_key: other_value
        CUSTOMER2:  # name of profile
                    # Should match env variables for AWS keys and Role ARNs
          images:
            name_of_image:
              is_rhel: False
              image_id: ami-567890234
              other_key: other_value
    """
    cfg = config.get_aws_image_config()
    image_ids = []
    profile_images = cfg['profiles'][aws_profile]['images']
    for image_group in profile_images:
        images = profile_images[image_group]
        image_ids.append(random.choice(images)['image_id'])

    all_instance_ids = []

    for image_id in image_ids:
        instance_ids = run_instances_by_id(aws_profile, image_id, count)
        all_instance_ids.extend(instance_ids)

    return all_instance_ids, image_ids


def run_instances_by_id(
        aws_profile,
        image_id,
        count,
        instance_type='t2.micro'):
    """Create instances and run them for a certain amount of time.

    :param aws_profile: (string) Name of profile as defined in config file.
    :param image_id: (string) AMI of image to be run.
    :param count: (int) Number of instances to create.

    :returns: (list of string) List of the instance ids as strings.
    """
    client = aws_session(aws_profile).client('ec2')
    response = client.run_instances(
        MaxCount=count,
        MinCount=count,
        ImageId=image_id,
        InstanceType=instance_type)
    instance_ids = []
    for instance in response.get('Instances', []):
        instance_ids.append(instance['InstanceId'])
    with Pool() as p:
        p.map(
            wait_until_running, zip(
                [aws_profile] * len(instance_ids), instance_ids))
    return instance_ids


def run_instances_by_name(
        aws_profile,
        image_type,
        image_name,
        count,
        instance_type='t2.micro'):
    """Create instances and run them for a certain amount of time.

    :param aws_profile: (string) Name of profile as defined in config file.
    :param image_type: (string) Name of the section of images in the config
        file to select the image from (owned, private-shared, community).
    :param image_name: (string) Name of image as defined in config file.
    :param count: (int) Number of instances to create.

    :returns: (list of string) List of the instance ids as strings.
    """
    image_id = get_image_id_by_name(aws_profile, image_type, image_name)
    instance_ids = run_instances_by_id(
        aws_profile, image_id, count, instance_type)
    return instance_ids


def terminate_all_instances(aws_profile):
    """Terminate all instances for a given aws account.

    :param aws_profile: (string) Name of profile as defined in config file

    This is useful when you want to make sure there are no running instances
    in an account. Terminated instances eventually disappear from the list of
    instances visible in the EC2 console or via describe_instances(), but this
    is cannot be controlled by the user (happens on the AWS backend).
    """
    client = aws_session(aws_profile).client('ec2')
    instances_to_terminate = []
    for reservation in client.describe_instances().get('Reservations', []):
        for instance in reservation.get('Instances'):
            if instance['State']['Code'] != EC2_TERMINATED_CODE:
                instances_to_terminate.append(instance['InstanceId'])
    num_instances = len(instances_to_terminate)
    if instances_to_terminate:
        with Pool() as p:
            p.map(
                terminate_instance, zip(
                    [aws_profile] * num_instances, instances_to_terminate))


def get_instances_from_image(aws_profile, image_name):
    """Retrieve list of all instances on an account sourced from a given image.

    :param aws_profile: (string) Name of profile as defined in config file
    :param image_name: (string) Name of image as defined in config file

    :returns: List
    """
    client = aws_session(aws_profile).client('ec2')
    cfg = config.get_aws_image_config()
    image_id = cfg['profiles'][aws_profile]['images'][image_name]['image_id']
    instances = []
    for reservation in client.describe_instances(
            Filters=[{
                'Name': 'image-id',
                'Values': [image_id]
            }]).get('Reservations', []):
        instances.extend([inst for inst in reservation.get('Instances', [])])
    return instances


def get_current_instances(aws_profile):
    """Return list of instance ids of currently existing instances."""
    client = aws_session(aws_profile).client('ec2')
    instance_ids = []
    for reservation in client.describe_instances().get('Reservations', []):
        instance_ids.extend([inst['InstanceId']
                             for inst in reservation.get('Instances', [])])
    return instance_ids


def delete_available_volumes(aws_profile):
    """Delete any available (dangling) volumes."""
    ec2_client = aws_session(aws_profile).client('ec2')
    for volume in ec2_client.describe_volumes(
            Filters=[
                {
                    'Name': 'status',
                    'Values': ['available']
                }
            ]).get('Volumes'):
        ec2_client.delete_volume(VolumeId=volume['VolumeId'])


def create_bucket_for_cloudtrail(aws_profile):
    """Create an s3 bucket suitable to point cloudtrail to for given aws_profile.

    :returns: (string) name of the s3 bucket to point the cloudtrail to.
    """
    session = aws_session(aws_profile)
    s3client = session.client('s3')
    bucket_name = uuid4()
    s3client.create_bucket(Bucket=bucket_name, ACL='public-read-write')
    unique_name1 = uuid4()
    unique_name2 = uuid4()
    new_policy = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Sid': f'{unique_name1}',
                'Effect': 'Allow',
                'Principal': {
                    'Service': 'cloudtrail.amazonaws.com'
                },
                'Action': 's3:GetBucketAcl',
                'Resource': f'arn:aws:s3:::{bucket_name}'
            },
            {
                'Sid': f'{unique_name2}',
                'Effect': 'Allow',
                'Principal': {
                    'Service': 'cloudtrail.amazonaws.com'
                },
                'Action': 's3:PutObject',
                'Resource': f'arn:aws:s3:::{bucket_name}/AWSLogs/*',
                'Condition': {
                    'StringEquals': {
                        's3:x-amz-acl': 'bucket-owner-full-control'
                    }
                }
            }
        ]
    }

    s3_resource = session.resource('s3')
    bucket_policy = s3_resource.BucketPolicy(bucket_name)
    bucket_policy.put(Policy=json.dumps(new_policy))
    return bucket_name


def clean_up_cloudigrade_ami_copies(aws_profile):
    """Clean up any copies of AMIs that cloudigrade made.

    Cloudigrade makes copies of AMIs when they are not owned
    by the account being metered. These add up and make it unclear
    what the current test session is doing, so it is good to clean
    them up on a regular basis.
    """
    client = aws_session(aws_profile).client('ec2')
    cloudigrade_image_copies = []
    cloudigrade_snapshots = []
    for image in client.describe_images(Owners=['self']).get('Images', []):
        if 'cloudigrade reference copy' in image['Name']:
            cloudigrade_image_copies.append(image['ImageId'])
            for device in image.get('BlockDeviceMappings', []):
                if device.get('Ebs', {}).get('SnapshotId'):
                    cloudigrade_snapshots.append(device['Ebs']['SnapshotId'])
    for image_id in cloudigrade_image_copies:
        client.deregister_image(ImageId=image_id)
    for snap_id in cloudigrade_snapshots:
        client.delete_snapshot(SnapshotId=snap_id)


def clean_cloudigrade_queues():
    """Purge any messages off of queues that have the deployment_prefix.

    :raises:
        1) MissingConfigurationError if no AWS_PREFIX is found
        in the environment.
        2) AWSCredentialsNotFoundError if the credentials expected for the
        cloudigrade are not found in the environment.
    """
    session = aws_session('CLOUDIGRADE')
    client = session.client('sqs')
    deployment_prefix = os.environ.get('AWS_QUEUE_PREFIX', False)
    if not deployment_prefix:
        iam = session.resource('iam')
        current_user_arn = iam.CurrentUser().arn
        raise MissingConfigurationError(
            'No deployment prefix was specified with the environment'
            ' variable AWS_PREFIX. Without this, we cannot safely'
            ' purge the SQS queues on the cloudigrade aws account'
            f' accessed with arn {current_user_arn}.')
    for q_url in client.list_queues(
            QueueNamePrefix=deployment_prefix).get('QueueUrls', []):
        try:
            client.purge_queue(QueueUrl=q_url)
        except botocore.errorfactory.ClientError as e:
            logging.getLogger().error(str(e))


def aws_session(aws_profile):
    """Retreive a boto3 Session for the given aws profile name.

    Profiles are defined in ~/.aws/config with the following syntax:
        [profile name_of_profile]
        aws_access_key_id=123456
        aws_secred_access_key=123456
        region = us-east-1
        output=json

    They must have the "profile" preamble because other types of sections can
    be defined in the ~/.aws/config file.
    """
    aws_profile = aws_profile.upper()
    if aws_profile == 'CLOUDIGRADE':
        access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    else:
        access_key_id = os.environ.get(f'AWS_ACCESS_KEY_ID_{aws_profile}')
        access_key = os.environ.get(f'AWS_SECRET_ACCESS_KEY_{aws_profile}')
    if access_key_id and access_key:
        return boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=access_key)
    else:
        raise AWSCredentialsNotFoundError(
            f'Could not find credentials in the environment for {aws_profile}'
        )
