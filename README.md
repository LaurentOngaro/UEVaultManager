Welcome to UEVaultManager
==========================================
![Logo](https://laurentongaro.github.io/UEVaultManager/statics/UEVM_200x200.png)

| pypi                                                                                                                 | py_versions                                                                                                          | github                                                                                                                         | docs                                                                                                                               |
|----------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| [![Current PyPi Version](https://img.shields.io/pypi/v/uevaultmanager)](https://pypi.python.org/pypi/uevaultmanager) | [![py_versions](https://img.shields.io/pypi/pyversions/uevaultmanager)](https://pypi.python.org/pypi/uevaultmanager) | [![github](https://img.shields.io/github/v/tag/LaurentOngaro/uevaultmanager)](https://github.com/LaurentOngaro/UEVaultManager) | [![docs](https://img.shields.io/readthedocs/uevaultmanager/latest)](https://uevaultmanager.readthedocs.io/en/latest/?badge=latest) |

**UEVaultManager** is an open-source assets manager that can list assets and
their data from the Epic Games Marketplace. It is developed in Python, so
it can run on any platform that support this language.

Its main purpose is to list the assets (with or without user login),
filter (optional) and save the list into a file that can be reused later
as a data source (in an Excel sheet for instance).

| Hot news                                                         |                                                                                                                                                                                                                                                                            |
|------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| The 1.12.4 version is out: important bug fix with data scrapping | The marketplace recently uses a new captcha system that can prevent data scrapping to work. A new scapping method has been implemented is this version to fix that.                                                                                                        | 
| The 1.10.0 version is out: download and install assets           | Download and install assets in your project or your engine folder. Uses of the VaultCache folder when needed.                                                                                                                                                              | 
| The 1.8.0  version is out: EPIC marketplace API integration      | Scrap the data of ALL the asset in the marketplace and save the in a sqlite3 database.                                                                                                                                                                                     | 
| The 1.6.0  version is out: Now we have a GUI !                   | [![preview](https://i.imgur.com/DhVArs4.png)](https://uevaultmanager.readthedocs.io/en/latest/tkgui.html) <br/>- Edit the data in the GUI and save it back to the file.<br/>- Use colors to visualize your asset status.<br/>- Use filters and search to find them easily. | 

**This project is still under active development**                                                                    

To go further, dive into [the documentation](https://uevaultmanager.readthedocs.io/en/latest/index.html) or just go
for [a quickstart](https://uevaultmanager.readthedocs.io/en/latest/quickstart.html)

Contents:

* [Hot new feature !](https://uevaultmanager.readthedocs.io/en/latest/tkgui.html)
* [UEVaultManager](https://uevaultmanager.readthedocs.io/en/latest/intro.html)
  * [A free and open-source Epic Games Assets Manager for Unreal Engine](https://uevaultmanager.readthedocs.io/en/latest/intro.html#a-free-and-open-source-epic-games-assets-manager-for-unreal-engine)
  * [Known bugs and limitations](https://uevaultmanager.readthedocs.io/en/latest/intro.html#known-bugs-and-limitations)
* [Quickstart](https://uevaultmanager.readthedocs.io/en/latest/quickstart.html)
  * [Installation](https://uevaultmanager.readthedocs.io/en/latest/quickstart.html#installation)
  * [log in](https://uevaultmanager.readthedocs.io/en/latest/quickstart.html#log-in)
  * [Listing your asset](https://uevaultmanager.readthedocs.io/en/latest/quickstart.html#listing-your-asset)
  * [Saving the list into a CSV file](https://uevaultmanager.readthedocs.io/en/latest/quickstart.html#saving-the-list-into-a-csv-file)
* [How to run/install](https://uevaultmanager.readthedocs.io/en/latest/setup.html)
  * [Requirements](https://uevaultmanager.readthedocs.io/en/latest/setup.html#requirements)
  * [Prerequisites](https://uevaultmanager.readthedocs.io/en/latest/setup.html#prerequisites)
  * [Directly from the repo](https://uevaultmanager.readthedocs.io/en/latest/setup.html#directly-from-the-repo)
  * [Direct installation (any)](https://uevaultmanager.readthedocs.io/en/latest/setup.html#direct-installation-any)
* [Usage](https://uevaultmanager.readthedocs.io/en/latest/usage.html)
* [Configuration](https://uevaultmanager.readthedocs.io/en/latest/configuration.html)
  * [Config folder](https://uevaultmanager.readthedocs.io/en/latest/configuration.html#config-folder)
  * [Config file](https://uevaultmanager.readthedocs.io/en/latest/configuration.html#config-file)

[More info](https://uevaultmanager.readthedocs.io/en/latest/intro.html "UEVaultManager")
