@echo off
echo ============================================================
echo  AudioSeparator - Installation (GPU/CUDA)
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python nicht gefunden.
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
echo [2/4] Installiere audio-separator (GPU)...
pip install "audio-separator[gpu]"
if errorlevel 1 (
    echo Zugriffsfehler - versuche mit --user Flag...
    pip install "audio-separator[gpu]" --user
)

echo.
echo [3/4] Installiere demucs als Fallback...
pip install demucs soundfile librosa
if errorlevel 1 (
    pip install demucs soundfile librosa --user
)

echo.
echo [4/4] Installiere Noise-Reduction...
pip install noisereduce
if errorlevel 1 (
    pip install noisereduce --user
)

echo.
echo ============================================================
echo  Fertig! Starte mit: start_gui.bat
echo  Beim ersten Start werden Modelle heruntergeladen (~500 MB)
echo ============================================================
pause
