"""Utility functions for interacting with the AWS API."""

import time
from multiprocessing import Pool

import boto3

import pytest

from integrade import config
from integrade.exceptions import ConfigFileNotFoundError
from integrade.tests.constants import EC2_TERMINATED_CODE


def aws_config_missing():
    """Test if aws config is missing and return boolean."""
    try:
        config.get_aws_config()
        return False
    except ConfigFileNotFoundError:
        return True


# apply as decorator on top of tests that need AWS config to be present
aws_config_needed = pytest.mark.skipif(
    aws_config_missing(), reason='AWS configuration missing.')


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


def create_instances(
        aws_profile,
        image_name,
        count=1,
        instance_type='t2.nano'):
    """Create instances from a named image.

    :param aws_profile: (string) Name of profile as defined in config file
    :param image_name: (string) Name of image as defined in config file
    :param count: (int) Number of instances to create.

    :returns: (list) List of the instance ids created.

    The instances will be created using the named AMI as found in the
    config file for the given profile.

    ``create_instances`` waits to return until the instances are all
    running.

    The profile must be named and have its credentials stored in ~/.aws/config
    The images are associated with the profiles in
    ~/.config/integrade/aws_config in the following manner:

    aws:
      profiles:
        name_of_profile1:
          images:
            name_of_image:
              is_rhel: True
              image_id: ami-123456789
              other_key: other_value
        name_of_profile2:
          images:
            name_of_image:
              is_rhel: False
              image_id: ami-567890234
              other_key: other_value
    """
    client = aws_session(aws_profile).client('ec2')
    cfg = config.get_aws_config()
    image_id = cfg['profiles'][aws_profile]['images'][image_name]['image_id']
    response = client.run_instances(
        MaxCount=count,
        MinCount=count,
        ImageId=image_id,
        InstanceType=instance_type)
    instance_ids = []
    for instance in response.get('Instances', []):
        instance_ids.append(instance['InstanceId'])
    with Pool(len(instance_ids)) as p:
        p.map(
            wait_until_running, zip(
                [aws_profile] * len(instance_ids), instance_ids))
    return instance_ids


def run_instances(aws_profile, image_name, count, run_time):
    """Create instances and run them for a certain amount of time.

    :param aws_profile: (string) Name of profile as defined in config file
    :param image_name: (string) Name of image as defined in config file
    :param count: (int) Number of instances to create.
    :param run_time: (double) Desired time to let instances run (in seconds)

    :returns: (double) Time from when instances were all live until all
         instances were all terminated (in seconds).
    """
    instance_ids = create_instances(aws_profile, image_name, count=count)
    # now sleep until instances have run for desired amount of time
    time_all_live = time.time()
    time.sleep(run_time)
    with Pool(len(instance_ids)) as p:
        p.map(
            terminate_instance, zip(
                [aws_profile] * len(instance_ids), instance_ids))
    time_all_terminated = time.time()
    return time_all_terminated - time_all_live


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
        with Pool(num_instances) as p:
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
    cfg = config.get_aws_config()
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
    return boto3.Session(profile_name=aws_profile)
