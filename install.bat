@echo off
echo ============================================================
echo  AudioSeparator - Installation (CPU)
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python nicht gefunden.
    echo Bitte Python von https://python.org installieren.
    pause
    exit /b 1
)

echo [1/4] Pruefe FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo FFmpeg nicht gefunden - installiere via winget...
    winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo.
        echo HINWEIS: winget konnte FFmpeg nicht installieren.
        echo Bitte manuell installieren:
        echo   1. https://www.gyan.dev/ffmpeg/builds/ aufrufen
        echo   2. ffmpeg-release-essentials.zip herunterladen
        echo   3. Entpacken nach C:\ffmpeg
        echo   4. C:\ffmpeg\bin zu den Windows PATH-Variablen hinzufuegen
        echo   5. Dieses Skript erneut ausfuehren
        echo.
        pause
        exit /b 1
    )
    echo FFmpeg erfolgreich installiert.
) else (
    echo FFmpeg bereits installiert - OK
)

echo.
echo [2/4] Installiere audio-separator (CPU)...
pip install "audio-separator[cpu]"

echo.
echo [3/4] Installiere demucs als Fallback...
pip install demucs soundfile librosa

echo.
echo [4/4] Installiere Noise-Reduction...
pip install noisereduce

echo.
echo ============================================================
echo  Fertig! Starte mit: start_gui.bat
echo  Beim ersten Start werden Modelle heruntergeladen (~500 MB)
echo  HINWEIS: CPU-Modus - Ensemble dauert ca. 15-30 Min pro Datei
echo ============================================================
pause
