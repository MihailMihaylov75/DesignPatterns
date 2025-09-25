@echo off
REM Use from CMD with:  call scripts\set_pythonpath.bat
REM Adds absolute ...\src and ...\tests to PYTHONPATH for the current CMD session.

REM project root = parent of this script
pushd "%~dp0\.."
set "ROOT=%CD%"
set "SRC=%ROOT%\src"
set "TESTS=%ROOT%\tests"

REM Normalize and create if missing (no-op if exist)
if not exist "%SRC%" echo [WARN] SRC not found: "%SRC%"
if not exist "%TESTS%" echo [WARN] TESTS not found: "%TESTS%"

REM Append only if not already present (case-insensitive)
set "NEWPP=%PYTHONPATH%"
echo %NEWPP% | find /I "%SRC%" >nul || set "NEWPP=%NEWPP%;%SRC%"
echo %NEWPP% | find /I "%TESTS%" >nul || set "NEWPP=%NEWPP%;%TESTS%"

REM Trim leading ';' if PYTHONPATH was empty
if "%NEWPP:~0,1%"==";" set "NEWPP=%NEWPP:~1%"

set "PYTHONPATH=%NEWPP%"
echo PYTHONPATH=%PYTHONPATH%

popd
