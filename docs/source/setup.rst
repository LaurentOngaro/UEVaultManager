How to run/install
------------------
.. _setup:

Requirements
~~~~~~~~~~~~

-  Linux, Windows (8.1+), or macOS (12.0+)

   -  32-bit operating systems are not supported

-  PyPI packages:

   -  ``requests``
   -  (optional) ``setuptools`` and ``wheel`` for setup/building
   -  (optional but recommended) ``pywebview`` for webview-based login

Prerequisites
~~~~~~~~~~~~~

-  Be sure that pip is installed by running

   -  for Linux or macOS (12.0+): ``sudo apt install python3-pip`` or
      ``python -m ensurepip`` or ``python3 -m ensurepip`` (depending on
      you os version)
   -  for Windows: ``python -m ensurepip``

-  To prevent problems with permissions during installation, please
   upgrade your ``pip`` by running
   ``python -m pip install -U pip --user``.
-  Install python3.9, setuptools, wheel, and requests

..

   **Tip:** You may need to replace ``python`` in the above command with
   ``python3`` on Linux/macOS.

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
   python3 -m pip install bs4
   cd UEVaultManager
   pip install .

Ubuntu 20.04 example
^^^^^^^^^^^^^^^^^^^^

Ubuntu 20.04’s standard repositories include everything needed to
install UEVaultManager:

.. code:: console

   sudo apt install python3 python3-requests python3-setuptools-git
   python3 -m pip install bs4
   git clone https://github.com/LaurentOngaro/UEVaultManager.git
   cd UEVaultManager
   pip install .

If the ``UEVaultManager`` executable is not available after
installation, you may need to configure your ``PATH`` correctly. You can
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

   **Tip:** You may need to replace ``python`` in the above command with
   ``python3`` on Linux/macOS.

Windows Binaries from repos
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**NOT DONE FOR NOW / TODO**

Download the ``uevaultmanager`` or ``uevaultmanager.exe`` binary from
`the latest
release <https://github.com/LaurentOngaro/UEVaultManager/releases/latest>`__
and move it to somewhere in your ``$PATH``/``%PATH%``. Don’t forget to
``chmod +x`` it on Linux/macOS.

The Windows .exe and Linux/macOS executable were created with
PyInstaller and will run standalone even without python being installed.
Note that on Linux glibc >= 2.25 is required, so older distributions
such as Ubuntu 16.04 or Debian stretch will not work.
