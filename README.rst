*********
integrade
*********

|license| |travis| |codecov|

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

    git clone git@github.com:cloudigrade/integrade.git
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

    git clone git@github.com:cloudigrade/integrade.git
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

Configuring and Running
=======================

Integrade can be configured to test any instance of cloudigrade. The
**REQUIRED** environment variables are::

    CLOUDIGRADE_BASE_URL # base url without http/https prefix
    CLOUDIGRADE_TOKEN    # This is the token of the super user created for
                         # cloudigrade

The **OPTIONAL** environment variables are::

    CLOUDIGRADE_API_VERSION # defaults to 'v1'
    CLOUDIGRADE_USER        # defaults to 'admin'. A username is generated for
                            # you when you source scripts/oc-auth.sh.
    CLOUDIGRADE_USER_PASS   # at the moment we only use the token to
                            # authenticate, but this will be useful later
    USE_HTTPS  # defaults to False so communication is done over http.
               #  Set to True to use https.
    SSL_VERIFY # defaults to False. If "True" make client verify certificate

To run ``cloudigrade`` locally, especially if you want to run a branch that is
not master, check out that branch and then follow the directions in the
Cloudigrade readme for `running locally in OpenShift
<https://github.com/cloudigrade/cloudigrade#running-locally-in-openshift>`_.
Then, to deploy the code in that branch in particular, follow the directions
for `deploying in-progress code to OpenShift
<https://github.com/cloudigrade/cloudigrade#running-locally-in-openshift>`_.

To run ``integrade`` against the test environment, it is necessary to log your
local ``oc`` (the command line OpenShift client` into the test environment. You
can do this by logging in through the web UI and in the menu opened by clicking
on your user name, there is an option to ``Copy Login Command``. Paste this to
the terminal to log the ``oc`` client into that OpenShift cluster.

In either case, given that your ``oc`` binary is logged into the correct
OpenShift cluster, you can collect the necessary `CLOUDIGRADE_BASE_URL` by
inspecting the output of `oc status`.  To create the necessary super user and
retreive a token for that user, you can source the script located in
``scripts/oc-auth.sh`` which will use ``CLOUDIGRADE_USER`` or create unique
name using ``uuidgen`` and create a superuser, and then retreive an
authentication token and set the ``CLOUDIGRADE_TOKEN`` with that value. It is
important to remember that ``source scripts/oc-auth.sh`` will set the
environment variables in you current shell but ``bash scripts/oc-auth.sh`` will
not.

If you desire to serve ``cloudigrade`` with the development server instead of
on OpenShift locally or on the test environment, you can use the ``make user``
and ``make user-authenticate`` targets provided in the ``Makefile`` inside the
``cloudigrade`` repository and set ``CLOUDIGRADE_USER`` and
``CLOUDIGRADE_TOKEN`` manually.

With ``integrade`` configured to talk to the correct cloudigrade instance, to
run the functional tests, run the make target ``make test-cloudigrade``.

.. |license| image:: https://img.shields.io/github/license/cloudigrade/integrade.svg
   :target: https://github.com/cloudigrade/cloudigrade/blob/master/LICENSE
.. |travis| image:: https://travis-ci.org/cloudigrade/integrade.svg?branch=master
    :target: https://travis-ci.org/cloudigrade/integrade
.. |codecov| image:: https://codecov.io/gh/cloudigrade/integrade/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/cloudigrade/integrade
