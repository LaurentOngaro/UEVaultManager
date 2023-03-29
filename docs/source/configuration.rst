Configuration
-------------
.. _configuration:

Config folder
~~~~~~~~~~~~~

Configuration file, log files and results files are stored by default in
the of the app.

The location is:

-  for Linux: ``~/.config/UEVaultManager/``
-  for Windows: ``C:\users\<you_login_name>\.config\UEVaultManager\``

Config file
~~~~~~~~~~~

UEVaultManager supports some settings in its config file
``<data folder>/config.ini``:

This is an example of this file content and the settings you can change:

.. code:: ini

   [UEVaultManager]
   log_level = debug
   ; locale override, must be in RFC 1766 format (e.g. "en-US")
   locale = fr-FR
   ; path to the "Manifests" folder in the EGL ProgramData directory
   egl_programdata = C:/ProgramData/Epic/EpicGamesLauncher/Data/Manifests
   ; Disables the automatic update check
   disable_update_check = true
   ; Disables the notice about an available update on exit
   disable_update_notice = true
   ; Disable automatically-generated aliases
   disable_auto_aliasing = false
   ; Create a backup of the output file (when using the --output option) suffixed by a timestamp before creating a new file
   create_output_backup = true
   ; Create a backup of the log files that store asset analysis suffixed by a timestamp
   create_log_backup = True
   ; Print more information during long operations
   verbose_mode = true
   ; Delay (in seconds) when UE assets metadata cache will be invalidated. Default value is 15 days
   ue_assets_max_cache_duration = 1296000
   ; Set the file name (and path) for logging issues with assets when running the --list command
   ; Set to  to disabled this feature
   ; use "~/" at the start of the filename to store it relatively to the user directory
   ignored_assets_filename_log = ~/.config/ignored_assets.log
   notfound_assets_filename_log = ~/.config/notfound_assets.log
   bad_data_assets_filename_log = ~/.config/bad_data_assets.log
