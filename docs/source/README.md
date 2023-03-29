# UEVaultManager

## A free and open-source Epic Games Assets Manager for Unreal Engine

_An Epic Launcher Asset management alternative available on all Platforms_

UEVaultManager is an open-source assets manager that can list assets and their data from the Epic Games Marketplace.
It's developed in Python, so it can run on any platform that support this language.

Its main purpose is to list the assets (with or without user login), filter (optional) and save the list into a file that can be reused later as a
data source (in an Excel sheet for instance).

In future versions, this application will also offer a GUI, and will be able to read directly the result file, display and edit the assets list.

Please read the [config file](#config-file) and [cli usage](#usage) sections before creating an issue to avoid invalid issue reports.

### Notes:

UEVaultManager is currently a CLI (command-line interface) application without a graphical user interface (GUI),
it has to be run from a terminal (e.g. a Linux Shell, a PowerShell or a Dos Console)

If you find a problem with this app, please note that it's a free app, and it 's made on my spare time.
So be patient and comprehensive, you can try to solve it by your own means if possible.

If you're stuck, you can [create an issue on GitHub](https://github.com/LaurentOngaro/UEVaultManager/issues/new/choose), so I'll be aware of, and I'll
try to fix it, as quick as I can.

_**All bug reports, PR, ideas, improvement suggestions, code correction... are welcome !**_

Released under [GNU General Public License v3.0](https://github.com/LaurentOngaro/UEVaultManager/blob/UEVaultManager/LICENSE)

**THIS TOOL IS PROVIDED AS IT IS. NO WARRANTY . AND, PLEASE, NO COMPLAIN . THANKS**

### Implemented Features:

- Authenticating with Epic's service
- Listing and getting data about assets
  - all the metadata that were already downloaded before by legendary: name, title, id, description, UE versions...
  - **extras data grabbed from the marketplace page of an asset : price, review, tags, purchased or not...**
- Using a cache system to avoid getting data using API calls and web scrapping each time the app is run. The delay of cache conservation can
  be set in the configuration file
- **Filtering the asset list by category before their listing (via the -fc | --filter-category optional arguments)**
- **Saving the resulting list in a csv or a json file (via the -o | --output optional arguments)**
- Saving the metadata and the extras data in individual json files (one for each asset) in sub-folders of the config folder
- Preserving user data for each asset (see the [Output file](#the-output-file) section below).
  - Some fiels in the result file (comments, personal note...) will be protected and not overwritten by a future data update.

### Planned Features

#### WIP

- Use an alternative url as source of data for the asset. Currently, the url is grabbed from the result page when searching the marketplace for the
  title of the asset.
- Grabbing tags and saving in the asset marketplace
- Simple GUI for managing assets
- Editing all the assets data using a GUI

#### Not for now

- Install and download assets into Unreal Engine VaultCache or into a project folder (Same feature as in Epic Game launcher)

### Special thanks

#### Legendary team

<img src="https://repository-images.githubusercontent.com/249938026/80b18f80-96c7-11ea-9183-0a8c96e7cada" height="50" alt="jetbrains LOGO">

This code was mainly a lighter, cleaned and improved version of the [Legendary](https://github.com/derrod/legendary) tool code base, with some
addition regarding the listing
and the management of unreal engine marketplace assets.
So Thanks to the Legendary team for the fantastic work on their tool !!

Till now, without it and its server REST API, This app won't be able to use the Epic API, specially the authentication part.

#### Jetbrains

<img src="https://resources.jetbrains.com/storage/products/company/brand/logos/jb_beam.png" height="50" alt="jetbrains LOGO">

I intensively use JetBrains software for developing all my projects.

Thanks to JetBrains for their support on this project through
their [License Program For non-commercial open source development](https://www.jetbrains.com/community/opensource/#support)

They tools are great ! If you don't know them, you should give them a try.

## How to run/install

### Requirements

- Linux, Windows (8.1+), or macOS (12.0+)
  - 32-bit operating systems are not supported
- PyPI packages:
  - `requests`
  - (optional) `setuptools` and `wheel` for setup/building
  - (optional but recommended) `pywebview` for webview-based login

### Prerequisites

- Be sure that pip is installed by running
  - for Linux or macOS (12.0+): `sudo apt install python3-pip` or `python -m ensurepip` or `python3 -m ensurepip` (depending on you os version)
  - for Windows: `python -m ensurepip`
- To prevent problems with permissions during installation, please upgrade your `pip` by running `python -m pip install -U pip --user`.
- Install python3.9, setuptools, wheel, and requests

> **Tip:** You may need to replace `python` in the above command with `python3` on Linux/macOS.

### Directly from the repo

#### Windows example

1. First install the Python language (3.9 minimal version required) as explained on
   the [official python website](https://www.python.org/downloads/windows/)
2. create a folder for storing the source files
3. open a command prompt or a terminal from this folder.
4. run the following commands:

```sh
git clone https://github.com/LaurentOngaro/UEVaultManager.git
python3 -m pip install bs4
cd UEVaultManager
pip install .
```

#### Ubuntu 20.04 example

Ubuntu 20.04's standard repositories include everything needed to install UEVaultManager:

```sh
sudo apt install python3 python3-requests python3-setuptools-git
python3 -m pip install bs4
git clone https://github.com/LaurentOngaro/UEVaultManager.git
cd UEVaultManager
pip install .
```

If the `UEVaultManager` executable is not available after installation, you may need to configure your `PATH` correctly. You can do this by running
the command:

```sh
echo 'export PATH=$PATH:~/.local/bin' >> ~/.profile && source ~/.profile
```

### Direct installation (any)

#### Python Package on [pypi](https://pypi.org) (any)

```sh
pip install UEVaultManager
```

> **Tip:** You may need to replace `python` in the above command with `python3` on Linux/macOS.

#### Windows Binaries from repos

**NOT DONE FOR NOW / TODO**

Download the `uevaultmanager` or `uevaultmanager.exe` binary
from [the latest release](https://github.com/LaurentOngaro/UEVaultManager/releases/latest)
and move it to somewhere in your `$PATH`/`%PATH%`. Don't forget to `chmod +x` it on Linux/macOS.

The Windows .exe and Linux/macOS executable were created with PyInstaller and will run standalone even without python being installed.
Note that on Linux glibc >= 2.25 is required, so older distributions such as Ubuntu 16.04 or Debian stretch will not work.

## Quickstart

**Tip:** When using PowerShell with the standalone executable, you may need to replace `UEVaultManager` with `.\UEVaultManager` in the commands below.

### log in:

```sh
UEVaultManager auth
```

If the pywebview package is installed (that is done by the installation process), this should open a new window with the Epic Login.

Otherwise, authentication is a little finicky since we have to go through the Epic website and manually copy a code.
The login page should open in your browser and after logging in you should be presented with a JSON response that contains a code ("
authorizationCode"), just copy the code into the terminal and hit enter.

Alternatively you can use the `--import` flag to import the authentication from the Epic Games Launcher

Note that this will log you out of the Epic Launcher.

### Listing your asset

```sh
UEVaultManager list
```

This will fetch a list of asset available on your account, the first time may take a while depending on how many asset you have.

### Saving the list into a CSV file

```sh
UEVaultManager list -o "c:/ue_asset_list.csv"
```

You can edit some data in this file
You can update the data in the file by running the same command again.
Your changes could be preserved, depending on what fields (aka. columns) has been changed (see [the output file section](#the-output-file) bellow).

## Usage

```text
usage: UEVaultManager [-h] [-H] [-d] [-y] [-V] [-c <file>] [-J] [-A <seconds>] <command> ...

exemple: 
  
  UEVaultManager list --csv -fc "plugin" --output "D:\testing\list.csv"
  
  Will list all the assets of the marketplace that have "plugin" it their category field (on the marketplace) and save the result using a csv format 
  into the "D:\testing\list.csv" file 

optional arguments:
  -h, --help            Show this help message and exit
  -H, --full-help       Show full help (including individual command help)
  -d, --debug           Set loglevel to debug
  -y, --yes             Default to yes for all prompts
  -V, --version         Print version and exit
  -c, --config-file     Overwrite the default configuration file name to use
  -J, --pretty-json     Pretty-print JSON. Improve readability

  -A <seconds>, --api-timeout <seconds>
                        API HTTP request timeout (default: 10 seconds)

Commands:
  <command>
    auth                Authenticate with the Epic Games Store
    cleanup             Remove old temporary, metadata, and manifest files
    info                Prints info about specified app name or manifest
    list                List available assets. It could take some time.
    list-files          List files in manifest
    status              Show UEVaultManager status information. Will update the assets list and could take some time.

Individual command help:

Command: auth
usage: UEVaultManager auth [-h] [--import] [--code <exchange code>] [--token <exchange token>]
                      [--sid <session id>] [--delete] [--disable-webview]

optional arguments:
  -h, --help            Show this help message and exit
  --import              Import Epic Games Launcher authentication data (logs
                        out of EGL)
  --code <authorization code>
                        Use specified authorization code instead of interactive authentication
  --token <exchange token>
                        Use specified exchange token instead of interactive authentication
  --sid <session id>    Use specified session id instead of interactive
                        authentication
  --delete              Remove existing authentication (log out)
  --disable-webview     Do not use embedded browser for login


Command: cleanup
usage: legendary cleanup [-h] [--delete-metadata] [--delete-extras-data]

optional arguments:
  -h, --help                Show this help message and exit
  -m, --delete-metadata     Also delete metadata files. They are kept by default
  -e, --delete-extras-data  Also delete extras data files. They are kept by default'


Command: info
usage: UEVaultManager info [-h] [--offline] [--json] [--force-refresh]
                      <App Name/Manifest URI>

positional arguments:
  <App Name/Manifest URI>
                        App name or manifest path/URI

optional arguments:
  -h, --help            Show this help message and exit
  --offline             Only print info available offline
  --json                Output information in JSON format
  -f, --force-refresh   Force a refresh of all asset metadata

Command: list
usage: UEVaultManager list [-h] [----third-party] [--csv]
                      [--tsv] [--json] [--force-refresh] 
                      [--filter-category <text_to_search>] [--output <file_name_with_path>] 

optional arguments:
  -h, --help              Show this help message and exit
  -T, --third-party       Include assets that are not installable
  --csv                   List asset in CSV format
  --tsv                   List asset in TSV format
  --json                  List asset in JSON format
  -f, --force-refresh     Force a refresh of all asset metadata
  -fc, --filter-category  Filter assets by category. Search against the asset category in the marketplace. Search is case insensitive and can be partial
  -o, --output            The file name (with path) where the list should be written to



Command: list-files
usage: UEVaultManager list-files [-h] [--manifest <uri>] [--csv] [--tsv] [--json]
                            [--hashlist] [--force-refresh]
                            [<App Name>]

positional arguments:
  <App Name>            Name of the app (optional)

optional arguments:
  -h, --help            Show this help message and exit
  --manifest <uri>      Manifest URL or path to use instead of the CDN one
  --csv                 Output in CSV format
  --tsv                 Output in TSV format
  --json                Output in JSON format
  --hashlist            Output file hash list in hashcheck/sha1sum -c
                        compatible format
  -f, --force-refresh   Force a refresh of all asset metadata


Command: status
usage: UEVaultManager status [-h] [--offline] [--json]

optional arguments:
  -h, --help            Show this help message and exit
  --offline             Only print offline status information, do not login
  --json                Show status in JSON format

```

## Configuration

### Config folder

Configuration file, log files and results files are stored by default in the <data folder> of the app.

The <data folder> location is:

- for Linux: `~/.config/UEVaultManager/`
- for Windows: `C:\users\<you_login_name>\.config\UEVaultManager\`

### Config file

UEVaultManager supports some settings in its config file `<data folder>/config.ini`:

This is an example of this file content and the settings you can change:

```ini
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
```

## Output Format and file

### Log files and debug

3 different log files could be used during the process
Use the config file to set their file name (and path).
If a file name is missing, empty or set to '' the corresponding log feature will be disabled.

- ignored assets file log
  - file is defined by the setting: 'ignored_assets_filename_log (default is ~/.config/ignored_assets.log)'
  - each asset listed in the file has been ignored during the process. Possible reasons are: not a UE asset, not an asset, asset filtered by
    category (-fc option)
- not found assets log
  - file is defined by the setting: 'notfound_assets_filename_log (default is ~/.config/notfound_assets.log)'
  - each asset listed in the file has not been found during the grabbing process (extras data). Possible reasons are: invalid, obsolete or removed
    from the marketplace
- bad data assets log
  - file is defined by the setting: 'bad_data_assets_filename_log  (default is ~/.config/bad_data_assets.log)'
  - each asset listed has different value in extras data and metadata. Reasons is: ambiguous asset name that leaded to an invalid search result during
    the grabbing process.
    See the [how to fix invalid search result during the grabbing process](#how-to-fix-invalid-search-result-during-the-grabbing-process) section
    bellow

### The output file

The result of the listing can be displayed on the console where the app has been launched.
This is done by default.
But it can also be saved in a csv or a json file for a future use.

The script use a (hardcoded) boolean value to know if the content of the field is "protected" and must be preserved before overwriting an existing
output file.

This feature goal is to avoid overwriting data that could have been manually changed by the user in the output file between successive runs.
As it, if the user manually change the content of some data in the file, by adding a comment for instance, this data WON'T be overwritten.
Also Note that if `create_output_backup = true` is set in the config file, the app will create a backup of the output file suffixed by a timestamp
before overwriting the result file.

These are the fields (or column headings) that will be written in that order into the CSV file (or the names of the fields ins the Json file).
The value is False if its content is not preserved, and True if it is preserved (and can be used to store persistant data).

These value are defined by the CSV_headings variable at the beginning of
the [core.py](https://github.com/LaurentOngaro/UEVaultManager/blob/UEVaultManager/UEVaultManager/core.py) file:

```python
headings = {
    'Asset_id'           : False,  # ! important: Do not Rename => this field is used as main key for each asset
    'App name'           : False,
    'App title'          : False,
    'Category'           : False,
    'Image'              : False,
    'Url'                : False,
    'UE Version'         : False,
    'Compatible Versions': False,
    'Review'             : False,
    'Developer'          : False,
    'Description'        : False,
    'Uid'                : False,
    'Creation Date'      : False,
    'Update Date'        : False,
    'Status'             : False,
    # Modified Fields when added into the file (mainly from extras data)
    'Date Added'         : True,
    'Price'              : False,  # ! important: Rename Wisely => this field is searched by text in the next lines
    'Old Price'          : False,  # ! important: always place it after the Price field in the list
    'On Sale'            : False,  # ! important: always place it after the Old Price field in the list
    'Purchased'          : False,
    # Extracted from page, can be compared with value in metadata. Coud be used to if check data grabbing if OK
    'Supported Versions' : False,
    'Page title'         : False,
    'Grab result'        : False,
    # User Fields
    'Comment'            : True,
    'Stars'              : True,
    'Asset Folder'       : True,
    'Must Buy'           : True,
    'Test result'        : True,
    'Installed Folder'   : True,
    'Alternative'        : True
}
```

### The individual json files

Each asset will also have its data saved in to different json files:

- the folder `<data folder>/metadata`: contains a json file for each asset (identified by its 'asset_id') to store its metadata (get from a call to
  the epic API)
- the folder `<data folder>/extras`: contains a json file for each asset (identified by its 'asset_id') to store its 'extras data' (grabbed from the
  marketplace page of the asset)

Note:

- filtering data (using the -fc optional arguments) occurs BEFORE saving extras data
- some "extras" json files can be missing where the corresponding "metadata" json file is present, that's because some data could have not been
  grabbed or the asset page not found during the process.
- the grabbing processing for extras data is using a text based search, so the analysed asset page could be the bad one and results could be taken for
  another asset. See the [how to fix invalid search result during the grabbing process](#how-to-fix-invalid-search-result-during-the-grabbing-process)
  section bellow

### how to fix invalid search result during the grabbing process

The grabbing processing for extras data is using a text based search (partial and case-insensitive).
By default, only the first result of this search is taken as the corresponding asset.
When the asset name, which must be converted to be used as a search keyword, is ambiguous, the search could provide several results or even a wrong
result (an asset that don't correspond).

So, in that case, the asset page that is analyzed could be the bad one and grabbed data could be taken for
the wrong asset.

To limit this error, a text comparison is done between the asset title in the metadata and the title in the asset page.
If the values are different, the asset name is added to the file pointed by the "bad_data_assets_filename_log" value of the config file and its "
error" field will contain a value different from 0. Each value correspond to a specific error code (
see [error code](#possible-values-in-the-error-field) bellow)

To fix that, the search of the correct url for the asset must be done and validated manually.

Once validated, the correct URL could be added into the result file, inside the Url field.
As this field is marked as "protected", it won't be overwritten on the next data update and will be used as a source url for the page to be grabbed
instead of making a new search for the asset page. (THIS IS STILL TO BE DONE / TODO)

**Please Note that the user is responsable for respecting the attended format of the result file when modifying its content.
Breaking its structure will probably result in losing the data the user has modified in the file when the application will be executed next time.**

Making a backup before any manual modification is certainly a good idea.
Using a tool (e.g. a linter) to check if the structure of the file (json or CSV) is still correct before running the application again is also a very
good idea.

### possible values in the error Field

The "Grab result" field of each asset contains a value that indicate how the process has run.
These code are defined by the following enum at the beginning of
the [api/egs.py](https://github.com/LaurentOngaro/UEVaultManager/blob/UEVaultManager/UEVaultManager/api/egs.py) file:

```python
class GrabResult(Enum):
    NO_ERROR = 0
    INCONSISTANT_DATA = 1
    PAGE_NOT_FOUND = 2
    CONTENT_NOT_FOUND = 3
```

## Known bugs and limitations
