The (new) tk Gui
================
.. _tkgui:

Since the 1.1.0 version , the application provides a graphical user interface (GUI)
based on the Tkinter library.

The GUI is designed to edit the result file of the `list` command of the application.
I should be self explanatory. If not, please report a bug.

The GUI is also available as an option from some commands of the application.
Usually, just add the '-g' or '--gui' option to the command arguments.
Please read the :doc:`usage` sections to see what command are supported.


The 'edit' command always uses the new GUI, so no need to add the option.

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


Use it as default starting mode
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to start the application without arguments or start it in edit mode by default (aka with the new GUI).
you can set the line start_in_edit_mode=true in the configuration file.
In this case, the application will use the default data file.
If the file does not exists, a new one will be created and its content will be rebuilt from scratch.

Screenshots
~~~~~~~~~~~

The main window
^^^^^^^^^^^^^^^

It displays a Listing of all the assets by row, as a standard data table. You can use pagination or not, filter rows, edit cells ...

Coloring is used to highlight the status of the asset or special cell values.

Rows can be selected and edited or filtered by a search string, a category or a status.

Double-clic on a cell to open the `edit cell window`.

Some fields are not editable, like the 'asset_id', other are editable directly by changing the value in the cell (mainly boolean and categorical values).

Users fields values can be quick edited by changing their value in the `Quick Edit User Fields` panel. Change will be applied on focus out of the editing widget.

A new file can be created from scratch or loaded from an existing file.

Data can be exported to a CSV file and saved to the current loaded file or to a new one.

Data can be rebuilt from the previous stored metadata files by clicking on the `Rebuild file content` button (basicaly, it will run the `list` command in background).
It could take some time, so a progress window will be displayed and the process can be stopped.

Some commands can be executed from the toolbar and their result will be displayed in a Result window.

.. image:: https://i.imgur.com/UDQ9S18.png
    :alt: main window
    :align: center

The Edit row window
^^^^^^^^^^^^^^^^^^^

It allows to edit the value of all the fields of a row.

Note that the data are raw and not formatted as in the main window, exception for boolean values that are displayed as checkboxes.

The changes made to a value must respect the initial format of the field to avoid errors on save.

.. image:: https://i.imgur.com/k4pQoYq.png
    :alt: row edit window
    :align: center


The Edit cell window
^^^^^^^^^^^^^^^^^^^^

It alloaw to change the value of a single cell of a row.

Note that the data are raw and not formatted as in the main window, exception for boolean values that are displayed as checkboxes.

The changes made to a value must respect the initial format of the field to avoid errors on save.

.. image:: https://i.imgur.com/p6OrwLz.png
    :alt: cell edit window
    :align: center



The Result window
^^^^^^^^^^^^^^^^^

When running a command by clicking on a button of the `Cli commands` panel, the result is displayed in a windows and can be saved in a text file for later use.

For instance, this is the result of the `status` command

.. image:: https://i.imgur.com/kVg2vK0.png
    :alt: cell edit window
    :align: center
