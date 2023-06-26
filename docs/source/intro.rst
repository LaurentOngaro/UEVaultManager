UEVaultManager
==============
.. _intro:

A free and open-source Epic Games Assets Manager for Unreal Engine
------------------------------------------------------------------

*An Epic Launcher Asset management alternative available on all
Platforms*

UEVaultManager is an open-source assets manager that can list assets and
their data from the Epic Games Marketplace. It's developed in Python, so
it can run on any platform that support this language.

Its main purpose is to list the assets (with or without user login),
filter (optional) and save the list into a file that can be reused later
as a data source (in an Excel sheet for instance).

Please read the :doc:`configuration` and :doc:`usage` sections before creating an issue to avoid invalid
issue reports.

Note:
~~~~~~

UEVaultManager can be run as a CLI (command-line interface) application, it has to be run from a
terminal (e.g. a Linux Shell, a PowerShell or a Dos Console).

Since the version 1.1.0, the app can edit the content of a previous assets scan (using the 'list' or the 'scrap' commands).
This feature offers GUI interface to edit the assets list, and to add or edit the user data for each asset.

If you find a problem with this app, please note that it's a free app,
and it 's made on my spare time. So be patient and comprehensive, you
can try to solve it by your own means if possible.

If you're stuck, you can `create an issue on
GitHub <https://github.com/LaurentOngaro/UEVaultManager/issues/new/choose>`__,
so I'll be aware of, and I'll try to fix it, as quick as I can.

**All bug reports, PR, ideas, improvement suggestions, code correction...
are welcome !**

Released under `GNU General Public License
v3.0 <https://github.com/LaurentOngaro/UEVaultManager/blob/UEVaultManager/LICENSE>`__

**THIS TOOL IS PROVIDED AS IT IS. NO WARRANTY . AND, PLEASE, NO COMPLAIN
. THANKS**

Implemented Features:
~~~~~~~~~~~~~~~~~~~~~

-  Authenticating with Epic's service
-  Listing and getting data about assets

   -  all the metadata that were already downloaded before by legendary:
      name, title, id, description, UE versions...
   -  **extras data grabbed from the marketplace page of an asset :
      price, review, tags, owned or not...**
-  **Scraping the marketplace page of an asset to get all the data using the EPIC MARKETPLACE API (since the version 1.8.0)**
-  Since version 1.8.0, the app can also use a sqlite database to store
   the data and, as it, it could list ALLthe assets available on the marketplace (and not only the ones you own like in the previous versions).
-  Using a cache system to avoid getting data using API calls and web
   scraping each time the app is run. The delay of cache conservation
   can be set in the configuration file
-  **Filtering the asset list by category before their listing (using the
   "-fc | -filter-category" optional argument)**
-  **Saving the resulting list in a csv or a json file (using the "-o |
   -output" optional argument)**
-  Saving the metadata and the extras data in individual json files (one
   for each asset) in sub-folders of the config folder
-  **Editing the content of a result file (json or csv) using a GUI (since the version 1.1.0)**
-  Preserving user data for each asset (see the :doc:`output` section).

   -  Some fields in the result file (comments, personal note...) will be
      protected and not overwritten by a future data update.

Planned Features
~~~~~~~~~~~~~~~~

Since version 1.4.3, the features can be listed using special Labels in the GitHub issues list.

-  `planed enhancements <https://github.com/LaurentOngaro/UEVaultManager/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement>`__
-  `ascetic improvments <https://github.com/LaurentOngaro/UEVaultManager/labels/ascetic%20only>`__
-  `ideas <https://github.com/LaurentOngaro/UEVaultManager/labels/idea>`__

Special thanks
~~~~~~~~~~~~~~

Legendary team
^^^^^^^^^^^^^^

This code was mainly a lighter, cleaned and improved version of the
`Legendary <https://github.com/derrod/legendary>`__ tool code base, with
some addition regarding the listing and the management of unreal engine
marketplace assets. So Thanks to the Legendary team for the fantastic
work on their tool !!

Till now, without it and its server REST API, This app won't be able to
use the Epic API, specially the authentication part.

Jetbrains
^^^^^^^^^

I intensively use JetBrains software for developing all my projects.

Thanks to JetBrains for their support on this project through their
`License Program For non-commercial open source
development <https://www.jetbrains.com/community/opensource/#support>`__

Their tools are great ! If you don't know them, you should give them a
try.


Known bugs and limitations
--------------------------
