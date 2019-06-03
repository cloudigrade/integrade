"""Initiate instances in customer accounts against which tests can run."""

from integrade import config
from integrade.tests import aws_utils

def aws_instance_instigator():
    """Run instances in an aws account for testing purposes."""
    cfg = config.get_config()
    profile = cfg['aws_profiles'][0]
    profile_name = profile['name']
    image_type = 'owned'
    image_name = 'rhel-extra-detection-methods'

    instance_ids = aws_utils.run_instances_by_name(
        profile_name,
        image_type,
        image_name,
        count=2
    )
    print(instance_ids)


if __name__ == "__main__":
    aws_instance_instigator()
