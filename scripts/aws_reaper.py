"""Terminate all instances and delete dangling volumes in customer accounts."""

import argparse

from integrade import config
from integrade.tests import aws_utils


def customer_aws_reaper(cloudtrails_only=False):
    """Clean up customer accounts from all testing activities.

    Terminate all instances and delete dangling volumes. De-registers the AMIs
    created by cloudigrade as copies of shared private AMIs and the associated
    snapshots.
    Iterates over all customers profiles configured for integrade to use as
    customer accounts and terminates their instances and deletes any dangling
    EBS volumes. Useful for periodic clean up but DANGEROUS! DELETES stuff!!!
    Do not use if you think you have important things running in these
    accounts.

    Expects all the same configuration as used by the tests to be present in
    the environment, most critcally the AWS credentials for any customer
    accounts.

    Example::

        # in a python 3 virutal environment
        $ make install-dev
        $ python scripts/aws_reaper.py

    This script is called by a nightly job running on gitlab-ci, and is meant
    to help reduce any detritus we leave behind on AWS during daily testing on
    the accounts used by automation as customers.
    """
    cfg = config.get_config()
    for profile in cfg['aws_profiles']:
        aws_utils.delete_cloudtrail(
            (profile['name'], profile['cloudtrail_name']))
        if cloudtrails_only:
            continue
        else:
            aws_utils.terminate_all_instances(profile['name'])
            aws_utils.delete_available_volumes(profile['name'])
            aws_utils.clean_up_cloudigrade_ami_copies(profile['name'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Clean up customer accounts from test activities.')
    parser.add_argument(
        '--cloudtrails-only',
        required=False,
        default=False,
        action='store_true',
        dest='cloudtrails_only',
        help=('Only delete the cloudtrails from this test run, not any.'
              ' Instances or other resources.')
    )
    args = parser.parse_args()

    customer_aws_reaper(args.cloudtrails_only)
