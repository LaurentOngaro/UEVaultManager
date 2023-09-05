@ECHO OFF
pushd %~dp0

echo Please check that you have the following done:
echo.
echo ### Increment the version number
echo   - check the [semantic versioning rules](https://semver.org/) (- [french version](https://semver.org/lang/fr/))
echo     - Use 4th number (_._.\_.X) for minor changes that don't impact code (typo, description, readme ...)
echo   - Increment the package/realease version number in `/UEVaultManager/__init__.py` (mandatory)
echo     - change the codename if the major version changes (X._._)
echo     - increase the codename if the minor version changes (_.X._)

echo ### release a new version on GitHub
echo   - commit the changes
echo   - push the changes
echo   - create a [new release on GitHub](https://github.com/LaurentOngaro/UEVaultManager/releases/new)
echo     - create a new tag on GitHub using the new version number
echo     - set the release title as the codename in `/UEVaultManager/__init__.py`
echo     - add a description (extract from commit messages)
echo   - publish the release
echo   - check the result of the [compilation of the doc](https://readthedocs.org/projects/uevaultmanager)

:check_sphinx
where sphinx-build > nul 2>&1
if %errorlevel% neq 0 (
    echo Sphinx is not installed. Installing...
    pip install -U sphinx
)

:docs
echo #################
echo Building docs...
echo #################
pause
set relaunched=0
cd ../docs/
rmdir build\html /S /Q
call make.bat
if %errorlevel% neq 0 (
    if %relaunched% neq 0 (
      echo building DOCS execution can not be fixed. Please check the console log and try to fix it manually
      goto end
    )
    echo An issue occured when building DOCS. Try to fix by installing some modules...
    pip install --ignore-installed  requirements-parser
    set relaunched=1
    goto docs
)

:build
echo #################
echo Building dist...
echo #################
pause
set relaunched=0
cd ..
rmdir dist /S /Q
python setup.py sdist bdist_wheel
if %errorlevel% neq 0 (
    if %relaunched% neq 0 (
      echo setup.py execution can not be fixed. Please check the console log and try to fix it manually
      goto end
    )
    echo An issue occured when running setup.py. Try to fix by installing some modules...
    pip install --ignore-installed wheel
    pip install --ignore-installed sdist
    pip install --ignore-installed  requirements-parser
    set relaunched=1
    goto build
)

:dist
echo #################
echo Check dist...
echo #################
set relaunched=0
twine check dist/*
if %errorlevel% neq 0 (
    if %relaunched% neq 0 (
      echo twine execution can not be fixed. Please check the console log and try to fix it manually
      goto end
    )
    echo An issue occured when running twine. Try to fix by installing some modules...
    pip install --ignore-installed twine
    set relaunched=1
    goto dist
)

echo.
echo Please check that you have no error in the previous step before continuing
echo.
pause

echo #################
echo Uploading dist...
echo #################
twine upload dist/*

:end
popd
