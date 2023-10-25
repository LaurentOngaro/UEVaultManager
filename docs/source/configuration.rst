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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
    ; File name (and path) to log issues with assets when running the list or scrap commands
    ; use "~/" at the start of the filename to store it relatively to the user directory
    scrap_assets_filename_log = ~/.config/scrap_assets.log
    notfound_assets_filename_log = ~/.config/notfound_assets.log
    scan_assets_filename_log = ~/.config/scan_assets.log
    ; Minimal unreal engine version to check for obsolete assets (default is 4.26)
    engine_version_for_obsolete_assets = 4.26


For the GUI settings
^^^^^^^^^^^^^^^^^^^^

Since version 1.6.0, UEVaultManager also supports some settings specific to the new GUI, in a config file ``<config folder>/config_gui.ini``:

This is an example of this file content and the settings you can change:

.. code:: ini

  [UEVaultManager]
  ;List of Folders to scan for assets. Their content will be added to the list
  folders_to_scan = ["G:/Assets/pour UE/01 Acquis", "G:/Assets/pour UE/00 A trier"]
  ;Set to True to print debug information (GUI related only)
  debug_mode = False
  ;Set to True to use multiple threads when scraping/grabing data for UE assets
  use_threads = True
  ;Set to True to re-open the last file at startup if no input file is given
  reopen_last_file = True
  ;Set to True to speed the update process by not updating the metadata files. FOR TESTING ONLY
  never_update_data_files = False
  ;Set to True to enable cell coloring depending on its content.It could slow down data and display refreshing
  use_colors_for_data = True
  ;Set to True to check and clean invalid asset folders when scraping or rebuilding data for UE assets
  check_asset_folders = True
  ;Set to True to browse for a folder when adding a new row. If false, an empty row will be added
  browse_when_add_row = True
  ;Number of Rows displayed or scraped per page.If this value is changed all the scraped files must be updated to match the new value
  rows_per_page = 37
  ;Delay in seconds when image cache will be invalidated. Default value represent 15 days
  image_cache_max_time = 1296000
  ;Folder (relative or absolute) to store images for assets
  asset_images_folder = K:/UE/UEVM/asset_images
  ;Folder (relative or absolute) to store the scraped files for the assets in markeplace
  scraping_folder = K:/UE/UEVM/scraping
  ;Folder (relative or absolute) to store result files to read and save data from
  results_folder = K:/UE/UEVM/results
  ;Minimal score required when looking for an url file comparing to an asset name. MUST BE LOWERCASE
  minimal_fuzzy_score_by_name = {"default": 70, "brushify": 90, "elite_landscapes": 90, "realistic landscapes": 100, "girl modular": 90}
  ;X position of the main windows. Set to 0 to center the window. Automatically saved on quit
  x_pos = 0
  ;Y position of the main windows. Set to 0 to center the window. Automatically saved on quit
  y_pos = 0
  ;Width of the main windows. Automatically saved on quit
  width = 1880
  ;Height of the main windows. Automatically saved on quit
  height = 1002
  ;File name of the last opened file. Automatically saved on quit
  last_opened_file = K:\UE\UEVM\scraping\assets.db
  ;The last opened Folder name. Automatically saved when browsing a folder
  last_opened_folder = G:\Assets\pour UE\02 Warez\Environments\Brushify\Brushify - Dunes Pack
  ;The last opened project name. Automatically saved when browsing a project folder
  last_opened_project = U:\UE_Big\UE_BigProjets\_EmptyForInstallTestsBBB
  ;The last opened Folder name. Automatically saved when browsing an engine folder
  last_opened_engine = R:\UnrealEngine\UE_5.1
  ;The last opened filter file name.Automatically saved when loading a filter.Leave empty to load no filter at start.Contains the file name only, not the path
  last_opened_filter =
  ;List of columns names that will be hidden when applying columns width. Note that the "Index_copy" will be hidden by default
  hidden_column_names = ["Uid","Release info","Urlslug"]
  ;Infos about columns of the table in SQLITE mode. Automatically saved on quit. Leave empty for default
  column_infos_sqlite = {"Asset_id": {"width": 174, "pos": 0}, "App name": {"width": 222, "pos": 1}, "Category": {"width": 112, "pos": 2}, "Review": {"width": 54, "pos": 3}, "Review count": {"width": 83, "pos": 4}, "Developer": {"width": -1, "pos": 5}, "Description": {"width": 205, "pos": 6}, "Status": {"width": 56, "pos": 7}, "Discount price": {"width": 61, "pos": 8}, "Discount percentage": {"width": 58, "pos": 9}, "Discounted": {"width": 71, "pos": 10}, "Is new": {"width": 48, "pos": 11}, "Free": {"width": 44, "pos": 12}, "Can purchase": {"width": -1, "pos": 13}, "Owned": {"width": 57, "pos": 14}, "Obsolete": {"width": 62, "pos": 15}, "Grab result": {"width": 79, "pos": 16}, "Price": {"width": 50, "pos": 17}, "Old price": {"width": 59, "pos": 18}, "Comment": {"width": 265, "pos": 19}, "Stars": {"width": 42, "pos": 20}, "Must buy": {"width": 59, "pos": 21}, "Test result": {"width": 69, "pos": 22}, "Installed folders": {"width": 150, "pos": 23}, "Alternative": {"width": -1, "pos": 24}, "Origin": {"width": 311, "pos": 25}, "Added manually": {"width": 44, "pos": 26}, "Custom attributes": {"width": 105, "pos": 27}, "Page title": {"width": 161, "pos": 28}, "Image": {"width": 50, "pos": 29}, "Url": {"width": 44, "pos": 30}, "Date added": {"width": 75, "pos": 31}, "Creation date": {"width": 86, "pos": 32}, "Update date": {"width": 79, "pos": 33}, "Asset slug": {"width": 65, "pos": 34}, "Tags": {"width": 228, "pos": 35}, "Downloaded size": {"width": 82, "pos": 36}, "Supported versions": {"width": 2, "pos": 37}, "Uid": {"width": 2, "pos": 38}, "Release info": {"width": 2, "pos": 39}, "Index copy": {"pos": 40, "width": 2}}
  ;Infos about columns of the table in FILE mode. Automatically saved on quit. Leave empty for default
  column_infos_file = {"Owned": {"width": 57, "pos": 0}, "App name": {"width": 222, "pos": 1}, "Category": {"width": 112, "pos": 2}, "Comment": {"width": 265, "pos": 3}, "Description": {"width": 205, "pos": 4}, "Discount price": {"width": 61, "pos": 5}, "Origin": {"width": 311, "pos": 6}, "Tags": {"width": 228, "pos": 7}, "Discount percentage": {"width": 58, "pos": 8}, "Review": {"width": 54, "pos": 9}, "Discounted": {"width": 71, "pos": 10}, "Is new": {"width": 48, "pos": 11}, "Free": {"width": 44, "pos": 12}, "Obsolete": {"width": 62, "pos": 13}, "Must buy": {"width": 59, "pos": 14}, "Added manually": {"width": 44, "pos": 15}, "Grab result": {"width": 79, "pos": 16}, "Price": {"width": 50, "pos": 17}, "Asset_id": {"width": 174, "pos": 18}, "Review count": {"width": 83, "pos": 19}, "Can purchase": {"width": -1, "pos": 20}, "Status": {"width": 56, "pos": 21}, "Old price": {"width": 59, "pos": 22}, "Developer": {"width": -1, "pos": 23}, "Stars": {"width": 42, "pos": 24}, "Test result": {"width": 69, "pos": 25}, "Alternative": {"width": -1, "pos": 26}, "Custom attributes": {"width": 105, "pos": 27}, "Downloaded size": {"width": 82, "pos": 28}, "Page title": {"width": 161, "pos": 29}, "Image": {"width": 50, "pos": 30}, "Url": {"width": 44, "pos": 31}, "Date added": {"width": 75, "pos": 32}, "Creation date": {"width": 86, "pos": 33}, "Update date": {"width": 79, "pos": 34}, "Asset slug": {"width": 65, "pos": 35}, "Installed folders": {"width": 150, "pos": 36}, "Uid": {"width": 2, "pos": 37}, "Supported versions": {"width": 2, "pos": 38}, "Release info": {"width": 2, "pos": 39}, "App title": {"width": 2, "pos": 40}, "urlSlug": {"width": 2, "pos": 41}, "Index copy": {"pos": 42, "width": 2}}
  ;DEV ONLY. NO CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Column name to sort the assets from the database followed by ASC or DESC (optional).
  ;assets_order_col = date_added
  assets_order_col = asset_id ASC
  ;DEV ONLY. NO CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING. Value that can be changed in live to switch some behaviours whithout quitting.
  testing_switch = 0



Note that some other settings for the new GUI are managed by a dedicated python file ``<python install folder>/<source folder of the package>/tkgui/modules/GuiSettingsClass.py``

For instance, the location is:

-  for Linux: ``~/.local/lib/python3.10/site-packages/UEVaultManager/tkgui/modules/GuiSettingsClass.py``
-  for Windows: ``c:\python3.10\site-packages\UEVaultManager\tkgui\modules\GuiSettingsClass.py``

The final path can depend on your installation.
