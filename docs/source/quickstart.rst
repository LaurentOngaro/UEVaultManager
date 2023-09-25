Quickstart
----------
.. _quickstart:

**Tip:** When using PowerShell with the standalone executable, you may
need to replace `UEVaultManager` with ``.\UEVaultManager`` in the
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
open in your browser and after login you should be presented with a
JSON response that contains a code (`authorizationCode`), just copy the
code into the terminal and hit enter.

Alternatively you can use the `--import` flag to import the
authentication from the Epic Games Launcher

Note that this will log you out of the Epic Launcher.

Listing your asset
~~~~~~~~~~~~~~~~~~

.. code:: console

  UEVaultManager list

This will fetch a list of asset available on your account (only the assets you OWNED), the first
time may take a while depending on how many asset you have.

Saving the list into a CSV file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: console

  UEVaultManager list -o "D:/ue_asset_list.csv"

You can manually edit some data in this file
And you can update the data extrated from the Marketplace (new version, new release, desciption update...) by running the same command again.
The changes you made manually will be preserved, depending on what fields (aka. columns) has been changed (see :doc:`output` section).

Editing the list with the new GUI (since 1.6.0)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: console

  UEVaultManager edit -i "D:/ue_asset_list.csv"

For more details, please read the :doc:`gui` section.

Scraping all the asset from the marketplace and store them in a database file (since 1.8.0)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: console

  UEVaultManager scrap

Editing the database content with the new GUI (since 1.8.0)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: console

  UEVaultManager edit -db "D:/scraping/assets.db"

Note that the folder ``D:/scraping`` is set in ``<config folder>/config_gui.ini``.
By default this folder is located in the application installation folder (``<python folder>/Lib/site-packages/UEVaultManager``).
