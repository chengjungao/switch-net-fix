@echo off
setlocal

rem ASCII-only and CRLF-terminated on purpose; see start.bat for the reason.
for %%I in ("%~dp0start.bat") do set "TARGET=%%~fI"
for %%I in ("%~dp0..") do set "ROOT=%%~fI"

if not exist "%TARGET%" (
  echo [ERROR] start.bat not found next to this script.
  pause
  exit /b 1
)

echo Target : %TARGET%
echo Writing shortcut into the Startup folder ...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $lnk=$w.CreateShortcut(([Environment]::GetFolderPath('Startup')) + '\SwitchNetFix.lnk'); $lnk.TargetPath='%TARGET%'; $lnk.WorkingDirectory='%ROOT%'; $lnk.WindowStyle=7; $lnk.Save()"

if errorlevel 1 (
  echo [ERROR] Failed to create the shortcut. Manual way:
  echo         Win+R -^> shell:startup -^> put a shortcut of start.bat there
) else (
  echo [OK] Added. It starts minimized at the next logon.
  echo      To undo: Win+R -^> shell:startup -^> delete SwitchNetFix.lnk
)

echo.
pause
