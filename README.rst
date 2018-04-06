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

integrade can be installed in two way. The first one is recommended for
everyone who is interested on just running the function tests. The second are
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

To be done... integrade is just starting and in the future you can see how to
configure and run the functional tests in this section.

.. |license| image:: https://img.shields.io/github/license/cloudigrade/integrade.svg
   :target: https://github.com/cloudigrade/cloudigrade/blob/master/LICENSE
.. |travis| image:: https://travis-ci.org/cloudigrade/integrade.svg?branch=master
    :target: https://travis-ci.org/cloudigrade/integrade
.. |codecov| image:: https://codecov.io/gh/cloudigrade/integrade/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/cloudigrade/integrade
