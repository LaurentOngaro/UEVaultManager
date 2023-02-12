# UEVaultManager

## A free and open-source Epic Games Launcher alternative

UEVaultManager is an open-source assets manager that can list assets from the Epic Games Marketplace.
Its main purpose is to list the assets (with or without user login) and save the list into a file that can be reused later as a data source (for
instance
in an Excel sheet).
In a future versions, this application will also offer a GUI, and will be able to read directly the result file, display and edit the assets list.

Please read the [config file](#config-file) and [cli usage](#usage) sections before creating an issue to avoid invalid reports.

or [create an issue on GitHub](https://github.com/LaurentOngaro/UEVaultManager/issues/new/choose), so we can fix it!

**Note:** UEVaultManager is currently a CLI (command-line interface) application without a graphical user interface,
it has to be run from a terminal (e.g. PowerShell)

**Features:**

- Authenticating with Epic's service
- Listing and managing your assets

**Planned:**

- Simple GUI for managing assets (WIP)
- Install and download assets into Unreal VaultCache or projects folders

**Special thanks:**

This code is mainly a lighter version of the [Legendary](https://github.com/derrod/legendary) tool code base, with some addition regarding the
management of the unreal engine marketplace assets.
Thanks to the Legendary team for the fantastic work on their tool.

## Requirements

- Linux, Windows (8.1+), or macOS (12.0+)
  + 32-bit operating systems are not supported
- python 3.9+ (64-bit)
  + (Windows) `pythonnet` is not yet compatible with 3.10+, use 3.9 if you plan to install `pywebview`
- PyPI packages:
  + `requests`
  + (optional) `pywebview` for webview-based login
  + (optional) `setuptools` and `wheel` for setup/building

## How to run/install

**NOT DONE FOR NOW / TODO**

Download the `uevaultmanager` or `uevaultmanager.exe` binary
from [the latest release](https://github.com/LaurentOngaro/UEVaultManager/releases/latest)
and move it to somewhere in your `$PATH`/`%PATH%`. Don't forget to `chmod +x` it on Linux/macOS.

The Windows .exe and Linux/macOS executable were created with PyInstaller and will run standalone even without python being installed.
Note that on Linux glibc >= 2.25 is required, so older distributions such as Ubuntu 16.04 or Debian stretch will not work.

### Python Package (any)

#### Prerequisites

**NOT DONE FOR NOW / TODO**

To prevent problems with permissions during installation, please upgrade your `pip` by running `python -m pip install -U pip --user`.

> **Tip:** You may need to replace `python` in the above command with `python3` on Linux/macOS.

```bash
pip install UEVaultManager
```

#### Manually from the repo

- Install python3.9, setuptools, wheel, and requests
- Clone the git repository and cd into it
- Run `pip install .`

#### Ubuntu 20.04 example

NOT TESTED BUT SHOULD RUN FINE

Ubuntu 20.04's standard repositories include everything needed to install UEVaultManager:

````bash
sudo apt install python3 python3-requests python3-setuptools-git
git clone https://github.com/LaurentOngaro/UEVaultManager.git
cd UEVaultManager
pip install .
````

If the `UEVaultManager` executable is not available after installation, you may need to configure your `PATH` correctly. You can do this by running
the command:

```bash
echo 'export PATH=$PATH:~/.local/bin' >> ~/.profile && source ~/.profile
```

#### Windows example

1. First install the Python language (3.9 minimal version required) as explained on the [official python website](https://www.python.org/downloads/windows/) 
2. create a folder for storing the source files 
3. open a command prompt or a terminal from this folder.
4. run the following commands:

```
git clone https://github.com/LaurentOngaro/UEVaultManager.git
cd UEVaultManager
pip install .
```

If the `UEVaultManager` executable is not available after installation, you may need to configure your `PATH` correctly. 

### Directly from the repo (for dev/testing)

- Install python 3.9 and requests (optionally in a venv)
- cd into the repository
- Run `pip install -e .`

This installs `UEVaultManager` in "editable" mode - any changes to the source code will take effect next time the `UEVaultManager` executable runs.

## Quickstart

**Tip:** When using PowerShell with the standalone executable, you may need to replace `UEVaultManager` with `.\UEVaultManager` in the commands below.

To log in:

````
UEVaultManager auth
````

When using the prebuilt Windows executables of version 0.20.14 or higher this should open a new window with the Epic Login.

Otherwise, authentication is a little finicky since we have to go through the Epic website and manually copy a code.
The login page should open in your browser and after logging in you should be presented with a JSON response that contains a code ("
authorizationCode"), just copy the code into the terminal and hit enter.

Alternatively you can use the `--import` flag to import the authentication from the Epic Games Launcher

Note that this will log you out of the Epic Launcher.

Listing your asset

````
UEVaultManager list
````

This will fetch a list of asset available on your account, the first time may take a while depending on how many asset you have.

## Usage

````
usage: UEVaultManager [-h] [-H] [-v] [-y] [-V] [-J] [-A <seconds>] <command> ...

exemple: 
  
  UEVaultManager list --csv -c "plugin" --output "D:\testing\list.csv"
  
  Will list all the assets of the marketplace that have "plugin" it their category field (on the marketplace) and save the result using a csv format 
  into the ""D:\testing\list.csv" file 

optional arguments:
  -h, --help            show this help message and exit
  -H, --full-help       Show full help (including individual command help)
  -v, --debug           Set loglevel to debug
  -y, --yes             Default to yes for all prompts
  -V, --version         Print version and exit
  -J, --pretty-json     Pretty-print JSON
  -A <seconds>, --api-timeout <seconds>
                        API HTTP request timeout (default: 10 seconds)

Commands:
  <command>
    auth                Authenticate with the Epic Games Store
    info                Prints info about specified app name or manifest
    list                List available assets
    list-files          List files in manifest
    status              Show UEVaultManager status information

Individual command help:

Command: auth
usage: UEVaultManager auth [-h] [--import] [--code <exchange code>]
                      [--sid <session id>] [--delete] [--disable-webview]

optional arguments:
  -h, --help            show this help message and exit
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


Command: info
usage: UEVaultManager info [-h] [--offline] [--json]
                      <App Name/Manifest URI>

positional arguments:
  <App Name/Manifest URI>
                        App name or manifest path/URI

optional arguments:
  -h, --help            show this help message and exit
  --offline             Only print info available offline
  --json                Output information in JSON format

Command: list
usage: UEVaultManager list [-h] [-T] [--csv]
                      [--tsv] [--json] [--force-refresh] [--output]

optional arguments:
  -h, --help            show this help message and exit
  --csv                 List asset in CSV format
  --tsv                 List asset in TSV format
  --json                List asset in JSON format
  --force-refresh       Force a refresh of all asset metadata
  -c, --category        Filter assets by category. Search against the asset category in the marketplace. Search is case insensitive and can be partial
  -o, --output          The file name (with path) where the list should be written to



Command: list-files
usage: UEVaultManager list-files [-h] [--force-download]
                            [--manifest <uri>] [--csv] [--tsv] [--json]
                            [--hashlist] [--install-tag <tag>]
                            [<App Name>]

positional arguments:
  <App Name>            Name of the app (optional)

optional arguments:
  -h, --help            show this help message and exit
  --force-download      Always download instead of using on-disk manifest
  --manifest <uri>      Manifest URL or path to use instead of the CDN one
  --csv                 Output in CSV format
  --tsv                 Output in TSV format
  --json                Output in JSON format
  --hashlist            Output file hash list in hashcheck/sha1sum -c
                        compatible format
  --install-tag <tag>   Show only files with specified install tag


Command: status
usage: UEVaultManager status [-h] [--offline] [--json]

optional arguments:
  -h, --help  show this help message and exit
  --offline   Only print offline status information, do not login
  --json      Show status in JSON format

````

## Config file

UEVaultManager supports some options in `~/.config/UEVaultManager/config.ini`:

````ini
[UEVaultManager]
log_level = debug
; locale override, must be in RFC 1766 format (e.g. "en-US")
locale = en-US
; path to the "Manifests" folder in the EGL ProgramData directory
egl_programdata = C:/ProgramData/Epic/EpicGamesLauncher/Data/Manifests
; Disables the automatic update check
disable_update_check = false
; Disables the notice about an available update on exit
disable_update_notice = false
; Disable automatically-generated aliases
disable_auto_aliasing = false
; Create a backup of the output file (when using the --output option) suffixe by a timestamp
create_output_backup = false
````

## Output Format and file

### CSV file

These are the headings that will be written to the stdout or to the file pointed by the --output command line option
The script also use a (hardcoded) boolean value to know if the content of the columns must be preserved before overwriting an existing
output file
This feature goal is to avoid overwriting data that could have been manually changed by the user in the output file between successive runs of the
program.

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
    # Modified Fields when added into the file
    'Date Added'         : True,
    'Price'              : False,  # ! important: Rename Wisely => this field is searched by text in the next lines
    'Old Price'          : False,  # ! important always place it after the Price field in the list
    'On Sale'            : False,  # ! important always place it after the Old Price field in the list
    # Modified Fields when added into the file
    'Comment'            : True,
    'Stars'              : True,
    'Asset Folder'       : True,
    'Must Buy'           : True,
    'Test result'        : True,
    'Installed Folder'   : True,
    'Alternative'        : True
}
```

### Json file

TODO

## Known bugs and limitations

### invalid data

Due to API changes, the `Price` and `Review` fields of an asset can not be retrieved and will be set to a default value
Consequently, the `Old Price` and `On Sale` fields will be also be set to a default value because of the mode of calculation
