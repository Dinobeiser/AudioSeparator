# AudioSeparator GUI (Windows)

Ein einfaches, aber extrem mächtiges Windows-Desktop-Tool, um Vocals (Stimmen) und Hintergrundmusik aus Audio- und Videodateien zu trennen. 

Anstatt sich mit komplexen Kommandozeilen-Befehlen und Python-Abhängigkeiten herumzuschlagen, bietet dieses Tool eine 1-Klick-Installation und eine aufgeräumte Benutzeroberfläche. Unter der Haube arbeiten State-of-the-Art KI-Modelle (BS-RoFormer und Mel-RoFormer), um Studio-Qualität zu liefern.

## Features

* **Zero-Setup für Windows:** Keine manuellen Pfade oder Terminal-Hacks nötig. [cite_start]Die Batch-Dateien installieren Python-Abhängigkeiten und sogar FFmpeg vollautomatisch. [cite: 1, 8, 15]
* **State-of-the-Art KI:** Nutzt die weltbesten Open-Source-Modelle für Audio-Separation (BS-RoFormer mit ca. 13 dB SDR).
* **Ensemble-Modus:** Kombiniert mehrere Modelle (BS-RoFormer + Mel-RoFormer Big) und mittelt die Ergebnisse für absolute Maximalqualität.
* **Lossless Output:** Exportiert die getrennten Spuren immer als unkomprimierte 32-bit Float WAV-Dateien für verlustfreie Weiterverarbeitung.
* [cite_start]**Auto-Denoise:** Integrierte Noise-Reduction, um minimales KI-Rauschen (Artefakte) aus der isolierten Stimm-Spur zu filtern. [cite: 5, 13]
* [cite_start]**CPU und GPU Support:** Spezifische Installations-Skripte für Rechner mit und ohne NVIDIA Grafikkarten. [cite: 1, 8]

---

## Installation und Start

Du benötigst lediglich Python auf deinem System. [cite_start]Alles andere erledigt das Tool. [cite: 1, 8]

### 1. Installieren
Lade das Projekt herunter oder klone das Repository. Führe per Doppelklick eine der beiden Installationsdateien aus:

* **Hast du eine NVIDIA Grafikkarte?**
  [cite_start]Nutze install_gpu.bat für maximale Geschwindigkeit über CUDA. [cite: 8]
* **Hast du keine NVIDIA Karte (oder bist unsicher)?**
  [cite_start]Nutze install.bat (Berechnung läuft dann über den Prozessor. Hinweis: Der Prozess dauert auf der CPU deutlich länger). [cite: 1, 7]

[cite_start]Das Skript prüft automatisch, ob FFmpeg installiert ist und lädt es bei Bedarf über winget herunter. [cite: 1, 8]

### 2. Starten
Klicke doppelt auf:
[cite_start]start_gui.bat [cite: 6, 14, 15]

---

## Automatischer Modell-Download

Das Tool verfügt über einen integrierten Download-Mechanismus. Beim ersten Start eines Trennungsvorgangs prüft das Programm automatisch, ob die benötigten KI-Modelle im lokalen Ordner vorhanden sind. 

Sollten Dateien fehlen, werden diese direkt vom GitHub-Repository dieses Projekts nachgeladen. Dies stellt sicher, dass das Tool auch dann funktioniert, wenn externe Modell-Hoster nicht erreichbar sind. [cite_start]Der erste Vorgang kann je nach Internetgeschwindigkeit einige Zeit in Anspruch nehmen, da mehrere hundert Megabyte an Daten geladen werden. [cite: 6, 14]

---

## Welche Modelle stecken drin?

[cite_start]Das Tool nutzt die audio-separator Bibliothek als Engine und bietet dir in der GUI ein Dropdown-Menü mit verschiedenen Qualitätsstufen: [cite: 4, 11]

1. **Ensemble**: Verbindet BS-RoFormer und Mel-RoFormer Big. Maximale Qualität bei doppelter Rechenzeit.
2. **BS-RoFormer**: Aktueller Spitzenreiter für die Extraktion von Vocals.
3. **Mel-RoFormer Big**: Exzellentes, sehr großes Alternativ-Modell.
4. **MDX-Net Inst HQ3**: Sehr robust bei lauter Instrumentierung.
5. [cite_start]**Demucs**: Fallback-Modell für allgemeine Trennungen. [cite: 4, 12]

---

## Fehlerbehebung (Troubleshooting)

**Fehler: FFmpeg nicht gefunden**
Die install.bat versucht FFmpeg via Windows Package Manager (winget) zu installieren. [cite_start]Sollte das fehlschlagen, installiere es manuell: [cite: 1, 8]
1. [cite_start]Rufe https://www.gyan.dev/ffmpeg/builds/ auf. [cite: 2, 9]
2. [cite_start]Lade die ffmpeg-release-essentials.zip herunter. [cite: 2, 9]
3. [cite_start]Entpacke den Inhalt nach C:\ffmpeg. [cite: 2, 9]
4. [cite_start]Füge C:\ffmpeg\bin zu den Windows PATH-Umgebungsvariablen hinzu. [cite: 2, 9]
5. [cite_start]Führe die install.bat erneut aus. [cite: 2, 9]

---
*Gebaut mit Python, Tkinter und Open-Source-Komponenten.*
