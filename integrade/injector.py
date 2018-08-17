"""Utilities to help interact with the remote environment."""
import os
import pickle
import subprocess
from random import randint
from shutil import which
from textwrap import dedent, indent


def run_remote_python(script, **kwargs):
    """Run Python code inside the remove OpenShift pod."""
    script = dedent(script).strip()

    deployment_prefix = os.environ.get('DEPLOYMENT_PREFIX', '')
    if deployment_prefix:
        container_name = f'{deployment_prefix}cloudigrade-api'
    else:
        container_name = 'cloudigrade-api'

    data = pickle.dumps(kwargs)
    wrap_start = 'import pickle as _pickle;import sys as _sys;\n' \
        f'globals().update(_pickle.loads({repr(data)}))\n' \
        'def _codewrapper():\n'
    wrap_end = '\n_retval = _codewrapper()\n' \
        '_sys.stdout.buffer.write(_pickle.dumps(_retval))\n'
    script = wrap_start + indent(script, '  ') + wrap_end
    script = script.encode('utf8')

    if which('oc'):
        result = subprocess.run(['sh',
                                 '-c',
                                 f'oc rsh -c {container_name} $(oc get pods'
                                 ' -o jsonpath="{.items[*].metadata.name}" -l'
                                 f' name={container_name})'
                                 ' scl enable rh-python36'
                                 ' -- python manage.py shell'],
                                stdout=subprocess.PIPE,
                                input=script,
                                timeout=60
                                )
        if result.returncode != 0:
            for line in result.stdout:
                print(line)
            raise RuntimeError('Remote script failed')
        elif result.stdout:
            return pickle.loads(result.stdout)
    else:
        raise EnvironmentError(
            'Must have access to the cloudigrade openshift pod via the "oc"'
            'client to run remote commands in the Django manage.py shell. Make'
            'sure the "oc" client is in your path and the $DEPLOYMENT_PREFIX'
            'used in the deploy is in your environment.'
        )


def direct_count_images(acct_id=None):
    """Count the number of images in an account directly."""
    return run_remote_python("""
        from datetime import date, timedelta
        from account.models import Account, AwsInstance, AwsInstanceEvent
        from account.models import AwsMachineImage

        if acct_id:
            return AwsMachineImage.objects.filter(
                instanceevent__instance__account__user_id=acct_id).count()
        else:
            return AwsMachineImage.objects.all().count()
        """, **locals())


def clear_images(acct_id=None):
    """Count the number of images in an account directly."""
    return run_remote_python("""
        from datetime import date, timedelta
        from account.models import Account, AwsInstance, AwsInstanceEvent
        from account.models import AwsMachineImage

        if acct_id:
            images = AwsMachineImage.objects.filter(
                instanceevent__instance__account__user_id=acct_id)
        else:
            images = AwsMachineImage.objects.all()
        images.delete()
        """, **locals())


def inject_aws_cloud_account(user_id, name=None, aws_account_number=None):
    """Mock an aws account for the user specified.

    Mocked AWS accounts dont point to a real AWS account! No cloudtrail
    will exist, no real events will arrive, and no images will actually be
    inspected.

    :returns: (int) The account id, needed by inject_instance_data.
    """
    if aws_account_number is None:
        aws_account_number = str(randint(100000000000, 999999999999))
    arn = f'arn:aws:iam::{aws_account_number}:role/mock-arn'
    if name is None:
        name = aws_account_number
    return run_remote_python("""
    from account.models import AwsAccount

    kwargs = {
        'aws_account_id': aws_account_number,
        'user_id': user_id,
        'account_arn': arn,
        'name': name,
    }

    acct, new = AwsAccount.objects.get_or_create(**kwargs)

    return {
        'id' : acct.id,
        'aws_account_id' : aws_account_number,
        'user_id' : user_id,
        'account_arn' : arn,
        'name' : name
    }
    """, **locals())


def inject_instance_data(
    acct_id, image_type, events,
    instance_id=None,
    ec2_ami_id=None,
    owner_aws_account_id=None,
):
    """Inject instance and image data for tests.

    Creates a new instance object directly in the Cloudigrade system and an
    image matching the given ID or creates one. The instance will be given tags
    based on a list of tags in `image_type`.

    The `events` parameter is a list of day offsets from today. For each offset
    an event will be created to power on, then power off, then repeat. As an
    example, the event list [10, 5, 3] will create events showing the instance
    was powered on 10 days ago, powered off 5 days ago, then powered on and
    left on 3 days ago.
    """
    if instance_id is None:
        instance_id = str(randint(100000, 999999999999))
    if ec2_ami_id is None:
        ec2_ami_id = str(randint(100000, 999999999999))
    run_remote_python("""
    from datetime import date, timedelta
    from account.models import Account, AwsInstance, AwsInstanceEvent
    from account.models import AwsMachineImage

    acct = Account.objects.get_or_create(id=acct_id)[0]
    image1 = AwsMachineImage.objects.get_or_create(
        ec2_ami_id=ec2_ami_id,

        defaults=dict(
            owner_aws_account_id=owner_aws_account_id or acct.aws_account_id,
            status=AwsMachineImage.INSPECTED,
            rhel_detected=True if 'rhel' in image_type else False,
            openshift_detected=True if 'openshift' in image_type else False,

            platform='none',
        )
    )[0]
    instance1 = AwsInstance.objects.get_or_create(
        ec2_instance_id=instance_id,

        defaults=dict(
            account=acct,
            region='us-east1',
        )
    )[0]

    on = False
    for event in events:
        if isinstance(event, int):
            when = date.today() - timedelta(days=event)
        else:
            when = event
        AwsInstanceEvent.objects.create(
            event_type='power_on' if not on else 'power_off',
            machineimage=image1,
            instance=instance1,
            occurred_at=when,
        )
        on = not on
    """, **locals())
