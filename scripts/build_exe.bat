@echo off
set exe_name=UEvm.exe
set python_script=..\UEVaultManager\cli.py
set tools_folder=H:\Sync\Scripts\Windows\04_tools
rem set level=DEBUG
set level=INFO
set relaunched=0
set script_path=%~dp0

echo Start the CLI version of UEVaultManager...
pushd %~dp0

:check_pyinstaller
where pyinstaller > nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller is not installed. Installing...
    pip install pyinstaller
)

:install_modules

pip install -r ..\requirements.txt

:build
echo Building the executable file %exe_name%...

pyinstaller --name %exe_name% ^
--noconsole ^
--onefile ^
--log-level=%level% ^
--workpath "..\build" ^
--distpath "..\binaries" ^
--add-data "..\UEVaultManager\assets;assets" ^
%python_script%

if %errorlevel% neq 0 (
    if %relaunched% neq 0 (
      echo PyInstaller execution can not be fixed. Please check the console log and try to fix it manually
      goto end
    )
    echo An issue occured when running PyInstaller. Try to fix by installing some modules...
    pip install --ignore-installed six
    pip install --ignore-installed python-dateutil
    set relaunched=1
    goto build
)

echo Build completed. Check the dist folder for the executable.

:copy
copy ..\binaries\%exe_name% %tools_folder%\%exe_name% /Y
if %errorlevel% == 0 (
  echo The executable file has been copied to %tools_folder%
)
:end
popd
echo Done!
