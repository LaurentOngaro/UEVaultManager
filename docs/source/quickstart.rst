Quickstart
----------
.. _quickstart:

**Tip:** When using PowerShell with the standalone executable, you may
need to replace ``UEVaultManager`` with ``.\UEVaultManager`` in the
commands below.

Installation
~~~~~~~~~~~~

To use UEVaultManager, first install it using pip:

.. code-block:: console

   pip install UEVaultManager

log in
~~~~~~

.. code:: console

  UEVaultManager auth

If the pywebview package is installed (that is done by the installation
process), this should open a new window with the Epic Login.

Otherwise, authentication is a little finicky since we have to go
through the Epic website and manually copy a code. The login page should
open in your browser and after logging in you should be presented with a
JSON response that contains a code (” authorizationCode”), just copy the
code into the terminal and hit enter.

Alternatively you can use the ``--import`` flag to import the
authentication from the Epic Games Launcher

Note that this will log you out of the Epic Launcher.

Listing your asset
~~~~~~~~~~~~~~~~~~

.. code:: console

  UEVaultManager list

This will fetch a list of asset available on your account, the first
time may take a while depending on how many asset you have.

Saving the list into a CSV file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: console

  UEVaultManager list -o "c:/ue_asset_list.csv"

You can edit some data in this file You can update the data in the file
by running the same command again. Your changes could be preserved,
depending on what fields (aka. columns) has been changed (see :doc:`output` section).
