=============
mungetout
=============

.. image:: https://travis-ci.com/stackhpc/mungetout.svg?branch=master
    :target: https://travis-ci.com/stackhpc/mungetout

Convert from Ironic Inspector introspection format to cardiff format. Now
you can mungetout...


Usage
=====

Requires the python `hardware <https://pypi.org/project/hardware/>`_
package to be installed.

.. code-block::

  pip install git+https://github.com/stackhpc/mungetout
  mkdir working-dir && cd working-dir
  m2-gen
  hardware-cardiff -I ipmi -p 'results/extra_hardware_kef1i-a00*'

It can be useful to limit the number of nodes for debugging purposes:

.. code-block::

  m2-gen --limit 4 -vv

Note
====

This project has been set up using PyScaffold 2.5.11. For details and usage
information on PyScaffold see http://pyscaffold.readthedocs.org/.
