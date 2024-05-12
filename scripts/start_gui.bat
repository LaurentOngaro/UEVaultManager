@echo off
set root_drive=D:
set root_folder=%root_drive%\Projets_Perso\03d_CodePython\UEVaultManager
rem we use the venv version of python to start, as it the venv will be loaded as in development
set python_exe=.\.venv\scripts\python.exe
rem we load the main file as a MODULE (i.e. without the .py extension) , as it, the path for imports will be OK
rem see: https://stackoverflow.com/questions/72852/how-can-i-do-relative-imports-in-python#comment5699857_73149
set module_path=UEVaultManager.tkgui.main
rem set params=%*
set params=edit --database

echo Start the GUI version of UEVaultManager...
cd %root_folder%

%python_exe% -m %module_path% %params%

:end
echo Done!
