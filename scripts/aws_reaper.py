"""Terminate all instances and delete dangling volumes in customer accounts."""

from integrade import config
from integrade.tests import aws_utils


def customer_aws_reaper():
    """Terminate all instances and delete dangling volumes.

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
        aws_utils.terminate_all_instances(profile['name'])
        aws_utils.delete_available_volumes(profile['name'])


if __name__ == '__main__':
    customer_aws_reaper()
