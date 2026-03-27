"""
AudioSeparator - Vocals / Hintergrund Trenner
Nutzt BS-RoFormer (State-of-the-Art) via audio-separator,
Ensemble-Modus für maximale Qualität, Fallback auf demucs.
"""

import math
import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

SUPPORTED = (
    ("Audio/Video Dateien", "*.wav *.mp3 *.mp4 *.mkv *.flac *.ogg *.m4a *.aac *.wma"),
    ("Alle Dateien", "*.*"),
)

# Modelle sortiert nach Qualität (bestes zuerst)
MODELS = [
    {
        "label":   "Ensemble  \u2605\u2605\u2605\u2605\u2605+  (BS-RoFormer + Mel-RoFormer Big, max. Qualitat)",
        "engine":  "ensemble",
        "models":  [
            "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
            "melband_roformer_big_beta5e.ckpt",
        ],
    },
    {
        "label":   "BS-RoFormer  \u2605\u2605\u2605\u2605\u2605  (State-of-the-Art, ~13 dB SDR)",
        "engine":  "audio-separator",
        "model":   "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
    },
    {
        "label":   "Mel-RoFormer Big Beta5e  \u2605\u2605\u2605\u2605\u00bd  (sehr gut, grosses Modell)",
        "engine":  "audio-separator",
        "model":   "melband_roformer_big_beta5e.ckpt",
    },
    {
        "label":   "Mel-RoFormer ep3005  \u2605\u2605\u2605\u2605  (~11.4 dB SDR)",
        "engine":  "audio-separator",
        "model":   "model_mel_band_roformer_ep_3005_sdr_11.4360.ckpt",
    },
    {
        "label":   "MDX-Net Inst HQ3  \u2605\u2605\u2605\u2605  (gut fur Musik)",
        "engine":  "audio-separator",
        "model":   "UVR-MDX-NET-Inst_HQ_3.onnx",
    },
    {
        "label":   "htdemucs_ft  \u2605\u2605\u2605  (demucs, Fallback)",
        "engine":  "demucs",
        "model":   "htdemucs_ft",
    },
    {
        "label":   "htdemucs  \u2605\u2605\u2605  (demucs, schnell)",
        "engine":  "demucs",
        "model":   "htdemucs",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Hilfsfunktion: 32-bit float WAV speichern
# ─────────────────────────────────────────────────────────────────────────────

def _write_float32(path: Path, audio, sr: int):
    """Schreibt Audio als 32-bit float WAV (verlustfrei, maximale Präzision)."""
    import soundfile as sf
    sf.write(str(path), audio, sr, subtype="FLOAT")


# ─────────────────────────────────────────────────────────────────────────────
# Noise Reduction auf Vocals
# ─────────────────────────────────────────────────────────────────────────────

def _denoise_vocals(vocals_path: Path, log):
    """Reduziert Residualrauschen auf der Vocals-Spur mit noisereduce."""
    try:
        import noisereduce as nr
        import soundfile as sf
        import numpy as np

        log("Noise-Reduction auf Vocals …")
        audio, sr = sf.read(str(vocals_path), dtype="float32")

        # noisereduce erwartet (samples,) mono oder (channels, samples)
        if audio.ndim == 1:
            denoised = nr.reduce_noise(y=audio, sr=sr, prop_decrease=0.8,
                                       stationary=False)
        else:
            # Stereo: jeden Kanal einzeln
            channels = [
                nr.reduce_noise(y=audio[:, ch], sr=sr, prop_decrease=0.8,
                                stationary=False)
                for ch in range(audio.shape[1])
            ]
            denoised = np.stack(channels, axis=1)

        _write_float32(vocals_path, denoised, sr)
        log("  → Noise-Reduction abgeschlossen")

    except ImportError:
        log("  ! noisereduce nicht installiert — überspringe (pip install noisereduce)")
    except Exception as e:
        log(f"  ! Noise-Reduction Fehler (übersprungen): {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Separation: audio-separator (BS-RoFormer etc.)
# ─────────────────────────────────────────────────────────────────────────────

def _separate_audio_separator(input_path: Path, output_dir: Path, model_file: str, log):
    """Trennt mit audio-separator (BS-RoFormer / Mel-RoFormer / MDX)."""
    from audio_separator.separator import Separator
    import soundfile as sf

    output_dir.mkdir(parents=True, exist_ok=True)

    log(f"  Lade Modell: {model_file}")
    log("  (Beim ersten Mal: Download ~200-500 MB)")

    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)

    sep = Separator(
        output_dir=str(output_dir),
        output_format="wav",
        normalization_threshold=0.9,
        model_file_dir=str(models_dir),
    )
    sep.load_model(model_file)

    log("  Trenne …")
    output_files = sep.separate(str(input_path))

    stem = input_path.stem
    vocals_out = output_dir / f"{stem}_vocals.wav"
    bg_out     = output_dir / f"{stem}_background.wav"

    for f in output_files:
        # audio-separator gibt manchmal nur den Dateinamen zurück (kein vollst. Pfad)
        fp = Path(f) if Path(f).is_absolute() else output_dir / Path(f).name
        if not fp.exists():
            fp = output_dir / fp.name
        if not fp.exists():
            continue
        name_lower = fp.name.lower()
        is_vocals = ("vocal" in name_lower or "voice" in name_lower)
        is_bg     = ("instrum" in name_lower or "no vocal" in name_lower
                     or "no_vocal" in name_lower or "accompaniment" in name_lower
                     or "music" in name_lower or "karaoke" in name_lower)
        if is_vocals and fp != vocals_out:
            fp.replace(vocals_out)
        elif is_bg and fp != bg_out:
            fp.replace(bg_out)

    # Fallback: falls bg_out noch nicht existiert, erstes verbleibendes WAV nehmen
    if not bg_out.exists():
        for leftover in output_dir.glob(f"{stem}*.wav"):
            if leftover != vocals_out:
                leftover.replace(bg_out)
                break

    # Restliche unbenannte Ausgaben umbenennen
    remaining = [f for f in output_dir.glob(f"{stem}*.wav")
                 if Path(f) != vocals_out and Path(f) != bg_out]
    for i, f in enumerate(remaining):
        try:
            Path(f).replace(output_dir / f"{stem}_part{i+1}.wav")
        except Exception:
            pass

    # Als 32-bit float neu speichern für maximale Präzision
    for out_path in (vocals_out, bg_out):
        if out_path.exists():
            audio, sr = sf.read(str(out_path), dtype="float32")
            _write_float32(out_path, audio, sr)

    return vocals_out, bg_out


# ─────────────────────────────────────────────────────────────────────────────
# Ensemble-Separation: mehrere Modelle → mitteln
# ─────────────────────────────────────────────────────────────────────────────

def _separate_ensemble(input_path: Path, output_dir: Path, models: list, log):
    """Trennt mit mehreren Modellen und mittelt die Ergebnisse (beste Qualität)."""
    import numpy as np
    import soundfile as sf

    tmp_dir = output_dir / "_tmp_ensemble"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    all_vocals, all_bg = [], []
    sr_ref = None

    for i, model_file in enumerate(models):
        log(f"\n[{i+1}/{len(models)}] {model_file}")
        model_tmp = tmp_dir / f"m{i}"
        try:
            v, b = _separate_audio_separator(input_path, model_tmp, model_file, log)
        except ImportError:
            log("audio-separator nicht installiert — Fallback auf demucs")
            v, b = _separate_demucs(input_path, model_tmp, "htdemucs_ft", log)

        v_audio, sr = sf.read(str(v), dtype="float32")
        b_audio, _  = sf.read(str(b), dtype="float32")
        all_vocals.append(v_audio)
        all_bg.append(b_audio)
        sr_ref = sr

    log(f"\nMittle {len(models)} Modelle …")

    # Auf gemeinsame Länge kürzen und mitteln
    min_len_v = min(a.shape[0] for a in all_vocals)
    min_len_b = min(a.shape[0] for a in all_bg)
    vocals_avg = sum(a[:min_len_v] for a in all_vocals) / len(all_vocals)
    bg_avg     = sum(a[:min_len_b] for a in all_bg)     / len(all_bg)

    stem = input_path.stem
    vocals_out = output_dir / f"{stem}_vocals.wav"
    bg_out     = output_dir / f"{stem}_background.wav"

    _write_float32(vocals_out, vocals_avg, sr_ref)
    _write_float32(bg_out,     bg_avg,     sr_ref)

    # Numpy-Arrays freigeben bevor rmtree läuft (Windows-Datei-Locks)
    del all_vocals, all_bg, vocals_avg, bg_avg

    # Temp-Ordner aufräumen — bei Windows-Locks mehrmals versuchen
    import time
    for _ in range(5):
        try:
            shutil.rmtree(tmp_dir)
            break
        except OSError:
            time.sleep(0.5)
    else:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return vocals_out, bg_out


# ─────────────────────────────────────────────────────────────────────────────
# Separation: demucs (Fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _separate_demucs(input_path: Path, output_dir: Path, model: str, log):
    """Trennt mit demucs Python-API."""
    import numpy as np
    import soundfile as sf
    import torch
    import librosa
    from demucs.pretrained import get_model
    from demucs.apply import apply_model

    log(f"  Lade demucs Modell: {model}")
    mdl = get_model(model)
    model_sr = mdl.samplerate
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log(f"  Gerät: {device}")
    mdl = mdl.to(device)
    mdl.eval()

    log("  Lese Audio …")
    audio, sr = sf.read(str(input_path), dtype="float32")
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=0)
    else:
        audio = audio.T
    if sr != model_sr:
        log(f"  Resample {sr} → {model_sr} Hz …")
        audio = librosa.resample(audio, orig_sr=sr, target_sr=model_sr)

    wav = torch.from_numpy(audio).float().unsqueeze(0).to(device)
    log("  Trenne …")
    with torch.no_grad():
        sources = apply_model(mdl, wav, progress=False)

    source_names = list(mdl.sources)
    vocals_idx = source_names.index("vocals")
    no_vocals = torch.zeros_like(sources[0, 0])
    for idx, name in enumerate(source_names):
        if name != "vocals":
            no_vocals += sources[0, idx]
    vocals = sources[0, vocals_idx]

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    vocals_out = output_dir / f"{stem}_vocals.wav"
    bg_out     = output_dir / f"{stem}_background.wav"

    _write_float32(vocals_out, vocals.cpu().numpy().T,    model_sr)
    _write_float32(bg_out,     no_vocals.cpu().numpy().T, model_sr)

    del mdl, wav, sources
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return vocals_out, bg_out


# ─────────────────────────────────────────────────────────────────────────────
# Haupt-Separation-Dispatcher
# ─────────────────────────────────────────────────────────────────────────────

def run_separation(input_path: Path, output_dir: Path, model_cfg: dict,
                   denoise: bool, log, on_done):
    try:
        engine = model_cfg["engine"]

        if engine == "ensemble":
            vocals, bg = _separate_ensemble(
                input_path, output_dir, model_cfg["models"], log)

        elif engine == "audio-separator":
            try:
                vocals, bg = _separate_audio_separator(
                    input_path, output_dir, model_cfg["model"], log)
            except ImportError:
                log("audio-separator nicht installiert — Fallback auf demucs htdemucs_ft")
                vocals, bg = _separate_demucs(
                    input_path, output_dir, "htdemucs_ft", log)

        else:  # demucs
            vocals, bg = _separate_demucs(
                input_path, output_dir, model_cfg["model"], log)

        if denoise:
            _denoise_vocals(vocals, log)

        log(f"\n✓ Fertig!")
        log(f"  Stimme/Sprache: {vocals.name}")
        log(f"  Hintergrund:    {bg.name}")
        log(f"  Format:         32-bit float WAV (verlustfrei)")
        log(f"  Ordner:         {output_dir}")
        on_done(True, str(output_dir))

    except Exception as e:
        log(f"\n✗ Fehler: {e}")
        import traceback
        log(traceback.format_exc())
        on_done(False, "")


# ─────────────────────────────────────────────────────────────────────────────
# Icon: Schallwelle die sich in zwei Spuren aufteilt
# ─────────────────────────────────────────────────────────────────────────────

def _draw_icon(size: int):
    """Zeichnet das AudioSeparator-Icon in der gegebenen Größe (PIL Image)."""
    from PIL import Image, ImageDraw

    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)

    # Hintergrund: abgerundetes Quadrat, dunkel
    r = max(4, size // 6)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r,
                        fill=(30, 30, 46, 255))

    lw     = max(2, size // 28)          # Linienbreite
    pad    = int(size * 0.11)            # Rand links/rechts
    cy     = size // 2                   # vertikale Mitte
    amp    = int(size * 0.14)            # Wellenamplitude eingehend
    fork_x = int(size * 0.50)           # Gabelungspunkt X
    end_x  = size - pad                  # rechter Rand

    WHT = (205, 214, 244, 255)           # #cdd6f4 eingehende Welle
    GRN = (166, 227, 161, 255)           # #a6e3a1 Vocals (oben)
    BLU = (137, 180, 250, 255)           # #89b4fa Hintergrund (unten)

    # ── Eingehende Welle (links → Gabelungspunkt), weiß ──────────────────────
    pts = []
    for x in range(pad, fork_x + 1):
        t = (x - pad) / max(1, fork_x - pad) * math.pi * 2.4
        y = cy + int(math.sin(t) * amp)
        pts.append((x, y))
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i + 1]], fill=WHT, width=lw)

    # ── Gabelungs-Y (kurze diagonale Äste) ───────────────────────────────────
    spread  = int(size * 0.20)
    branch  = int(size * 0.10)
    top_cy  = cy - spread
    bot_cy  = cy + spread
    fx_end  = fork_x + branch

    d.line([(fork_x, cy), (fx_end, top_cy)], fill=WHT, width=lw)
    d.line([(fork_x, cy), (fx_end, bot_cy)], fill=WHT, width=lw)

    # ── Obere Ausgangswelle: Vocals (grün) ────────────────────────────────────
    pts_top = []
    for x in range(fx_end, end_x + 1):
        t = (x - fx_end) / max(1, end_x - fx_end) * math.pi * 1.8
        y = top_cy + int(math.sin(t) * amp * 0.55)
        pts_top.append((x, y))
    for i in range(len(pts_top) - 1):
        d.line([pts_top[i], pts_top[i + 1]], fill=GRN, width=lw)

    # ── Untere Ausgangswelle: Hintergrund/Musik (blau) ───────────────────────
    pts_bot = []
    for x in range(fx_end, end_x + 1):
        t = (x - fx_end) / max(1, end_x - fx_end) * math.pi * 2.4 + 0.6
        y = bot_cy + int(math.sin(t) * amp * 0.45)
        pts_bot.append((x, y))
    for i in range(len(pts_bot) - 1):
        d.line([pts_bot[i], pts_bot[i + 1]], fill=BLU, width=lw)

    return img


def _make_icon_file() -> Path | None:
    """Erstellt icon.ico neben dem Skript (wird gecacht, nur 1× erzeugt)."""
    icon_path = Path(__file__).parent / "icon.ico"
    if icon_path.exists():
        return icon_path
    try:
        from PIL import Image
        sizes = [256, 64, 48, 32, 16]
        imgs  = [_draw_icon(s) for s in sizes]
        imgs[0].save(
            str(icon_path), format="ICO",
            append_images=imgs[1:],
            sizes=[(s, s) for s in sizes],
        )
        return icon_path
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AudioSeparator  —  Vocals / Hintergrund")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")
        self._default_output = str(Path(__file__).parent / "getrennt")
        self._apply_icon()
        self._build_ui()
        self._center()

    def _apply_icon(self):
        """Setzt das custom Icon (Fenster + Windows-Taskleiste)."""
        ico = _make_icon_file()
        if ico and ico.exists():
            try:
                self.iconbitmap(str(ico))
            except Exception:
                pass
        # Fallback / zusätzlich: PhotoImage für Fenstertitel-Icon
        try:
            from PIL import Image, ImageTk
            img = _draw_icon(64)
            ph  = ImageTk.PhotoImage(img)
            self.iconphoto(True, ph)
            self._icon_ref = ph   # Referenz halten damit GC es nicht löscht
        except Exception:
            pass

    def _center(self):
        self.update_idletasks()
        w, h = 680, 660
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        BG  = "#1e1e2e"
        FG  = "#cdd6f4"
        ACC = "#89b4fa"
        ENT = "#313244"
        GRN = "#a6e3a1"
        DIM = "#6c7086"

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel",       background=BG, foreground=FG,  font=("Segoe UI", 10))
        style.configure("TButton",      background=ACC, foreground="#1e1e2e",
                        font=("Segoe UI", 10, "bold"), padding=6)
        style.map("TButton",            background=[("active", "#74c7ec")])
        style.configure("TCombobox",    fieldbackground=ENT, background=ENT,
                        foreground=FG, selectbackground=ENT,
                        selectforeground=FG, insertcolor=FG)
        style.map("TCombobox",
                  fieldbackground=[("readonly", ENT), ("disabled", BG)],
                  foreground=[("readonly", FG), ("disabled", DIM)],
                  selectbackground=[("readonly", ENT)],
                  selectforeground=[("readonly", FG)])
        style.configure("TFrame",       background=BG)
        style.configure("TLabelframe",  background=BG, foreground=ACC)
        style.configure("TLabelframe.Label", background=BG, foreground=ACC,
                        font=("Segoe UI", 10, "bold"))
        style.configure("Go.TButton",   background=GRN, foreground="#1e1e2e",
                        font=("Segoe UI", 11, "bold"), padding=8)
        style.map("Go.TButton",         background=[("active", "#94e2d5"),
                                                    ("disabled", "#45475a")])
        style.configure("TCheckbutton", background=BG, foreground=FG,
                        font=("Segoe UI", 10))
        style.map("TCheckbutton",       background=[("active", BG)],
                  foreground=[("active", ACC)])

        PAD = {"padx": 14, "pady": 5}

        # ── Eingabe ──────────────────────────────────────────────────────────
        frm_in = ttk.LabelFrame(self, text="  Eingabedatei  ", padding=10)
        frm_in.pack(fill="x", **PAD)
        self._input_var = tk.StringVar()
        tk.Entry(frm_in, textvariable=self._input_var, bg=ENT, fg=FG,
                 insertbackground=FG, relief="flat", font=("Segoe UI", 9)
                 ).pack(side="left", fill="x", expand=True, ipady=4, padx=(0,8))
        ttk.Button(frm_in, text="Durchsuchen …",
                   command=self._browse_input).pack(side="right")

        # ── Ausgabe ──────────────────────────────────────────────────────────
        frm_out = ttk.LabelFrame(self, text="  Ausgabeordner  ", padding=10)
        frm_out.pack(fill="x", **PAD)
        self._output_var = tk.StringVar(value=self._default_output)
        tk.Entry(frm_out, textvariable=self._output_var, bg=ENT, fg=FG,
                 insertbackground=FG, relief="flat", font=("Segoe UI", 9)
                 ).pack(side="left", fill="x", expand=True, ipady=4, padx=(0,8))
        ttk.Button(frm_out, text="Durchsuchen …",
                   command=self._browse_output).pack(side="right")

        # ── Modell ───────────────────────────────────────────────────────────
        frm_model = ttk.LabelFrame(self, text="  Modell  ", padding=10)
        frm_model.pack(fill="x", **PAD)
        self._model_var = tk.StringVar(value=MODELS[0]["label"])
        ttk.Combobox(frm_model, textvariable=self._model_var,
                     values=[m["label"] for m in MODELS],
                     state="readonly", font=("Segoe UI", 9)
                     ).pack(fill="x", ipady=3)
        ttk.Label(frm_model,
                  text="Ensemble = BS-RoFormer + Mel-RoFormer Big (empfohlen, 2x laenger)   demucs = Fallback",
                  foreground=DIM, font=("Segoe UI", 8)
                  ).pack(anchor="w", pady=(4, 0))

        # ── Optionen ─────────────────────────────────────────────────────────
        frm_opt = ttk.LabelFrame(self, text="  Optionen  ", padding=10)
        frm_opt.pack(fill="x", **PAD)

        self._denoise_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frm_opt,
            text="Noise-Reduction auf Vocals  (entfernt Residualrauschen nach Trennung)",
            variable=self._denoise_var,
        ).pack(anchor="w")

        ttk.Label(frm_opt,
                  text="Ausgabe immer als 32-bit float WAV  (verlustfrei, maximale Präzision)",
                  foreground=DIM, font=("Segoe UI", 8)
                  ).pack(anchor="w", pady=(4, 0))

        # ── Start ────────────────────────────────────────────────────────────
        self._btn_start = ttk.Button(self, text="▶  Trennen starten",
                                     command=self._start, style="Go.TButton")
        self._btn_start.pack(fill="x", padx=14, pady=(10, 4))

        # ── Log ──────────────────────────────────────────────────────────────
        frm_log = ttk.LabelFrame(self, text="  Fortschritt  ", padding=8)
        frm_log.pack(fill="both", expand=True, **PAD)
        self._log_text = tk.Text(frm_log, bg="#11111b", fg="#a6e3a1",
                                 font=("Consolas", 9), relief="flat",
                                 state="disabled", wrap="word")
        sb = ttk.Scrollbar(frm_log, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log_text.pack(fill="both", expand=True)

        # ── Ordner öffnen ────────────────────────────────────────────────────
        self._btn_open = ttk.Button(self, text="📂  Ausgabeordner öffnen",
                                    command=self._open_output, state="disabled")
        self._btn_open.pack(fill="x", padx=14, pady=(0, 10))
        self._result_dir = ""

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _browse_input(self):
        p = filedialog.askopenfilename(title="Eingabedatei wählen", filetypes=SUPPORTED)
        if p:
            self._input_var.set(p)
            if not self._output_var.get():
                self._output_var.set(self._default_output)

    def _browse_output(self):
        p = filedialog.askdirectory(title="Ausgabeordner wählen")
        if p:
            self._output_var.set(p)

    def _log_write(self, msg: str):
        self._log_text.configure(state="normal")
        self._log_text.insert("end", msg + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _log(self, msg: str):
        self.after(0, self._log_write, msg)

    def _start(self):
        inp = self._input_var.get().strip()
        out = self._output_var.get().strip()
        if not inp or not Path(inp).exists():
            messagebox.showwarning("Fehler", "Bitte eine gültige Eingabedatei wählen.")
            return
        if not out:
            messagebox.showwarning("Fehler", "Bitte einen Ausgabeordner wählen.")
            return

        label = self._model_var.get()
        model_cfg = next(m for m in MODELS if m["label"] == label)
        denoise   = self._denoise_var.get()

        self._btn_start.configure(state="disabled")
        self._btn_open.configure(state="disabled")
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

        mode_info = "Ensemble (2 Modelle)" if model_cfg["engine"] == "ensemble" \
                    else model_cfg.get("model", "")
        self._log(f"Eingabe:  {Path(inp).name}")
        self._log(f"Modell:   {mode_info}")
        self._log(f"Denoise:  {'ja' if denoise else 'nein'}\n")

        def on_done(success, result_dir):
            self._result_dir = result_dir
            self.after(0, self._btn_start.configure, {"state": "normal"})
            if success:
                self.after(0, self._btn_open.configure, {"state": "normal"})

        threading.Thread(
            target=run_separation,
            args=(Path(inp), Path(out), model_cfg, denoise, self._log, on_done),
            daemon=True,
        ).start()

    def _open_output(self):
        if self._result_dir and Path(self._result_dir).exists():
            os.startfile(self._result_dir)


if __name__ == "__main__":
    App().mainloop()
