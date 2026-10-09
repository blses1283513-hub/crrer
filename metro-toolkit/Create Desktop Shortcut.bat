@echo off
rem Double-click to put a "Metro Toolkit" icon on your Desktop (opens the dashboard, no terminal or cd needed).
rem   Create Desktop Shortcut.bat              -> Desktop shortcut
rem   Create Desktop Shortcut.bat startmenu    -> Desktop shortcut and a Start menu entry
rem Paths are worked out from this file's own location; nothing personal is stored in the repo.
setlocal
set "HERE=%~dp0"
if not exist "%HERE%Metro Toolkit.bat" (
    echo Could not find "Metro Toolkit.bat" next to this file ^(%HERE%^).
    pause
    exit /b 1
)
set "MT_START=0"
if /i "%~1"=="startmenu" set "MT_START=1"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$here = $env:HERE; $sh = New-Object -ComObject WScript.Shell;" ^
  "$dirs = @([Environment]::GetFolderPath('Desktop'));" ^
  "if ($env:MT_START -eq '1') { $dirs += [Environment]::GetFolderPath('Programs') };" ^
  "foreach ($d in $dirs) {" ^
  "  $lnk = $sh.CreateShortcut((Join-Path $d 'Metro Toolkit.lnk'));" ^
  "  $lnk.TargetPath = (Join-Path $here 'Metro Toolkit.bat');" ^
  "  $lnk.WorkingDirectory = $here.TrimEnd('\');" ^
  "  $lnk.IconLocation = (Join-Path $here 'assets\metro-toolkit.ico') + ',0';" ^
  "  $lnk.Description = 'metro-toolkit dashboard';" ^
  "  $lnk.Save(); Write-Host ('Created ' + $lnk.FullName) }"
if errorlevel 1 (
    echo.
    echo Could not create the shortcut ^(see above^). You can also right-click "Metro Toolkit.bat",
    echo choose Send to ^> Desktop ^(create shortcut^), then right-click the shortcut ^> Properties ^>
    echo Change Icon... and pick assets\metro-toolkit.ico.
    pause
    exit /b 1
)
echo.
echo Done. Look for "Metro Toolkit" on your Desktop. If the icon looks blank or old, restart Explorer
echo ^(Task Manager ^> Windows Explorer ^> Restart^) or sign out and in again to refresh the icon cache.
pause
endlocal
