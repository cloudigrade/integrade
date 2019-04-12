*********
integrade
*********

|license| |gitlabci| |codecov|

What is integrade?
==================

**integrade** is a Python library that facilitates functional testing of
cloudigrade.

Installation
============

integrade can be installed in two ways. The first one is recommended for
everyone who is interested on just running the functional tests. The second are
for people interested on contribute by helping improving either the automation
framework or the test cases.

In this section will only be covered how to install integrade in order to run
the functional tests. If you are interested on contributing with test cases or
improving the automation framework check the Contributing section.

To install integrade you have to clone the repository and install it. The
following commands will do that for you::

    git clone git@gitlab.com:cloudigrade/integrade.git
    cd integrade
    make install

.. note::

    Don't get yourself confused by the ``tests`` directory. Those tests are
    integrade's automation framework tests, not the functional tests for
    cloudigrade. Cloudigrade functional tests are located at the
    integrade/tests directory.

Once you have integrade installed you can configure it and run the functional
tests. See the Configuring and Running section for more information.

Contributing
============

So you are interested on contributing to integrade, huh? That is great and we
will help you do a development installation so you can send your great
contributions.

To do a development installation you have to clone the repository and install
the development requirements. Run the following commands to do that::

    git clone git@gitlab.com:cloudigrade/integrade.git
    cd integrade
    make install-dev

Now you can browse the source code and to help you here is an overview about
the source organization. Considering the repository root directory as a
starting point:

* ``integrade`` directory: place where all integrade automation framework
  modules are created. There you will find, for example, an API client,
  utilities functions, etc...
* ``integrade/tests`` directory: place where all cloudigrade's functional tests
  are created. There you will find modules for testing cloudigrade's projects
  and features.
* ``tests`` directory: place where all integrade automation framework tests are
  created. Yes, integrade is tested! How can an automation framework test a
  project if itself does not have tests and they pass?

No matter if you are interested on contributing to new functional tests for
cloudigrade projects or improving integrade automation framework, make sure
that the tests pass and also the code follows the code style properly. The
``make lint`` can help you linting your code and ensuring the code style.

Configuring Integrade
=======================

Integrade can be configured to test any instance of cloudigrade. You may set
up this configuration yourself or use the `setup-env.sh` script in the
`scripts/` directory.

Automatic Setup
---------------

Before using the automatic setup you will need to create a configuration file
for AWS access credentials. These credentials should include the Cloudigrade
AWS account's access key and secret key as well as ARNs and credentials for two
"customer" accounts.

Create a file `.env-pre-setup` in the integrade root directory::

    # Access and Secret Keys for the Cloudigrade AWS Account
    export AWS_ACCESS_KEY_ID=XXX
    export AWS_SECRET_ACCESS_KEY=XXX

    # Access keys to the first customer account
    export AWS_ACCESS_KEY_ID_DEV07CUSTOMER=XXX
    export AWS_SECRET_ACCESS_KEY_DEV07CUSTOMER=XXX
    export CLOUDIGRADE_ROLE_DEV07CUSTOMER=XXX

    # Access keys to the second customer account
    export AWS_ACCESS_KEY_ID_DEV08CUSTOMER=XXX
    export AWS_SECRET_ACCESS_KEY_DEV08CUSTOMER=XXX
    export CLOUDIGRADE_ROLE_DEV08CUSTOMER=XXX

If you don't know which credentials to use ask another integrade developer
for assistance.

Automatic setup configures your environment to run tests against a remote
installation of the Cloudigrade service. These include automated review
environments that are created for each active branch of the cloudigrade and
frontigrade repositories. When you push an integrade branch of the same name
for a Merge Request, its tests will be run on the matching environment.

To configure your local setup to use that same branch-based environment, use
the `setup-env.sh` script::

    eval $(scripts/setup-env.sh my-branch-name-here)

Your environment is not populated with all the correct information to point
running tests at the remote review environment. You can test them out with a
simple test run.

    make test-api

Manual Setup
------------

The **REQUIRED** environment variables are::

    CLOUDIGRADE_BASE_URL # base url without http/https prefix
    AWS_S3_BUCKET_NAME   # cloudigrade's bucket name
    AWS_QUEUE_PREFIX     # string that integrade's queues begin with
    OPENSHIFT_PREFIX     # Prefix for all of cloudigrade's openshift
                         # related objects

To run tests that require AWS accounts (and API access to these), configure any
number of accounts with the following sets of environment varibles::

    CLOUDIGRADE_ROLE_${PROFILE_NAME}
    AWS_ACCESS_KEY_ID_${PROFILE_NAME}
    AWS_SECRET_ACCESS_KEY_${PROFILE_NAME}

There can be any number of these "profiles". The only requirement is that the sets of environment variables share this same ending.


The **OPTIONAL** environment variables are::

    CLOUDIGRADE_USER     # Super username on cloudigrade. Integrade assumes
                         # that the email is {username}@example.com
    CLOUDIGRADE_PASSWORD # Password for above user.
    CLOUDIGRADE_TOKEN    # You may provide an authentication token for a super
                         # user you have allready created. You should
                         # also provide the username and password with the two
                         # variables above.
    CLOUDIGRADE_API_VERSION # defaults to 'v1'
    USE_HTTPS  # defaults to False so communication is done over http.
               #  Set to True to use https.
    SSL_VERIFY # defaults to False. If "True" make client verify certificate
    SAVE_CLOUDIGRADE_LOGS # if set to any truthy value, logs from cloudigrade
                          # api, celery worker, and celery beat will be saved
                          # to local disk after each test session.

If ``SAVE_CLOUDIGRADE_LOGS`` is set, three logs will be saved to disk after
test run, one for the api pod, one for the celery worker pod, and the third
for the celery beat pod.

Additionally, there is an **OPTIONAL** config file you can install in your
``integrade/aws_image_config.yaml``. An example file is
provided in the base directory at ``aws_image_config_template.yaml``.

This yaml file contains dictionaries mapping the ``${PROFILE_NAME}`` of each
AWS account to images the attributes of which are described in a dictionary. See
the example file for more details.

For example if one AWS account environment varibles are configured with the
``${PROFILE_NAME}`` of ``CUSTOMER1``, and information matching this profile
name is in ``integrade/aws_image_config.yaml``, then the config object will
contain the following information::

    {
        'api_version': 'v1',
        'base_url': 'test.cloudigra.de',
        'aws_profiles': [
            {
                'arn': 'arn:aws:iam::439727791560:role/CloudigradeRoleForTestEnv',
                'name': 'CUSTOMER1',
                'account_number': '439727791560',
                'cloudtrail_name': 'cloudigrade-439727791560',
                'access_key_id': 'SECRET',
                'access_key': 'ALSOSECRET',
                'images': {
                    'rhel1': {
                        'is_rhel': True,
                        'image_id': 'ami-09c521cbc20a78b49',
                        'is_shared': False
                    },
                    'rhel2': {
                        'is_rhel': True,
                        'image_id': 'ami-0d2e46db3ba19f204',
                        'is_shared': False
                    },
                    'centos1': {
                        'is_rhel': False,
                        'image_id': 'ami-0bf18d6709ff12ee8',
                        'is_shared': False
                    }
                }
            }
        ],
        'superuser_token': 'ANOTHERSECRET',
        'scheme': 'http',
        'ssl-verify': False
    }


Running Integrade
=======================

To run ``cloudigrade`` locally, refer to `shiftigrade <https://gitlab.com/cloudigrade/shiftigrade>`_.

Environments are created by `cloudigrade
<https://gitlab.com/cloudigrade/cloudigrade>`_ and `frontigrade
<https://gitlab.com/cloudigrade/frontigrade>`_ when branches are pushed to
those repositories. If you are working on a feature or bug fix that has a
branch in either of those repositories, name your integrade branch the same
name. This way, your MR will know to point itself to those environments.

If there do not exist branches for both cloudigrade and frontigrade for the
integrade work you are doing, then you should make branches based off of
``master`` in those repos and then push branches (with no changes) to each of
those repositories with the name of your branch, for example
``update_integrade_tools``.

To run ``integrade`` locally against an MR environment, it is necessary to log your
local ``oc`` (the command line `OpenShift client`) into the test environment. You
can do this by logging in through the web UI and in the menu opened by clicking
on your user name, there is an option to ``Copy Login Command``. Paste this to
the terminal to log the ``oc`` client into that OpenShift cluster.

To set all needed environment variables, you can ``source`` script like the following, but filled in with the necessary details:

.. code::

    # ==================================================================
    # Example script to set your environment to point to an MR
    # ==================================================================

    # Name of your branch
    export BRANCH_NAME=

    # The access keys for the aws account that Cloudigrade is using
    # The MRs are using dev11
    export AWS_ACCESS_KEY_ID=
    export AWS_SECRET_ACCESS_KEY=

    # Access keys to the dev07 aws account
    export AWS_ACCESS_KEY_ID_DEV07CUSTOMER=
    export AWS_SECRET_ACCESS_KEY_DEV07CUSTOMER=
    export CLOUDIGRADE_ROLE_DEV07CUSTOMER=

        # Access keys to the dev08 aws account
    export AWS_ACCESS_KEY_ID_DEV08CUSTOMER=
    export AWS_SECRET_ACCESS_KEY_DEV08CUSTOMER=
    export CLOUDIGRADE_ROLE_DEV08CUSTOMER=

    # The rest of the items needed can be derived from above
    echo "=================================================================="
    echo "SETTING INTEGRADE CONFIG"
    echo "=================================================================="
    export OPENSHIFT_PREFIX="c-review-${BRANCH_NAME}-"
    export AWS_QUEUE_PREFIX="${BRANCH_NAME}-"
    export CLOUDTRAIL_PREFIX="review-$AWS_PREFIX"
    export USE_HTTPS=True
    export CLOUDIGRADE_BASE_URL="review-${BRANCH_NAME}.5a9f.insights-dev.openshiftapps.com"
    export AWS_S3_BUCKET_NAME="${AWS_PREFIX}cloudigrade-s3"

You can copy the file in the root of this repository named ``.mr_env_template`` and fill it out for your own use.

Integrade will create a super user on the fly for you, but you can optionally provide ``CLOUDIGRADE_TOKEN`` if you have a token you would prefer to use.

If you want to test a different instance of cloudigrade, just make sure to
export ``CLOUDIGRADE_BASE_URL`` to the correct value and log your ``oc`` client
into the correct openshift instance.

With ``integrade`` configured to talk to the correct cloudigrade instance, to
run the functional tests against the api, run the make target ``make test-api``.

To learn more about different options regarding creating environments for testing, refer to the  `shiftigrade <https://gitlab.com/cloudigrade/shiftigrade>`_ ``README``.

To get started using the api client for exploratory testing, try opening up an `ipython <https://ipython.readthedocs.io/en/stable/>`_ session and running the following:

.. code::

    from integrade import api
    # this will create a client using super user credentials
    client = api.Client()
    client.get('/api/v1/')


Running UI Tests
================

UI tests may run via Selenium-driven local browsers or remotely through the
SauceLabs service.

Running tests on SauceLabs locally will require use of the SauceLabs Connect
tunnel, which you can get here: https://wiki.saucelabs.com/display/DOCS/Sauce+Connect+Proxy

Download this tool and place the `sc` binary in your path. Next, add the two
environment variables $SAUCELABS_USERNAME and $SAUCELABS_API_KEY to your
~/.bash_profile. You can now run the SauceLabs Connect tunnel in a terminal.

.. code::

    sc --user $SAUCELABS_USERNAME --api-key $SAUCELABS_API_KEY --shared-tunnel

The command will take a few seconds to start up and will tell you when it is
ready to accept connections from SauceLabs. Once it is ready you can proceed to
run your tests locally.

The UI tests can be easily run either on Chrome or Firefox:

.. code::

    py.test -v integrade/tests/ui/ --driver Chrome
    py.test -v integrade/tests/ui/ --driver Firefox


Troubleshooting Test Runs
=========================

Are tests failing unexpectedly? Check these items to ensure a healthy run.

* Do you have a local login session with OpenShift? Use ``oc whoami`` and
  ``oc projects`` to check that the correct OpenShift host and project are
  selected. If that fails, you may need to go to your OpenShift web console,
  use ``Copy Login Command``, and paste the session connection string into
  your local terminal.
* Is the inspection cluster running? If it's left "stuck" from a previous test
  run, you may need to manually scale it down or else inspection-related tests
  may fail. Go to the AWS web console's ECS screen, find the appropriate
  cluster, view its ECS Instances, and edit the Auto Scaling configuration to
  set Desired Capacity, Min, and Max all to ``0``.
* Are you using the correct ``houndigrade`` image? If you are testing changes
  to the inspection process, you may need to configure the OpenShift project to
  use a nonstandard image name and tag. Find the appropriate Config Map and
  verify ``aws-houndigrade-ecs-image-name`` and
  ``aws-houndigrade-ecs-image-tag`` have the correct value. You may need to
  redeploy the ``-w`` pod(s) so the Celery workers pick up any config changes.
* Does the target customer AWS cloud account have too many cloud trails? AWS
  has a limit of 5 trails per region per account, but our heavily-used test
  accounts may attempt and fail to exceed that limit. Check the AWS console in
  the customer's account and delete any old trails.
* Is the deployed environment somehow tainted? When all else fails, destroy the
  review environment and start over. Use the GitLab pipeline to run the
  "Teardown Cloudigrade" and "Teardown Frontigrade" jobs. When they complete,
  verify that the OpenShift applications, AWS ECS cluster, AWS SQS queues, and
  customer AWS CloudTrail trails are all gone. Manually remove any that remain.


.. |license| image:: https://img.shields.io/github/license/cloudigrade/integrade.svg
   :target: https://github.com/cloudigrade/cloudigrade/blob/master/LICENSE
.. |gitlabci| image:: https://gitlab.com/cloudigrade/integrade/badges/master/pipeline.svg
   :target: https://gitlab.com/cloudigrade/integrade/commits/master
.. |codecov| image:: https://codecov.io/gl/cloudigrade/integrade/branch/master/graph/badge.svg
   :target: https://codecov.io/gl/cloudigrade/integrade
