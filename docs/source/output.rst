Output Format and file
----------------------
.. _output:

Log files and debug
~~~~~~~~~~~~~~~~~~~

3 different log files could be used during the process Use the config
file to set their file name (and path). If a file name is missing, empty
or set to ’’ the corresponding log feature will be disabled.

-  ignored assets file log

   -  file is defined by the setting: ‘ignored_assets_filename_log
      (default is ~/.config/ignored_assets.log)’
   -  each asset listed in the file has been ignored during the process.
      Possible reasons are: not a UE asset, not an asset, asset filtered
      by category (-fc option)

-  not found assets log

   -  file is defined by the setting: ‘notfound_assets_filename_log
      (default is ~/.config/notfound_assets.log)’
   -  each asset listed in the file has not been found during the
      grabbing process (extras data). Possible reasons are: invalid,
      obsolete or removed from the marketplace

-  bad data assets log

   -  file is defined by the setting: ‘bad_data_assets_filename_log
      (default is ~/.config/bad_data_assets.log)’
   -  each asset listed has different value in extras data and metadata.
      Reasons is: ambiguous asset name that leaded to an invalid search
      result during the grabbing process. See the :ref:`how-to-fix-invalid-search-result-during-the-grabbing-process`
      section.

The output file
~~~~~~~~~~~~~~~

The result of the listing can be displayed on the console where the app
has been launched. This is done by default. But it can also be saved in
a csv or a json file for a future use.

The script use a (hardcoded) boolean value to know if the content of the
field is “protected” and must be preserved before overwriting an
existing output file.

This feature goal is to avoid overwriting data that could have been
manually changed by the user in the output file between successive runs.
As it, if the user manually change the content of some data in the file,
by adding a comment for instance, this data WON’T be overwritten. Also
Note that if ``create_output_backup = true`` is set in the config file,
the app will create a backup of the output file suffixed by a timestamp
before overwriting the result file.

These are the fields (or column headings) that will be written in that
order into the CSV file (or the names of the fields ins the Json file).
The value is False if its content is not preserved, and True if it is
preserved (and can be used to store persistant data).

These value are defined by the CSV_headings variable at the beginning of
the
`core.py <https://github.com/LaurentOngaro/UEVaultManager/blob/UEVaultManager/UEVaultManager/core.py>`__
file:

.. code:: python

  CSV_headings = {
      'Asset_id': False,  # ! important: Do not Rename => this field is used as main key for each asset
      'App name': False,
      'App title': False,
      'Category': False,
      'Review': False,
      'Developer': False,
      'Description': False,
      'Status': False,
      'Discount Price': False,
      'On sale': False,
      'Purchased': False,
      'Obsolete': True,
      'Supported Versions': False,
      'Grab result': False,
      'Price': False,  # ! important: Rename Wisely => this field is searched by text in the next lines
      'Old Price': False,  # ! important: always place it after the Price field in the list
      # User Fields
      'Comment': True,
      'Stars': True,
      'Must Buy': True,
      'Test result': True,
      'Installed Folder': True,
      'Alternative': True,
      'Asset Folder': True,
      # less important fields
      'Page title': False,
      'Image': False,
      'Url': True,  # could be kept if a better url that can be used to download the asset is found
      'Compatible Versions': False,
      'Date Added': True,
      'Creation Date': False,
      'Update Date': False,
      'UE Version': False,
      'Uid': False
  }

The individual json files
~~~~~~~~~~~~~~~~~~~~~~~~~

Each asset will also have its data saved in to different json files:

-  the folder ``<data folder>/metadata``: contains a json file for each
   asset (identified by its ‘asset_id’) to store its metadata (get from
   a call to the epic API)
-  the folder ``<data folder>/extras``: contains a json file for each
   asset (identified by its ‘asset_id’) to store its ‘extras data’
   (grabbed from the marketplace page of the asset)

Note:

-  filtering data (using the -fc optional arguments) occurs BEFORE
   saving extras data
-  some “extras” json files can be missing where the corresponding
   “metadata” json file is present, that’s because some data could have
   not been grabbed or the asset page not found during the process.
-  the grabbing processing for extras data is using a text based search,
   so the analysed asset page could be the bad one and results could be
   taken for another asset. See the :ref:`how-to-fix-invalid-search-result-during-the-grabbing-process`
   section.

.. _how-to-fix-invalid-search-result-during-the-grabbing-process:

how to fix invalid search result during the grabbing process
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The grabbing processing for extras data is using a text based search
(partial and case-insensitive). By default, only the first result of
this search is taken as the corresponding asset. When the asset name,
which must be converted to be used as a search keyword, is ambiguous,
the search could provide several results or even a wrong result (an
asset that don’t correspond).

So, in that case, the asset page that is analyzed could be the bad one
and grabbed data could be taken for the wrong asset.

To limit this error, a text comparison is done between the asset title
in the metadata and the title in the asset page. If the values are
different, the asset name is added to the file pointed by the
“bad_data_assets_filename_log” value of the config file and its ” error”
field will contain a value different from 0. Each value correspond to a
specific error code (see :ref:`possible-values-in-the-error-field`)

To fix that, the search of the correct url for the asset must be done
and validated manually.

Once validated, the correct URL could be added into the result file,
inside the Url field. As this field is marked as “protected”, it won’t
be overwritten on the next data update and will be used as a source url
for the page to be grabbed instead of making a new search for the asset
page. (THIS IS STILL TO BE DONE / TODO)

**Please Note that the user is responsable for respecting the attended
format of the result file when modifying its content. Breaking its
structure will probably result in losing the data the user has modified
in the file when the application will be executed next time.**

Making a backup before any manual modification is certainly a good idea.
Using a tool (e.g. a linter) to check if the structure of the file (json
or CSV) is still correct before running the application again is also a
very good idea.

.. _possible-values-in-the-error-field:

possible values in the error Field
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The “Grab result” field of each asset contains a value that indicate how
the process has run. These code are defined by the following enum at the
beginning of the
`api/egs.py <https://github.com/LaurentOngaro/UEVaultManager/blob/UEVaultManager/UEVaultManager/api/egs.py>`__
file:

.. code:: python

   class GrabResult(Enum):
       NO_ERROR = 0
       INCONSISTANT_DATA = 1
       PAGE_NOT_FOUND = 2
       CONTENT_NOT_FOUND = 3
       TIMEOUT = 4
