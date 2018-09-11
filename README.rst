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
the develpment requirements. Run the following commands to do that::

    git clone git@gitlab.com:cloudigrade/integrade.git
    cd integrade
    make install-dev

Now you can browse the source code and to help you here is an overview about
the source organization. Considering the repository root directory as a
starting point:

* ``integrade`` directory: place where all integrade automation framework
  modules are created. There you will find, for example, an API client,
  utilities funtions, etc...
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

Integrade can be configured to test any instance of cloudigrade. The
**REQUIRED** environment variables are::

    CLOUDIGRADE_BASE_URL # base url without http/https prefix

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
``$XDG_CONFIG_HOME/integrade/aws_image_config.yaml``. An example file is
provided in the base directory with the name ``aws_image_config.yaml``. This
yaml file contains dictionaries mapping the ``${PROFILE_NAME}`` of each AWS
account to images that whos attributes are described in a dictionary. See the
example file for more details.

For example if one AWS account environment varibles are configured with the
``${PROFILE_NAME`` of ``CUSTOMER1``, and information matching this profile name
is in ``$XDG_CONFIG_HOME/integrade/aws_image_config.yaml``, then the config
object will contain the following information::

    {'api_version': 'v1',
     'base_url': 'test.cloudigra.de',
     'aws_profiles': [{'arn': 'arn:aws:iam::439727791560:role/CloudigradeRoleForTestEnv',
       'name': 'CUSTOMER1',
       'account_number': '439727791560',
       'cloudtrail_name': 'cloudigrade-439727791560',
       'access_key_id': 'SECRET',
       'access_key': 'ALSOSECRET',
       'images': {'rhel1': {'is_rhel': True,
         'image_id': 'ami-09c521cbc20a78b49',
         'is_shared': False},
        'rhel2': {'is_rhel': True,
         'image_id': 'ami-0d2e46db3ba19f204',
         'is_shared': False},
        'centos1': {'is_rhel': False,
         'image_id': 'ami-0bf18d6709ff12ee8',
         'is_shared': False}}}],
     'superuser_token': 'ANOTHERSECRET',
     'scheme': 'http',
     'ssl-verify': False}


Running Integrade
=======================

To run ``cloudigrade`` locally, especially if you want to run a branch that is
not master, check out that branch and then follow the directions in the
Cloudigrade readme for `running locally in OpenShift
<https://gitlab.com/cloudigrade/cloudigrade#running-locally-in-openshift>`_.
Then, to deploy the code in that branch in particular, follow the directions
for `deploying in-progress code to OpenShift
<https://gitlab.com/cloudigrade/cloudigrade#running-locally-in-openshift>`_.

To run ``integrade`` against the test environment, it is necessary to log your
local ``oc`` (the command line OpenShift client` into the test environment. You
can do this by logging in through the web UI and in the menu opened by clicking
on your user name, there is an option to ``Copy Login Command``. Paste this to
the terminal to log the ``oc`` client into that OpenShift cluster.

No matter which OpenShift cluster cloudigrade is running in, given that your
``oc`` binary is logged into it, you can collect the necessary
``CLOUDIGRADE_BASE_URL`` by inspecting the output of ``oc status``. If this
environment variable is not set, by default we assume the test environment,
``test.cloudigra.de``. 

If you want to create a super user with a custom set username and password,
you can do that and retrieve a token for that user, you can source the script
located in ``scripts/oc-auth.sh`` which will set ``CLOUDIGRADE_USER`` to a
unique name using ``uuidgen`` and create a superuser with that name, and then
retreive an authentication token and set the ``CLOUDIGRADE_TOKEN`` with that
value. It is important to remember that ``source scripts/oc-auth.sh`` will set
the environment variables in you current shell but ``bash scripts/oc-auth.sh``
will not. This is ENTIRELY OPTIONAL and only useful if you want to set the
super user username and password yourself. Otherwise integrade will create one
on the fly.

If you want to test a different instance of cloudigrade, just make sure to
export ``CLOUDIGRADE_BASE_URL`` to the correct value and log your ``oc`` client
into the correct openshift instance.

If you desire to serve ``cloudigrade`` with the development server instead of
on OpenShift locally or on the test environment, you can use the ``make user``
and ``make user-authenticate`` targets provided in the ``Makefile`` inside the
``cloudigrade`` repository and set ``CLOUDIGRADE_USER`` and
``CLOUDIGRADE_TOKEN`` manually.

With ``integrade`` configured to talk to the correct cloudigrade instance, to
run the functional tests against the api, run the make target ``make test-api``.

Running UI Tests
================

UI tests may run via Selenium-driven local browsers or remotely through the
SauceLabs service.

Running tests on SauceLabs locally will require use of the SauceLabs Connect
tunnel, which you can get here: https://wiki.saucelabs.com/display/DOCS/Sauce+Connect+Proxy

Download this tool and place the `sc` binary in your path. Next, add the two
environment variables $SAUCELABS_USERNAME and $SAUCELABS_API_KEY to your
~/.bash_profile. You can now run the SauceLabs Connect tunnel in a terminal.

    sc --user $SAUCELABS_USERNAME --api-key $SAUCELABS_API_KEY --shared-tunnel

The command will take a few seconds to start up and will tell you when it is
ready to accept connections from SauceLabs. Once it is ready you can proceed to
run your tests locally.

The UI tests can be easily run either on Chrome or Firefox:

    py.test -v integrade/tests/ui/ --driver Chrome
    py.test -v integrade/tests/ui/ --driver Firefox


.. |license| image:: https://img.shields.io/github/license/cloudigrade/integrade.svg
   :target: https://github.com/cloudigrade/cloudigrade/blob/master/LICENSE
.. |gitlabci| image:: https://gitlab.com/cloudigrade/integrade/badges/master/pipeline.svg
   :target: https://gitlab.com/cloudigrade/integrade/commits/master
.. |codecov| image:: https://codecov.io/gl/cloudigrade/integrade/branch/master/graph/badge.svg
   :target: https://codecov.io/gl/cloudigrade/integrade
