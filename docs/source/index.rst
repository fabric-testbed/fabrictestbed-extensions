.. fabrictestbed-extensions documentation master file, created by
   sphinx-quickstart on Mon Mar 14 13:37:01 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to fabrictestbed-extensions documentation!
==================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:


fabrictestbed-extensions, otherwise known as "FABlib", is an
implementation of a Python API for interacting with `FABRIC testbed`_.
You would typically call FABlib APIs from your `Jupyter`_ notebooks or
from your Python code.  FABRIC project runs an instance of
`JupyterHub`_ at https://jupyter.fabric-testbed.net.

If you are new to FABRIC, it would be helpful to begin by reading the
articles at https://learn.fabric-testbed.net.  If you have questions
or run into trouble, you can discuss them at FABRIC forums:
https://learn.fabric-testbed.net/forums/.


Installing FABlib
-----------------

You can install released versions of FABlib from PyPI:

.. code-block:: bash

   $ pip install fabrictestbed-extensions

If you need the current development version of FABlib, install it from
the git repository:

.. code-block:: bash

   $ pip install git+https://github.com/fabric-testbed/fabrictestbed-extensions@main

Installing FABlib will also install a number of dependencies, so you
might want to install FABlib in a virtual environment.


FABlib's "hello world"
----------------------

Here's a quick example of some code that uses FABlib:

.. code-block:: python

   from fabrictestbed_extensions.fablib.fablib import FablibManager

   try:
       fablib = FablibManager()
       fablib.show_config()
   except Exception as e:
       print(f"Exception: {e}")

However, please note that the above example will `not` work out of the
box. Some configuration is required for the code above to work as
expected. Configuration can come from either environment variables or
from a file, usually placed at ``~/work/fabric_config/fabric_rc``.

More examples of FABlib usage can be found in the notebooks available
at FABRIC project's JupyterLab instance, which are also maintained at
https://github.com/fabric-testbed/jupyter-examples.

Configuring FABlib
------------------

In order to interact with FABRIC testbed, FABlib will need to know
these things:

- FABRIC orchestrator host's address
- FABRIC credential manager host's address
- FABRIC bastion host's address
- Your FABRIC project ID
- Path to your FABRIC token
- Your username for FABRIC bastion host
- Your ssh private key to use with FABRIC bastion host
- Your ssh public and private keys to use with FABRIC slices
- And, optionally, the passphrases to the private keys

In FABRIC project's JupyterLab, this configuration is usually done by
running a "Configure your Jupyter Environment" notebook that you will
need to run, when you sign in there for the first time.

If you are running code in another machine, you must set some
environment variables, like so:

.. code-block:: bash

  export FABRIC_CREDMGR_HOST=cm.fabric-testbed.net
  export FABRIC_ORCHESTRATOR_HOST=orchestrator.fabric-testbed.net

  # Find your real project ID from FABRIC portal: https://portal.fabric-testbed.net/.
  export FABRIC_PROJECT_ID=a429da84-20cd-449d-bcb6-5e2c4ac269c0

  # Download FABRIC token from FABRIC credential manager: https://cm.fabric-testbed.net/.
  export FABRIC_TOKEN_LOCATION=/path/to/token.json

  export FABRIC_BASTION_HOST=bastion.fabric-testbed.net
  # Find your real FABRIC bastion host username at https://portal.fabric-testbed.net/user.
  export FABRIC_BASTION_USERNAME=you_0000010534

  export FABRIC_BASTION_KEY_LOCATION=/home/fabric/work/fabric_config/fabric_bastion_key
  # If your bastion private key is protected, export its passphrase.
  export FABRIC_BASTION_KEY_PASSPHRASE=s00p3rs3kr3t

  export FABRIC_SLICE_PRIVATE_KEY_FILE=/home/fabric/work/fabric_config/slice_key
  export FABRIC_SLICE_PUBLIC_KEY_FILE=/home/fabric/work/fabric_config/slice_key.pub
  export FABRIC_SLICE_PRIVATE_KEY_PASSPHRASE=maj0rs3kr3t

The ``fabric_rc`` configuration file also follows the same format as
above.  Currently, contents of the configuration file will override
values set using environment variables.


.. _FABRIC testbed: https://fabric-testbed.net/
.. _Jupyter: https://jupyter.org/
.. _JupyterHub: https://jupyter.org/hub

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
