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

echo #################
echo Building docs...
echo #################
pause
cd ../docs/
rmdir build\html /S /Q
call make.bat


echo #################
echo Building dist...
echo #################
pause
cd ../
rmdir dist /S /Q
python setup.py sdist bdist_wheel

echo #################
echo Check dist...
echo #################
twine check dist/*

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
