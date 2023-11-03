Output Format and file
----------------------
.. _output:

Log files and debug
~~~~~~~~~~~~~~~~~~~

3 different log files could be used during the process Use the config
file to set their file name (and path). If a file name is missing, empty
or set to '' the corresponding log feature will be disabled.

-  ignored assets file log

   -  file is defined by the setting: `ignored_assets_filename_log`
      (default is ``~/.config/ignored_assets.log``)
   -  each asset listed in the file has been ignored during the process.
      Possible reasons are: asset filtered by category (list with -fc option)

-  not found assets log

   -  file is defined by the setting: `notfound_assets_filename_log`
      (default is ``~/.config/notfound_assets.log``)
   -  each asset listed in the file has not been found during the
      scraping process. Possible reasons are: invalid url,
      obsolete or removed from the marketplace

-  folder scanning for assets log

   -  file is defined by the setting: `scan_assets_filename_log`
      (default is ``~/.config/scan_assets_filename_log.log``)
   -  each scanned folder is listed here whith the result of the scan


-  assets scraping log

   -  file is defined by the setting: `scrap_assets_filename_log`
      (default is ``~/.config/scan_assets.log``)
   -  each scraped asset is listed here whith the result of the scan


The output file
~~~~~~~~~~~~~~~

The result of the listing can be displayed on the console where the application
has been launched. This is done by default. But it can also be saved in
a csv or a json file for a future use.

The script use a (hardcoded) boolean value to know if the content of the
field is `protected` and must be preserved before overwriting an
existing output file.

This feature goal is to avoid overwriting data that could have been
manually changed by the user in the output file between successive runs.
As it, if the user manually change the content of some data in the file,
by adding a comment for instance, this data WON'T be overwritten. Also
Note that if `create_output_backup = true` is set in the config file,
the application will create a backup of the output file suffixed by a timestamp
before overwriting the result file.

These are the fields (or column headings) that will be written in that
order into the CSV file (or the names of the fields ins the Json file).
The value is False if its content is not preserved, and True if it is
preserved (and can be used to store persistant data).

These value are defined by the csv_sql_fields variable at the beginning of
the
`core.py <https://github.com/LaurentOngaro/UEVaultManager/blob/UEVaultManager/models/csv_data.py>`__
file:

.. code:: python

  csv_sql_fields = {
      # fields mapping from csv to sql
      # key: csv field name, value: {sql name, state }
      # some field are intentionnaly duplicated because
      #   several CSV fields could come from a same database field
      #   a csv field with this name must exist to get the value
      'Asset_id': {
          'sql_name': 'asset_id',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'App name': {
          'sql_name': 'title',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'App title': {
          # intentionnaly duplicated
          'sql_name': 'title',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Category': {
          'sql_name': 'category',
          'state': CSVFieldState.CHANGED,
          'field_type': CSVFieldType.LIST
      },
      'Review': {
          'sql_name': 'review',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.FLOAT
      },
      'Review count': {
          # not in "standard/result" csv file
          'sql_name': 'review_count',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.INT
      },
      'Developer': {
          'sql_name': 'author',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Description': {
          'sql_name': 'description',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.TEXT
      },
      'Status': {
          'sql_name': 'status',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Discount price': {
          'sql_name': 'discount_price',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.FLOAT
      },
      'Discount percentage': {
          'sql_name': 'discount_percentage',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.INT
      },
      'Discounted': {
          'sql_name': 'discounted',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.BOOL
      },
      'Is new': {
          # not in "standard/result" csv file
          'sql_name': 'is_new',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.BOOL
      },
      'Free': {
          # not in "standard/result" csv file
          'sql_name': 'free',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.BOOL
      },
      'Can purchase': {
          # not in "standard/result" csv file
          'sql_name': 'can_purchase',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.BOOL
      },
      'Owned': {
          'sql_name': 'owned',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.BOOL
      },
      'Obsolete': {
          'sql_name': 'obsolete',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.BOOL
      },
      'Supported versions': {
          'sql_name': 'supported_versions',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Grab result': {
          'sql_name': 'grab_result',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.LIST
      },
      'Price': {
          'sql_name': 'price',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.FLOAT
      },
      'Old price': {
          'sql_name': 'old_price',
          'state': CSVFieldState.CHANGED,
          'field_type': CSVFieldType.FLOAT
      },
      # ## User Fields
      'Comment': {
          'sql_name': 'comment',
          'state': CSVFieldState.USER,
          'field_type': CSVFieldType.TEXT
      },
      'Stars': {
          'sql_name': 'stars',
          'state': CSVFieldState.USER,
          'field_type': CSVFieldType.INT
      },
      'Must buy': {
          'sql_name': 'must_buy',
          'state': CSVFieldState.USER,
          'field_type': CSVFieldType.BOOL
      },
      'Test result': {
          'sql_name': 'test_result',
          'state': CSVFieldState.USER,
          'field_type': CSVFieldType.STR
      },
      'Installed folders': {
          'sql_name': 'installed_folders',
          'state': CSVFieldState.USER,
          'field_type': CSVFieldType.STR
      },
      'Alternative': {
          'sql_name': 'alternative',
          'state': CSVFieldState.USER,
          'field_type': CSVFieldType.STR
      },
      'Origin': {
          'sql_name': 'origin',
          'state': CSVFieldState.CHANGED,
          'field_type': CSVFieldType.STR
      },
      'Added manually': {
          'sql_name': 'added_manually',
          'state': CSVFieldState.USER,
          'field_type': CSVFieldType.BOOL
      },
      # ## less important fields
      'Custom attributes': {
          # not in "standard/result" csv file
          'sql_name': 'custom_attributes',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Page title': {
          'sql_name': 'page_title',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Image': {
          'sql_name': 'thumbnail_url',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Url': {
          'sql_name': 'asset_url',
          'state': CSVFieldState.CHANGED,
          'field_type': CSVFieldType.STR
      },
      'Compatible versions': {
          # not in database
          'sql_name': None,
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Date added': {
          'sql_name': 'date_added',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.DATETIME
      },
      'Creation date': {
          'sql_name': 'creation_date',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.DATETIME
      },
      'Update date': {
          'sql_name': 'update_date',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.DATETIME
      },
      'UE version': {
          # not in database
          'sql_name': None,
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Uid': {
          'sql_name': 'id',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      # ## UE asset class field only
      'Namespace': {
          'sql_name': 'namespace',
          'state': CSVFieldState.ASSET_ONLY,
          'field_type': CSVFieldType.STR
      },
      'Catalog itemid': {
          'sql_name': 'catalog_item_id',
          'state': CSVFieldState.ASSET_ONLY,
          'field_type': CSVFieldType.STR
      },
      'Asset slug': {
          'sql_name': 'asset_slug',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Currency code': {
          'sql_name': 'currency_code',
          'state': CSVFieldState.ASSET_ONLY,
          'field_type': CSVFieldType.STR
      },
      'Technical details': {
          'sql_name': 'technical_details',
          'state': CSVFieldState.ASSET_ONLY,
          'field_type': CSVFieldType.STR
      },
      'Long description': {
          'sql_name': 'long_description',
          'state': CSVFieldState.ASSET_ONLY,
          'field_type': CSVFieldType.TEXT
      },
      'Tags': {
          'sql_name': 'tags',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Comment rating id': {
          'sql_name': 'comment_rating_id',
          'state': CSVFieldState.ASSET_ONLY,
          'field_type': CSVFieldType.STR
      },
      'Rating id': {
          'sql_name': 'rating_id',
          'state': CSVFieldState.ASSET_ONLY,
          'field_type': CSVFieldType.STR
      },
      'Is catalog item': {
          'sql_name': 'is_catalog_item',
          'state': CSVFieldState.ASSET_ONLY,
          'field_type': CSVFieldType.BOOL
      },
      'Thumbnail': {
          # intentionnaly duplicated
          'sql_name': 'thumbnail_url',
          'state': CSVFieldState.ASSET_ONLY,
          'field_type': CSVFieldType.STR
      },
      'Release info': {
          'sql_name': 'release_info',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
      'Downloaded size': {
          'sql_name': 'downloaded_size',
          'state': CSVFieldState.NORMAL,
          'field_type': CSVFieldType.STR
      },
  }


The individual json files
~~~~~~~~~~~~~~~~~~~~~~~~~

Each asset will also have its data saved in to different json files:

-  for the all the assets available in the marketplace (including the owned ones):

  -  the folder ``<Scraping folder>/assets``: contains a json file for each
     asset (identified by its `asset_id` is the asset has one) to store its metadata (get from
     a call to the epic API). The <Scraping folder> can be set in the ``<config folder>/config_gui.ini`` configuration file

-  for the assets OWNED by the user

  -  the folder ``<Scraping folder>/owned``: contains a json file for each
     asset (identified by its `asset_id` is the asset has one) to store its metadata (get from
     a call to the epic API). The <Scraping folder> can be set in the ``<config folder>/config_gui.ini`` configuration file


.. _how-to-fix-invalid-search-result-during-the-scrapin-process:

how to fix invalid search result during the scraping process
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The INDIVIDUAL scraping process (i.e. click on the "Scrap" or "Scrap range" buttons
some a text based search (partial and case-insensitive) can be used if the url of the asset is invalid.
By default, only the first result of this search is taken as the corresponding asset. When the asset name,
which must be converted to be used as a search keyword, is ambiguous,the search could provide several
results or even a wrong result (an asset that don't correspond).

So, in that case, the asset page that is analyzed could be the bad one
and grabbed data could be taken for the wrong asset.

To limit this error, a text comparison is done between the asset title
in the metadata and the title in the asset page. If the values are
different, its `Grab Result` field will contain a value different from NO_ERROR.
Each value correspond to a specific status code (see :ref:`possible-values-in-the-error-field`)

To fix that, the search of the correct url for the asset must be done
and validated manually.

Once validated, the correct URL could be added into the result file,
inside the Url field. As this field is marked as `USER`, it won't
be overwritten on the next data update and will be used as a source url
for the page to be grabbed instead of making a new search for the asset
page.

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

The `Grab result` field of each asset contains a value that indicate how
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
      PARTIAL = 5  # when asset has been added when owned asset data only (less complete that "standard" asset data)
      NO_APPID = 6  # no appid found in the data (will produce a file name like '_no_appId_asset_1e10acc0cca34d5c8ff7f0ab57e7f89f
      NO_RESPONSE = 7  # the url does not return HTTP 200
