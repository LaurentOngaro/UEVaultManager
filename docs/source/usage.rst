Usage
-----
.. _usage:

.. code:: console

  usage: UEVaultManager [-h] [-H] [-d] [-y] [-V] [-c <file>] [-J] [-A <seconds>] <command> ...

    exemple:

      UEVaultManager list --csv -fc "plugin" --output "D:\testing\list.csv"

      Will list all the assets of the marketplace that have "plugin" it their category field (on the marketplace) and save the
      result using a csv format into the "D:\testing\list.csv" file

  optional arguments:
    -h, --help          Show this help message and exit
    -H, --full-help     Show full help (including individual command help)
    -d, --debug         Set loglevel to debug
    -y, --yes           Default to yes for all prompts
    -V, --version       Print version and exit
    -c, --config-file   Overwrite the default configuration file name to use
    -J, --pretty-json   Pretty-print JSON. Improve readability
    -A <seconds>, --api-timeout <seconds>   API HTTP request timeout (default: 10 seconds)
    -g,  --gui          Display the help in a windows instead of using the console

  Commands:
      <command>
       auth             Authenticate with the Epic Games Store
       cleanup          Remove old temporary, metadata, and manifest files
       info             Prints info about specified app name or manifest
       list             List the assets you OWNED. It could take some time.
       list-files       List files in manifest
       status           Show UEVaultManager status information. Will update the assets list and could take some time.
       edit             Display a GUI to Edit the file that contains a list of assets. Mainly use in conjunction with the list command that could
                          produce a list of assets in a file.


  Individual command help:

  Command: auth
    usage: UEVaultManager auth [-h] [--import] [--code <exchange code>] [--token <exchange token>]
                          [--sid <session id>] [--delete] [--disable-webview]

    optional arguments:
      -h, --help                  Show this help message and exit
      --import                    Import Epic Games Launcher authentication data (logs out of EGL)
      --code <authorization code> Use specified authorization code instead of interactive authentication
      --token <exchange token>    Use specified exchange token instead of interactive authentication
      --sid <session id>          Use specified session id instead of interactive authentication
      --delete                    Remove existing authentication (log out)
      --disable-webview           Do not use embedded browser for login


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
      <App Name/Manifest URI> App name or manifest path/URI

    optional arguments:
      -h, --help              Show this help message and exit
      --offline               Only print info available offline
      --json                  Output information in JSON format
      -f, --force-refresh     Force a refresh of all asset metadata. It could take some time ! If not forced, the cached data will be used
      -g,  --gui              Display the output in a windows instead of using the console

  Command: list
    usage: UEVaultManager list [-h] [----third-party] [--csv]
                          [--tsv] [--json] [--force-refresh] [--gui]
                          [--filter-category <text_to_search>] [--output <file_name_with_path>]

    optional arguments:
      -h,  --help             Show this help message and exit
      -T,  --third-party      Include assets that are not installable
      --csv                   List asset in CSV format
      --tsv                   List asset in TSV format
      --json                  List asset in JSON format
      -f,  --force-refresh    Force a refresh of all asset metadata. It could take some time ! If not forced, the cached data will be used
      -fc, --filter-category  Filter assets by category. Search against the asset category in the marketplace. Search is case insensitive
                                and can be partial
      -o, --output            The file name (with path) where the list should be written to
      -g,  --gui              Display additional informations using gui elements like dialog boxes or progress window


  Command: list-files
    usage: UEVaultManager list-files [-h] [--manifest <uri>] [--csv] [--tsv] [--json]
                          [--hashlist] [--force-refresh] [<App Name>]

    positional arguments:
      <App Name>            Name of the app (optional)

    optional arguments:
      -h, --help            Show this help message and exit
      --manifest <uri>      Manifest URL or path to use instead of the CDN one
      --csv                 Output in CSV format
      --tsv                 Output in TSV format
      --json                Output in JSON format
      --hashlist            Output file hash list in hashcheck/sha1sum -c compatible format
      -f, --force-refresh   Force a refresh of all asset metadata. It could take some time ! If not forced, the cached data will be used
      -g,  --gui            Display the output in a windows instead of using the console


  Command: status
    usage: UEVaultManager status [-h] [--offline] [--json]

    optional arguments:
      -h, --help            Show this help message and exit
      --offline             Only print offline status information, do not login
      --json                Show status in JSON format
      -f, --force-refresh   Force a refresh of all asset metadata. It could take some time ! If not forced, the cached data will be used
      -g,  --gui            Display the output in a windows instead of using the console


  Command: edit
    usage: UEVaultManager edit [-h] [--input]

    optional arguments:
      -h, --help            Show this help message and exit
      -i, --input           The file name (with path) where the list should be read from

  Command: scrap
    usage: UEVaultManager scrap [-h]

    optional arguments:
      -h, --help            Show this help message and exit
      -f, --force-refresh   Force a refresh of all asset metadata. It could take some time ! If not forced, the cached data will be used
      -g,  --gui            Display the output in a windows instead of using the console
