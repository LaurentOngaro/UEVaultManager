# TO DO in this folder or App or Package

## Bugs to confirm:

- the url column contains nan

## Bugs to fix:

- in UEVM: the obsolete check is invalid. must check for the version ABOVE the minimal one, not only for it
- the "rebuild file content" button launch the update but without the csv file output parameter
- update pagination when reload or load a file
- the reload file content button is HS
- enlarge the label with the file name in the main window

## To Do:

- add features and buttons to refresh csv file by calling UEVaultManager cli (WIP)
  - integrate the code into the UEVaultManager code base (WIP)
  - when the refresh of the list is started, display progress windows. See 13_tk_progressBar_for_long_task
  - if a category is selected in the main window, only refresh this category (using the -fc option)
- add more info about the current row (at least comment, review...) in the preview frame
- edit users fields (comment, alternative...) in the main windows (in the preview frame ?)
- save and load for tcsv files
- save and load for json files
- update the PyPi package
- document the new features
- update the PyPi package
