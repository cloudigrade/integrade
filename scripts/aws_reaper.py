"""Terminate all instances and delete dangling volumes in customer accounts."""

import argparse

from integrade import config
from integrade.tests import aws_utils


def customer_aws_reaper(
        env_cloudtrail_only=False,
        all_integrade_cloudtrails=False
):
    """Clean up customer accounts from all testing activities.

    Terminate all instances and delete dangling volumes. De-registers the AMIs
    created by cloudigrade as copies of shared private AMIs and the associated
    snapshots. Also deletes the cloudtrail associated with the current
    DEPLOYMENT_PREFIX. Optionally can delete all cloudtrails created by
    integrade environments. This option is relativly heavy handed, as it
    deletes any cloudtrail that has 'integrade' in the name.

    Iterates over all customers profiles configured for integrade to use as
    customer accounts and terminates their instances and deletes any dangling
    EBS volumes. Useful for periodic clean up but DANGEROUS! DELETES stuff!!!
    Do not use if you think you have important things running in these
    accounts.

    Expects all the same configuration as used by the tests to be present in
    the environment, most critcally the AWS credentials for any customer
    accounts.

    Command line arguments::

        --env-cloudtrail-only
        --all-integrade-cloudtrails

    The ``--env-cloudtrail-only`` option makes it so that **only** the
    cloudtrail associated with this environments DEPLOYMENT_PREFIX is deleted,
    and **no other action is taken with any instances or AMIs**. This option
    takes precedence over any other option.

    The ``--all-integrade-cloudtrails`` option deletes **all** cloudtrails with
    'integrade' in the name of the trail. When this option is passed all
    other cleanup activities are also taken, so all instances are terminated
    and cloudigrade AMI copies are deleted, etc.

    Example::

        # in a python 3 virutal environment
        $ make install-dev
        # would terminate all instances and also the cloudtrail for this env
        $ python scripts/aws_reaper.py

        # would terminate all instances and also all integrade cloudtrails
        # and also any cloudtrail in the customer accounts with
        # $CLOUDTRAIL_PREFIX
        $ python scripts/aws_reaper.py --all-integrade-cloudtrails

        # would ONLY delete the cloudtrail for this environment
        $ python scripts/aws_reaper.py --env-cloudtrail-only

        # Equivalent to previous example,
        # would ONLY delete the cloudtrail for this environment
        $ python scripts/aws_reaper.py --env-cloudtrail-only --all-integrade-cloudtrails # noqa E501


    This script is called by a nightly job running on gitlab-ci, and is meant
    to help reduce any detritus we leave behind on AWS during daily testing on
    the accounts used by automation as customers.
    """
    cfg = config.get_config(create_superuser=False, need_base_url=False)
    for profile in cfg['aws_profiles']:
        aws_utils.delete_cloudtrail(
            (profile['name'], profile['cloudtrail_name']))
        if env_cloudtrail_only:
            continue
        else:
            aws_utils.terminate_all_instances(profile['name'])
            aws_utils.delete_available_volumes(profile['name'])
            aws_utils.clean_up_cloudigrade_ami_copies(profile['name'])
            if all_integrade_cloudtrails:
                session = aws_utils.aws_session(profile['name'])
                client = session.client('cloudtrail')
                trail_names = [
                    trail['Name'] for trail in
                    client.describe_trails()['trailList']]
                for trail_name in trail_names:
                    if 'integrade' in trail_name:
                        client.delete_trail(Name=trail_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Clean up customer accounts from test activities.')
    parser.add_argument(
        '--env-cloudtrail-only',
        required=False,
        default=False,
        action='store_true',
        dest='env_cloudtrail_only',
        help=('Only delete the cloudtrails from this test run, not any.'
              ' Instances or other resources.')
    )
    parser.add_argument(
        '--all-integrade-cloudtrails',
        required=False,
        default=False,
        action='store_true',
        dest='all_integrade_cloudtrails',
        help=(
            'Delete all integrade review environment cloudtrails. '
            'Not compatible with --env-cloudtrail-only, which takes '
            'precedence.'))
    args = parser.parse_args()

    customer_aws_reaper(
        args.env_cloudtrail_only,
        args.all_integrade_cloudtrails)
