@echo off

:: PATH aus Registry neu laden (damit frisch installiertes FFmpeg gefunden wird)
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USR_PATH=%%B"
if defined SYS_PATH set "PATH=%SYS_PATH%;%PATH%"
if defined USR_PATH set "PATH=%USR_PATH%;%PATH%"

:: Haeufige FFmpeg-Installationsorte manuell hinzufuegen (Fallback)
if exist "C:\ffmpeg\bin\ffmpeg.exe"                   set "PATH=C:\ffmpeg\bin;%PATH%"
if exist "C:\Program Files\ffmpeg\bin\ffmpeg.exe"      set "PATH=C:\Program Files\ffmpeg\bin;%PATH%"
if exist "C:\ProgramData\chocolatey\bin\ffmpeg.exe"    set "PATH=C:\ProgramData\chocolatey\bin;%PATH%"

:: FFmpeg nochmal pruefen
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo FEHLER: FFmpeg nicht gefunden.
    echo Bitte install.bat als Administrator ausfuehren.
    echo Danach dieses Fenster schliessen und start_gui.bat neu starten.
    pause
    exit /b 1
)

python "%~dp0separator_gui.py"
if errorlevel 1 (
    echo.
    echo Fehler beim Starten. Bitte zuerst install.bat ausfuehren.
    pause
)
