"""Utilities to help interact with the remote environment."""
import os
import pickle
import subprocess
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


def inject_instance_data(
    acct_id, image_type, events,
    instance_id='000000000000',
    ec2_ami_id='000000000000',
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
    run_remote_python("""
    from datetime import date, timedelta
    from account.models import Account, AwsInstance, AwsInstanceEvent
    from account.models import AwsMachineImage

    acct = Account.objects.get(id=acct_id)
    image1 = AwsMachineImage.objects.create(
        account=acct,
        status=AwsMachineImage.INSPECTED,
        rhel_detected=True if 'rhel' in image_type else False,
        openshift_detected=True if 'openshift' in image_type else False,

        ec2_ami_id=ec2_ami_id,
        platform='none',
    )
    instance1 = AwsInstance.objects.create(
        account=acct,
        ec2_instance_id=instance_id,
        region='us-east1',
    )

    on = False
    for event in events:
        AwsInstanceEvent.objects.create(
            event_type='power_on' if not on else 'power_off',
            machineimage=image1,
            instance=instance1,
            occurred_at=date.today() - timedelta(days=event),
        )
        on = not on
    """, **locals())


def direct_count_images(acct_id=None):
    """Count the number of images in an account directly."""
    return run_remote_python("""
        from datetime import date, timedelta
        from account.models import Account, AwsInstance, AwsInstanceEvent
        from account.models import AwsMachineImage

        if acct_id:
            acct = Account.objects.get(id=acct_id)
            return AwsMachineImage.objects.filter(account=acct).count()
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
            acct = Account.objects.get(id=acct_id)
            return AwsMachineImage.objects.filter(account=acct).delete()
        else:
            return AwsMachineImage.objects.all().delete()
        """, **locals())
