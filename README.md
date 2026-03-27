# AudioSeparator GUI (Windows)

Ein einfaches, aber extrem mächtiges Windows-Desktop-Tool, um Vocals (Stimmen) und Hintergrundmusik aus Audio- und Videodateien zu trennen. 

Anstatt sich mit komplexen Kommandozeilen-Befehlen und Python-Abhängigkeiten herumzuschlagen, bietet dieses Tool eine 1-Klick-Installation und eine aufgeräumte Benutzeroberfläche. Unter der Haube arbeiten State-of-the-Art KI-Modelle (BS-RoFormer & Mel-RoFormer), um Studio-Qualität zu liefern.



## Features

* **Zero-Setup für Windows:** Keine manuellen Pfade oder Terminal-Hacks nötig. Die Batch-Dateien installieren Python-Abhängigkeiten und sogar FFmpeg vollautomatisch.
* **State-of-the-Art KI:** Nutzt die weltbesten Open-Source-Modelle für Audio-Separation (BS-RoFormer mit ~13 dB SDR).
* **Ensemble-Modus:** Kombiniert mehrere Modelle (BS-RoFormer + Mel-RoFormer Big) und mittelt die Ergebnisse für absolute Maximalqualität.
* **Lossless Output:** Exportiert die getrennten Spuren immer als unkomprimierte 32-bit Float WAV-Dateien für verlustfreie Weiterverarbeitung.
* **Auto-Denoise:** Integrierte Noise-Reduction, um minimales KI-Rauschen (Artefakte) aus der isolierten Stimm-Spur zu filtern.
* **CPU & GPU Support:** Spezifische Installations-Skripte für Rechner mit und ohne NVIDIA Grafikkarten.

---

## Installation & Start

Du benötigst lediglich [Python](https://www.python.org/downloads/) auf deinem System. Alles andere erledigt das Tool.

### 1. Installieren
Lade das Projekt herunter oder klone das Repository. Führe per Doppelklick **eine** der beiden Installationsdateien aus:

* **Hast du eine NVIDIA Grafikkarte?**
  Nutze `install_gpu.bat` für maximale Geschwindigkeit über CUDA.
* **Hast du keine NVIDIA Karte (oder bist unsicher)?**
  Nutze `install.bat` (Berechnung läuft dann über den Prozessor. *Hinweis: Dauert länger!*)

*Das Skript prüft automatisch, ob FFmpeg installiert ist und lädt es bei Bedarf über `winget` herunter.*

### 2. Starten
Klicke doppelt auf:
`start_gui.bat`

*Hinweis: Beim allerersten Trenn-Vorgang lädt das Tool automatisch die benötigten KI-Modelle (ca. 500 MB) im Hintergrund herunter. Das kann einen Moment dauern.*

---

##  Welche Modelle stecken drin?

Das Tool nutzt die fantastische [audio-separator](https://github.com/nomadkaraoke/python-audio-separator) Bibliothek als Engine und bietet dir in der GUI ein Dropdown-Menü mit verschiedenen Qualitätsstufen:

1. **Ensemble (★★★★★+)**: Verbindet BS-RoFormer und Mel-RoFormer Big. Maximale Qualität, doppelte Rechenzeit.
2. **BS-RoFormer (★★★★★)**: Aktueller Spitzenreiter für Vocals.
3. **Mel-RoFormer Big (★★★★½)**: Exzellentes, sehr großes Alternativ-Modell.
4. **MDX-Net Inst HQ3 (★★★★)**: Der Klassiker, sehr robust bei lauter Instrumentierung.
5. **Demucs (★★★)**: Fallback-Modell, falls andere Modelle auf deinem System streiken.

## Fehlerbehebung (Troubleshooting)

**Fehler: "FFmpeg nicht gefunden"**
Die `install.bat` versucht FFmpeg via Windows Package Manager (`winget`) zu installieren. Sollte das fehlschlagen, installiere es manuell:
1. Gehe auf https://www.gyan.dev/ffmpeg/builds/
2. Lade die `ffmpeg-release-essentials.zip` herunter.
3. Entpacke den Inhalt nach `C:\ffmpeg`.
4. Füge `C:\ffmpeg\bin` zu deinen Windows PATH-Umgebungsvariablen hinzu.
5. Führe die `install.bat` erneut aus.

---
*Gebaut mit Python, Tkinter und viel Open-Source-Liebe.*
