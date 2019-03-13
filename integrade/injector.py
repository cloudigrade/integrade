"""Utilities to help interact with the remote environment."""
import pickle
import subprocess
from random import randint
from shutil import which
from textwrap import dedent, indent

from integrade import config
from integrade.constants import (
    CLOUD_ACCESS_AMI_NAME,
    MARKETPLACE_AMI_NAME,
)


def run_remote_python(script, **kwargs):
    """Run Python code inside the remote OpenShift pod."""
    script = dedent(script).strip()

    openshift_prefix = config.get_config()['openshift_prefix']
    if openshift_prefix:
        container_name = f'{openshift_prefix}a'
    else:
        raise RuntimeError('Unable to determine openshift prefix!')

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
                                 ' -- python -W ignore manage.py shell'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                input=script,
                                timeout=60
                                )
        if result.returncode != 0:
            for line in result.stdout:
                print(line)
            raise RuntimeError(
                f'Remote script failed (container_name="{container_name}"'
            )
        elif result.stdout:
            return pickle.loads(result.stdout)
    else:
        raise EnvironmentError(
            'Must have access to the cloudigrade openshift pod via the "oc"'
            'client to run remote commands in the Django manage.py shell. Make'
            'sure the "oc" client is in your path and the $OPENSHIFT_PREFIX'
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


def inject_aws_cloud_account(user_id,
                             name=None,
                             aws_account_number=None,
                             acct_age=100,
                             ):
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
    import datetime
    from account.models import AwsAccount

    kwargs = {
        'aws_account_id': aws_account_number,
        'user_id': user_id,
        'account_arn': arn,
        'name': name,
    }

    acct, new = AwsAccount.objects.get_or_create(**kwargs)
    days_ago = datetime.timedelta(days=acct_age)
    created_date = datetime.datetime.now() - days_ago
    timetuple = list(created_date.timetuple()[:-2])
    # make it noon, this sets the hour
    timetuple[3] = 12
    # this sets the min
    timetuple[4] = 0
    # this sets the sec
    timetuple[5] = 0
    acct.created_at = datetime.datetime(*timetuple)
    acct.save()

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
    challenged=False,
    vcpu=1,
    memory=1,
    rhel_enabled_repos_found=False,
    rhel_product_certs_found=False,
    rhel_release_files_found=False,
    rhel_signed_packages_found=False,
    is_marketplace=False,
    is_cloud_access=False,
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
    ami_name = ''
    owner_id = 841258680906
    if instance_id is None:
        instance_id = str(randint(100000, 999999999999))
    if ec2_ami_id is None:
        ec2_ami_id = str(randint(100000, 999999999999))
    if is_marketplace:
        owner_aws_account_id = owner_id
        ami_name = MARKETPLACE_AMI_NAME
    if is_cloud_access:
        owner_aws_account_id = owner_id
        ami_name = CLOUD_ACCESS_AMI_NAME
    if is_marketplace and is_cloud_access:
        raise ValueError('Both is_marketplace and is_cloud_access are True.'
                         'Only zero or one can be True at a time.')
    return run_remote_python("""
    from datetime import date, timedelta
    import json

    from account.models import Account, AwsInstance, AwsInstanceEvent
    from account.models import AwsMachineImage, AwsEC2InstanceDefinitions
    from account.util import recalculate_runs

    instance_type = 'xx.fake-' + str(vcpu) + '-' + str(memory)

    AwsEC2InstanceDefinitions.objects.get_or_create(
        instance_type=instance_type,
        defaults=dict(
            memory=memory,
            vcpu=vcpu,
        ),
    )

    acct = Account.objects.get_or_create(id=acct_id)[0]
    rhel_detected = True if 'rhel' in image_type else False
    rhel_detected = rhel_detected or rhel_release_files_found
    image1 = AwsMachineImage.objects.get_or_create(
        ec2_ami_id=ec2_ami_id,

        defaults=dict(
            owner_aws_account_id=owner_aws_account_id or acct.aws_account_id,
            name=ami_name,
            status=AwsMachineImage.INSPECTED,
            inspection_json=json.dumps({
                'rhel_release_files_found': rhel_detected,
                'rhel_enabled_repos_found': rhel_enabled_repos_found,
                'rhel_product_certs_found': rhel_product_certs_found,
                'rhel_signed_packages_found': rhel_signed_packages_found,
            }),
            openshift_detected=True if 'openshift' in image_type else False,

            rhel_challenged=(challenged and 'rhel' in image_type),
            openshift_challenged=(challenged and 'openshift' in image_type),

            platform='none',
        )
    )[0]
    instance1 = AwsInstance.objects.get_or_create(
        ec2_instance_id=instance_id,
        machineimage=image1,
        defaults=dict(
            account=acct,
            region='us-east1',
        )
    )[0]

    on = False
    on_off_when = []
    for event in events:
        on = not on
        if isinstance(event, int):
            when = date.today() - timedelta(days=event)
        else:
            when = event
        on_off_when.append(when)
        instanceevent = AwsInstanceEvent.objects.create(
            event_type='power_on' if on else 'power_off',
            machineimage=image1 if on else None,
            instance=instance1,
            instance_type=instance_type,
            occurred_at=when,
            created_at=when,
        )
        # Need to reload event from DB, otherwise occurred_at is passed
        # as a date object instead of a datetime object.
        instanceevent.refresh_from_db()
        recalculate_runs(instanceevent)
    return {
        'image_id': image1.id,
        'instance_id': instance1.id,
        'on_off_when': on_off_when,
        'rhel_enabled_repos_found': rhel_enabled_repos_found,
        'rhel_product_certs_found': rhel_product_certs_found,
        'rhel_release_files_found': rhel_release_files_found,
        'rhel_signed_packages_found': rhel_signed_packages_found,
    }
    """, **locals())


def make_super_user(username, password):
    """Use manange.py to create a superuser and return an auth token."""
    return run_remote_python("""
        from django.contrib.auth import get_user_model;
        from rest_framework.authtoken.models import Token
        User = get_user_model();
        email = '{0}@example.com'.format(username)
        if User.objects.filter(username=username).exists():
            super_user = User.objects.get_by_natural_key(username)
            super_user.set_password(password)
            super_user.save()
        else:
            super_user = User.objects.create_superuser(
                            username,
                            email,
                            password
                            )
        token = Token.objects.get_or_create(user=super_user)
        return str(token[0])
            """, **locals())
