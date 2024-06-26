Usage
-----
.. _usage:

.. code:: console

  usage: UEVaultManager [-h] [-H] [-d] [-y] [-V] [-c <file>] [-J] [-A <seconds>] <command> ...

    exemple:

      UEVaultManager list --csv -fc "plugin" -o "D:\testing\list.csv"

      Will list all the assets of the marketplace that have "plugin" it their category field (on the marketplace) and save the
      result using a csv format into the "D:\testing\list.csv" file

  optional arguments:
    -h, --help                  Show this help message and exit
    -H, --full-help             Show full help (including individual command help)
    -d, --debug                 Set loglevel to debug
    -y, --yes                   Default to yes for all prompts
    -V, --version               Print version and exit
    -c, --config-file <file>    Overwrite the default configuration file name to use
    -J, --pretty-json           Pretty-print JSON. Improve readability
    -A, --api-timeout <seconds> Connection and read timeout API HTTP request (default: 7 seconds for each)
    -g, --gui                   Display the help in a windows instead of using the console

  Commands:
      <command>
       auth             Authenticate with the Epic Games Store
       cleanup          Remove old temporary, metadata, and manifest files
       info             Prints info about specified Asset or manifest
       list             List the assets you OWNED (and only them). The process could take some time.
       list-files       List files in manifest
       status           Show UEVaultManager status information. Will update the assets list and could take some time.
       edit             Display a GUI to Edit the file that contains a list of assets. Mainly use in conjunction with the list command that could
                          produce a list of assets in a file.
       scrap            Will use the EPIC API to retreive the data of ALL THE AVAILABLE assets in the EPIC marketplace (including the ones you owned)
                          and store them in an sqlite database file. The process could take some time.
       install          Download and install or not an asset by name or manifest URI in a project Folder.

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
    usage: UEVaultManager cleanup [-h] [-cs] [-cc] [-g]

    optional arguments:
      -h,  --help                  Show this help message and exit
      -cs, --delete-scraping-data  Also delete scraping data files. They are kept by default
      -cc, --delete-cache-data     Also delete image asset previews. They are usefull and should be kept. They are kept by default
      -g,  --gui                   Display the output in a windows instead of using the console


  Command: info
    usage: UEVaultManager info [-h] [--offline] [--json] [-a] [-g] <Asset Name/Manifest URI>

    positional arguments:
      <Asset Name/Manifest URI> Asset Name or manifest path/URI

    optional arguments:
      -h, --help              Show this help message and exit
      --offline               Only print info available offline. It will use files saved previously, do not log in
      --json                  Output information in JSON format
      -a, --all               Display all the information even if non-relevant for an asset
      -g, --gui               Display the output in a windows instead of using the console

  Command: list
    usage: UEVaultManager list [-h] [--csv] [--tsv] [--json] [-f] [--offline]
                          [-fc <text_to_search>] [-o <file_name_with_path>]
                          [-g]

    optional arguments:
      -h,  --help             Show this help message and exit
      --csv                   List assets in CSV format
      --tsv                   List assets in TSV format
      --json                  List assets in JSON format
      -f,  --force-refresh    Force a refresh of all asset metadata. It could take some time ! If not forced, the cached data will be used
      --offline               Only print info available offline. It will use files saved previously, do not log in
      -fc, --filter-category  Filter assets by category. Search against the asset category in the marketplace. Search is case-insensitive
                                and can be partial
      -o,  --output <file>    The file name (with path) where the list should be written to
      -g,  --gui              Display additional informations using gui elements like dialog boxes or progress window


  Command: list-files
    usage: UEVaultManager list-files [-h] [--manifest <url>] [--csv] [--tsv] [--json]
                          [--hashlist] [-g] [<Asset Name>]

    positional arguments:
      <Asset Name>          Name of the asset

    optional arguments:
      -h, --help            Show this help message and exit
      --manifest <url>      Manifest URL or path to use instead of the CDN one
      --csv                 Output in CSV format
      --tsv                 Output in TSV format
      --json                Output in JSON format
      --hashlist            Output file hash list in hashcheck/sha1sum -c compatible format
      -g, --gui             Display the output in a windows instead of using the console


  Command: status
    usage: UEVaultManager status [-h] [--offline] [--json] [-g]

    optional arguments:
      -h, --help            Show this help message and exit
      --offline             Only print offline status information, do not login
      --json                Show status in JSON format
      -g, --gui             Display the output in a windows instead of using the console


  Command: edit
    usage: UEVaultManager edit [-h] [--input] [--database]

    optional arguments:
      -h,  --help            Show this help message and exit
      -i,  --input <file>    The file name (with path) where the list should be read from (it exludes the --database option)
      --offline              Only edit info available offline. It will use files saved previously, do not log in
      -db, --database <file> The sqlite file name (with path) where the list should be read from (it exludes the --input option)

  Command: scrap
    usage: UEVaultManager scrap [-h] [-f] [--offline] [-g]

    optional arguments:
      -h, --help            Show this help message and exit
      -f, --force-refresh   Force a refresh of all asset metadata. It could take some time ! If not forced, the cached data in json files will be used
      --offline             Use previous saved data files (json) instead of scapping and new data, do not log in
      -fc, --filter-category  Filter assets by category. Search against the asset category in the marketplace. Search is case-insensitive
                                and can be partial
      -g, --gui             Display the output in a windows instead of using the console

  Command: install
    usage: UEVaultManager install [-h] [...see arguments bellow...] [<Asset Name>]

    positional arguments:
      <Asset Name>                   Name of the asset

    optional arguments:
      -h,  --help                    Show this help message and exit
      -dp, --download-path <path>    Path where the Asset will be downloaded. If empty, the Epic launcher Vault cache will be used.
      -f,  --force-refresh           Force a refresh of all asset's data. It could take some time ! If not forced, the cached data will be used
      -vc, --vault-cache             Use the vault cache folder to store the downloaded asset. It uses Epic Game Launcher setting to get this value. In that case, the download_path option will be ignored
      -c,  --clean-dowloaded-data    Delete the folder with dowloaded data. Keep the installed version if it has been installed.
      --max-shared-memory <Mib>      Maximum amount of shared memory to use (in MiB), default: 1 GiB
      --max-workers <workers>        Maximum amount of download workers, default: min(2 * CPUs, 16)
      --manifest <url>               Manifest URL or path to use instead of the CDN one (e.g. for downgrading)
      --base-url <url>               Base URL to download from (e.g. to test or switch to a different CDNs)
      --download-only, --no-install  Do not install the Asset after download
      -r,  --reuse-last-install      If the asset has been previouly installed, the installation folder will be reused. In that case, the install-path option will be ignored
      --enable-reordering            Enable reordering optimization to reduce RAM requirements during download (may have adverse results for some titles
      --timeout                      Connection and read timeout for downloader (default: 7 seconds for each)
      --preferred-cdn <cdn>          Set the hostname of the preferred CDN to use when available
