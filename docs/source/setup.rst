How to run/install
------------------
.. _setup:

Requirements
~~~~~~~~~~~~

-  Windows (8.1+), Linux, or macOS (12.0+)

   -  32-bit operating systems are not supported

-  Python 3.9 or newer
-  PyPI packages:

   -  `requests`
   -  `beautifulsoup4`, `Pillow`, `tkinter`, `pandas`, `pandastable` and their dependencies for the GUI
   -  (optional) `setuptools` and `wheel` for setup/building
   -  (optional but recommended) `pywebview` for webview-based login

  **Note:** We describe how to do things for Ubuntu 22.04. But it should be similar for other Linux distributions and macOS.

  We only make tests and installations on Windows 11, Ubuntu 22.04 (WSL) and Pop!OS 22.04. So we can't guarantee that it will work on other OS.

Prerequisites
~~~~~~~~~~~~~

-  Install python3.9
-  You can manually install all the python packages listed before, but it will be done when running the command ``pip install .`` as indicated bellow.
-  The tkinter package is not installed by default on Ubuntu and won't be installed by pip.
   So you need to install it manually with the command ``sudo apt install python3-tk``.
-  Be sure that pip is installed by running

   -  for Linux or macOS (12.0+): ``sudo apt install python3-pip`` or
      ``python -m ensurepip`` or ``python3 -m ensurepip`` (depending on
      you os version)
   -  for Windows: ``python -m ensurepip``

-  To prevent problems with permissions during installation, please
   upgrade your `pip` by running
   ``python -m pip install -U pip --user``.

..

   **Tip:** You may need to replace `python` in the above command with
   `python3` on Linux/macOS.

Directly from the repo
~~~~~~~~~~~~~~~~~~~~~~

Windows example
^^^^^^^^^^^^^^^

1. First install the Python language (3.9 minimal version required) as
   explained on the `official python
   website <https://www.python.org/downloads/windows/>`__
2. create a folder for storing the source files
3. open a command prompt or a terminal from this folder.
4. run the following commands:

.. code:: console

   git clone https://github.com/LaurentOngaro/UEVaultManager.git
   cd UEVaultManager
   pip install .

Ubuntu 22.04 example
^^^^^^^^^^^^^^^^^^^^

Ubuntu standard repositories include everything needed to
install UEVaultManager:

.. code:: console

   sudo apt install python3 python3-requests python3-setuptools-git
   sudo apt install python3-tk
   git clone https://github.com/LaurentOngaro/UEVaultManager.git
   cd UEVaultManager
   pip install .

If the `UEVaultManager` executable is not available after
installation, you may need to configure your `PATH` correctly. You can
do this by running the command:

.. code:: console

   echo 'export PATH=$PATH:~/.local/bin' >> ~/.profile && source ~/.profile

Direct installation (any)
~~~~~~~~~~~~~~~~~~~~~~~~~

Python Package on `pypi <https://pypi.org>`__ (any)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: console

   pip install UEVaultManager

..



Windows Binaries from repos (since 1.6.2)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Download the `UEvm.exe` binary from
`the latest release <https://github.com/LaurentOngaro/UEVaultManager/releases/latest>`__
and move it to somewhere in your path.
The simpliest way is to put the executable into your windows folder (aka. `C:\Windows`).
But you can also create a folder and add the folder to your path.

The Windows executable was created with `PyInstaller <https://pyinstaller.org/en/stable>`__ and will run standalone even without python being installed.

Note the executable is not signed, so you could get a warning from Windows SmartScreen when you run it.
The executable will be decompressed in your temp folder and run from there. **So the first runs will be slow**.
