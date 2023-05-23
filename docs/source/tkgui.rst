The (new) tk Gui
================
.. _tkgui:

Since the 1.1.0 version , the application provides a graphical user interface (GUI)
based on the Tkinter library.

The GUI is designed to edit the result file of the `list` command of the application.
I should be self explanatory. If not, please report a bug.

The GUI is also available as a an option from some commands of the application.
Usually, just add the '-g' or '--gui' option to the arguments.
Please read the :doc:`usage` sections to see what command are supported.


The 'edit' command is always using the new GUI, so no need to add the option.

Usage for editing
~~~~~~~~~~~~~~~~~

.. code:: console

  usage: UEVaultManager edit [-h] [--input]

  optional arguments:
    -h, --help            Show this help message and exit
    -i, --input           The file name (with path) where the list should be read from

    exemple:

      UEVaultManager edit --input "D:\testing\list.csv"

Note : if you run the application from its sources, you can also start the new edit mode by executing the ``./UEVaultManager/tkgui/main.py`` file.

Screenshots
~~~~~~~~~~~

The main window
^^^^^^^^^^^^^^^

Listing of all the assets by row, as a standard data table.

Color code are used to highlight the status of the asset or special cell values.

Rows can be selected and edited or filtered by a search string, a category or a status

Double clic on a cell to open the `edit cell window`.

Some fields are not editable, like the 'asset_id', other are editable directly by changing the value in the cell (mainly boolean and categorical values).

Users fields values can be quick edited by changing their value in the `Quick Edit User Fields` panel.

A new file can be created from scratch or loaded from an existing file.

Data can be exported to a CSV file and saved to the current loaded file or to a new one.

Data can be rebuilt from the previous stored metadata files by clicking on the `Rebuild file content` button (see the `list` command).
It could take some time, and a progress window will be displayed and the process can be stopped.

Some commands can be executed from the toolbar and their result displayed in a new window.

.. image:: https://i.imgur.com/UDQ9S18.png
    :alt: main window
    :align: center

The Edit row window
^^^^^^^^^^^^^^^^^^^

Change the value of all the fields of a row.

Note that the data are raw and not formatted as in the main window, exception for boolean values that are displayed as checkboxes.

The changes made to a value must respect the initial format of the field to avoid errors on save.

.. image:: https://i.imgur.com/k4pQoYq.png
    :alt: row edit window
    :align: center


The Edit cell window
^^^^^^^^^^^^^^^^^^^^

Change the value of a single cell of a row.

Note that the data are raw and not formatted as in the main window, exception for boolean values that are displayed as checkboxes.

The changes made to a value must respect the initial format of the field to avoid errors on save.

.. image:: https://i.imgur.com/p6OrwLz.png
    :alt: cell edit window
    :align: center



The Result window
^^^^^^^^^^^^^^^^^

When running a command by clicking on a button of the `Cli commands` panel, the result is displayed in a windows and can be saved in a text file.

By example, this is the result a the `status` command

.. image:: https://i.imgur.com/kVg2vK0.png
    :alt: cell edit window
    :align: center
