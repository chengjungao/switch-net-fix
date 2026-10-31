@echo off
setlocal
title Switch Net Fix
pushd "%~dp0.." 2>nul

rem Locate a usable Python 3.
rem NOTE: this file is intentionally ASCII-only and CRLF-terminated.
rem       cmd.exe parses .bat with the console codepage (e.g. 936/GBK);
rem       UTF-8 Chinese text plus a mid-file chcp will desync the parser
rem       and turn fragments of lines into bogus commands.
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY ( where python >nul 2>nul && set "PY=python" )

if not defined PY (
  echo.
  echo [ERROR] Python 3 not found.
  echo         Install Python 3.8+ from https://www.python.org/downloads/
  echo         and enable "Add python.exe to PATH" during setup.
  echo.
  pause
  popd
  exit /b 1
)

%PY% -m switch_net_fix %*
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" echo [EXIT] code %RC%
echo Service stopped. Press any key to close.
pause >nul

popd
endlocal
