Configuration
-------------
.. _configuration:

Config folder
~~~~~~~~~~~~~

Configuration file, log files and results files are stored by default in data folders in the user home directory.

The location is:

-  for Linux: ``~/.config/UEVaultManager/``
-  for Windows: ``C:\users\<you_login_name>\.config\UEVaultManager\``

Config files
~~~~~~~~~~~~

For the Cli Application settings
^^^^^^^^^^^^^^^^^^^^^^^^

UEVaultManager supports some settings in its config file ``<config folder>/config.ini``:

This is an example of this file content and the settings you can change:

.. code:: ini

    [UEVaultManager]
    ;Set to True to start the Application in Edit mode (since v1.4.4) with the GUI
    start_in_edit_mode = False
    ;Set to True to disable the automatic update check
    disable_update_check = False
    ; Set to True to disable the notice about an available update on exit
    disable_update_notice = False
    ; Create a backup of the output file (when using the --output option) suffixed by a timestamp before creating a new file
    create_output_backup = True
    ; Set to True to create a backup of the log files that store asset analysis. It is suffixed by a timestamp
    create_log_backup = True
    ; Set to True to print more information during long operations
    verbose_mode = False
    ; Delay in seconds when UE assets metadata cache will be invalidated. Default value represent 15 days
    ue_assets_max_cache_duration = 1296000
    ; File name (and path) to log issues with assets when running the --list command
    ; use "~/" at the start of the filename to store it relatively to the user directory
    ignored_assets_filename_log = ~/.config/ignored_assets.log
    notfound_assets_filename_log = ~/.config/notfound_assets.log
    bad_data_assets_filename_log = ~/.config/bad_data_assets.log
    scan_assets_filename_log = ~/.config/scan_assets.log
    ; Minimal unreal engine version to check for obsolete assets (default is 4.26)
    engine_version_for_obsolete_assets = 4.26


For the GUI settings
^^^^^^^^^^^^^^^^^^^^^^^^

Since version 1.6.0, UEVaultManager also supports some settings specific to the new GUI, in a config file ``<config folder>/config_gui.ini``:

This is an example of this file content and the settings you can change:

.. code:: ini

  [UEVaultManager]
  ;File name of the last opened file
  last_opened_file = D:\Projets_Perso\03d_CodePython\UEVaultManager\scraping\assets.db
  ;X position of the main windows. Set to 0 to center the window
  x_pos = -1885
  ;Y position of the main windows. Set to 0 to center the window
  y_pos = 8
  ;Width of the main windows
  width = 1694
  ;Height of the main windows
  height = 941
  ;Set to True to print debug information (GUI related only)
  debug_mode = False
  ;Set to True to speed the update process by not updating the metadata files. FOR TESTING ONLY
  never_update_data_files = False
  ;Set to True to re-open the last file at startup if no input file is given
  reopen_last_file = True
  ;Set to True to enable cell coloring depending on its content.It could slow down data and display refreshing
  use_colors_for_data = True
  ;Delay in seconds when image cache will be invalidated. Default value represent 15 days
  image_cache_max_time = 1296000
  ;Folder (relative or absolute) to store cached data for assets (mainly preview images)
  cache_folder = ../../../cache
  ;Folder (relative or absolute) to store result files to read and save data from
  results_folder = ../../../results
  ;The last opened filter file name.Automatically saved when loading a filter.Leave empty to load no filter at start.Contains the file name only, not the path
  last_opened_filter =
  ;Number of Rows displayed or scraped per page.If this value is changed all the scraped files must be updated to match the new value
  rows_per_page = 37
  ;Folder (relative or absolute) to store the scraped files for the assets in markeplace
  scraping_folder = ../../../scraping




Note that some other settings for the new GUI are managed by a dedicated python file ``<python install folder>/<source folder of the package>/tkgui/modules/GuiSettingsClass.py``

For instance, the location is:

-  for Linux: ``~/.local/lib/python3.10/site-packages/UEVaultManager/tkgui/modules/GuiSettingsClass.py``
-  for Windows: ``c:\python3.10\site-packages\UEVaultManager\tkgui\modules\GuiSettingsClass.py``

The final path can depend on your installation.
