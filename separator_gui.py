"""
AudioSeparator - Vocals / Hintergrund Trenner
FIXED: GitHub-Download & Windows File-Lock Schutz.
"""

import math
import os
import shutil
import threading
import time
import tkinter as tk
import requests
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

SUPPORTED = (
    ("Audio/Video Dateien", "*.wav *.mp3 *.mp4 *.mkv *.flac *.ogg *.m4a *.aac *.wma"),
    ("Alle Dateien", "*.*"),
)

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
        "label":   "MDX-Net Inst HQ3  \u2605\u2605\u2605\u2605  (gut fur Musik)",
        "engine":  "audio-separator",
        "model":   "UVR-MDX-NET-Inst_HQ_3.onnx",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Rettungs-Funktionen (Download & File-Lock)
# ─────────────────────────────────────────────────────────────────────────────

def ensure_models_exist(log_func):
    """Lädt fehlende Modelle von GitHub."""
    BASE_URL = "https://github.com/Dinobeiser/AudioSeparator/releases/download/v1.0/"
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)

    files = [
        "model_bs_roformer_ep_317_sdr_12.9755.ckpt", "model_bs_roformer_ep_317_sdr_12.9755.yaml",
        "melband_roformer_big_beta5e.ckpt", "melband_roformer_big_beta5e.yaml",
        "model_mel_band_roformer_ep_3005_sdr_11.4360.ckpt", "model_mel_band_roformer_ep_3005_sdr_11.4360.yaml",
        "UVR-MDX-NET-Inst_HQ_3.onnx"
    ]

    for filename in files:
        target = models_dir / filename
        if not target.exists():
            log_func(f"Download: {filename} fehlt...")
            try:
                r = requests.get(BASE_URL + filename, stream=True, timeout=600)
                if r.status_code == 200:
                    total = int(r.headers.get('content-length', 0))
                    dl = 0
                    with open(target, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                                dl += len(chunk)
                                if dl % (20 * 1024 * 1024) < 65536:
                                    done = int(100 * dl / total) if total else 0
                                    log_func(f"    ... {done}% geladen")
                    log_func(f"  ✓ {filename} bereit.")
            except Exception as e:
                log_func(f"  ! Fehler bei {filename}: {e}")

def _safe_read_audio(path, log):
    """Verhindert den 'System error' bei blockierten Dateien."""
    import soundfile as sf
    for i in range(10):
        if not Path(path).exists():
            if i < 9:
                log(f"  (Warte auf Datei: {Path(path).name}...)")
                time.sleep(1.0)
                continue
            else:
                raise FileNotFoundError(f"Datei nicht gefunden: {path}")
        try:
            return sf.read(str(path), dtype="float32")
        except Exception:
            if i < 9:
                log(f"  (Warte auf Zugriff: {Path(path).name}...)")
                time.sleep(2.0)
            else:
                raise

def _write_float32(path: Path, audio, sr: int):
    import soundfile as sf
    sf.write(str(path), audio, sr, subtype="FLOAT")

# ─────────────────────────────────────────────────────────────────────────────
# Trennungs-Logik
# ─────────────────────────────────────────────────────────────────────────────

def _denoise_vocals(vocals_path: Path, log):
    try:
        import noisereduce as nr
        import numpy as np
        log("Noise-Reduction auf Vocals …")
        audio, sr = _safe_read_audio(vocals_path, log)
        if audio.ndim == 1:
            denoised = nr.reduce_noise(y=audio, sr=sr, prop_decrease=0.8, stationary=False)
        else:
            channels = [nr.reduce_noise(y=audio[:, ch], sr=sr, prop_decrease=0.8, stationary=False) for ch in range(audio.shape[1])]
            denoised = np.stack(channels, axis=1)
        _write_float32(vocals_path, denoised, sr)
        log("  → Noise-Reduction abgeschlossen")
    except Exception as e:
        log(f"  ! Denoise Fehler: {e}")

def _separate_audio_separator(input_path: Path, output_dir: Path, model_file: str, log):
    from audio_separator.separator import Separator
    output_dir.mkdir(parents=True, exist_ok=True)
    models_dir = Path(__file__).parent / "models"
    sep = Separator(output_dir=str(output_dir), output_format="wav", normalization_threshold=0.9, model_file_dir=str(models_dir))
    sep.load_model(model_file)
    log("  Trenne …")
    output_files = sep.separate(str(input_path))

    time.sleep(1.0)
    stem = input_path.stem
    vocals_out, bg_out = output_dir / f"{stem}_vocals.wav", output_dir / f"{stem}_background.wav"

    for f in output_files:
        fp = Path(f) if Path(f).is_absolute() else output_dir / Path(f).name
        if not fp.exists(): fp = output_dir / fp.name
        if not fp.exists(): continue
        name_lower = fp.name.lower()
        if "vocal" in name_lower or "voice" in name_lower: fp.replace(vocals_out)
        elif any(x in name_lower for x in ["instrum", "no vocal", "music", "other", "background", "accomp"]): fp.replace(bg_out)

    for out_path in (vocals_out, bg_out):
        if out_path.exists():
            audio, sr = _safe_read_audio(out_path, log)
            _write_float32(out_path, audio, sr)
    return vocals_out, bg_out

def _separate_ensemble(input_path: Path, output_dir: Path, models: list, log):
    import numpy as np
    tmp_dir = output_dir / "_tmp_ensemble"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    all_vocals, all_bg, sr_ref = [], [], None
    for i, m_file in enumerate(models):
        log(f"\n[{i+1}/{len(models)}] {m_file}")
        v, b = _separate_audio_separator(input_path, tmp_dir / f"m{i}", m_file, log)
        v_audio, sr = _safe_read_audio(v, log)
        b_audio, _  = _safe_read_audio(b, log)
        all_vocals.append(v_audio); all_bg.append(b_audio); sr_ref = sr

    min_v, min_b = min(a.shape[0] for a in all_vocals), min(a.shape[0] for a in all_bg)
    v_out, b_out = output_dir / f"{input_path.stem}_vocals.wav", output_dir / f"{input_path.stem}_background.wav"
    _write_float32(v_out, sum(a[:min_v] for a in all_vocals) / len(all_vocals), sr_ref)
    _write_float32(b_out, sum(a[:min_b] for a in all_bg) / len(all_bg), sr_ref)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return v_out, b_out

def run_separation(input_path: Path, output_dir: Path, model_cfg: dict, denoise: bool, log, on_done):
    try:
        ensure_models_exist(log)
        if model_cfg["engine"] == "ensemble":
            vocals, bg = _separate_ensemble(input_path, output_dir, model_cfg["models"], log)
        else:
            vocals, bg = _separate_audio_separator(input_path, output_dir, model_cfg["model"], log)
        if denoise: _denoise_vocals(vocals, log)
        log(f"\n✓ Fertig!"); on_done(True, str(output_dir))
    except Exception as e:
        log(f"\n✗ Fehler: {e}"); on_done(False, "")

# ─────────────────────────────────────────────────────────────────────────────
# GUI (Exakt dein Design)
# ─────────────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AudioSeparator  —  Vocals / Hintergrund")
        self.resizable(False, False); self.configure(bg="#1e1e2e")
        self._default_output = str(Path(__file__).parent / "getrennt")
        self._build_ui(); self._center()

    def _center(self):
        self.update_idletasks()
        w, h = 680, 660
        x, y = (self.winfo_screenwidth() - w) // 2, (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        BG, FG, ACC, ENT, GRN, DIM = "#1e1e2e", "#cdd6f4", "#89b4fa", "#313244", "#a6e3a1", "#6c7086"
        style = ttk.Style(self); style.theme_use("clam")
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("TButton", background=ACC, foreground="#1e1e2e", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("TLabelframe", background=BG, foreground=ACC)
        style.configure("TLabelframe.Label", background=BG, foreground=ACC, font=("Segoe UI", 10, "bold"))
        style.configure("Go.TButton", background=GRN, foreground="#1e1e2e", font=("Segoe UI", 11, "bold"), padding=8)
        style.configure("TCheckbutton", background=BG, foreground=FG)

        PAD = {"padx": 14, "pady": 5}

        # Eingabe
        frm_in = ttk.LabelFrame(self, text="  Eingabedatei  ", padding=10); frm_in.pack(fill="x", **PAD)
        self._input_var = tk.StringVar()
        tk.Entry(frm_in, textvariable=self._input_var, bg=ENT, fg=FG, insertbackground=FG, relief="flat").pack(side="left", fill="x", expand=True, padx=(0,8))
        ttk.Button(frm_in, text="Durchsuchen …", command=self._browse_input).pack(side="right")

        # Ausgabe
        frm_out = ttk.LabelFrame(self, text="  Ausgabeordner  ", padding=10); frm_out.pack(fill="x", **PAD)
        self._output_var = tk.StringVar(value=self._default_output)
        tk.Entry(frm_out, textvariable=self._output_var, bg=ENT, fg=FG, insertbackground=FG, relief="flat").pack(side="left", fill="x", expand=True, padx=(0,8))
        ttk.Button(frm_out, text="Durchsuchen …", command=self._browse_output).pack(side="right")

        # Modell
        frm_model = ttk.LabelFrame(self, text="  Modell  ", padding=10); frm_model.pack(fill="x", **PAD)
        self._model_var = tk.StringVar(value=MODELS[0]["label"])
        ttk.Combobox(frm_model, textvariable=self._model_var, values=[m["label"] for m in MODELS], state="readonly").pack(fill="x")

        # Optionen
        frm_opt = ttk.LabelFrame(self, text="  Optionen  ", padding=10); frm_opt.pack(fill="x", **PAD)
        self._denoise_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm_opt, text="Noise-Reduction auf Vocals", variable=self._denoise_var).pack(anchor="w")

        # Start
        self._btn_start = ttk.Button(self, text="▶  Trennen starten", command=self._start, style="Go.TButton")
        self._btn_start.pack(fill="x", padx=14, pady=10)

        # Log
        frm_log = ttk.LabelFrame(self, text="  Fortschritt  ", padding=8); frm_log.pack(fill="both", expand=True, **PAD)
        self._log_text = tk.Text(frm_log, bg="#11111b", fg=GRN, font=("Consolas", 9), relief="flat", state="disabled", wrap="word")
        self._log_text.pack(fill="both", expand=True)

        self._btn_open = ttk.Button(self, text="📂  Ausgabeordner öffnen", command=self._open_output, state="disabled")
        self._btn_open.pack(fill="x", padx=14, pady=(0, 10))

    def _browse_input(self):
        p = filedialog.askopenfilename(filetypes=SUPPORTED)
        if p: self._input_var.set(p)
    def _browse_output(self):
        p = filedialog.askdirectory()
        if p: self._output_var.set(p)
    def _log(self, msg):
        self.after(0, lambda: [self._log_text.configure(state="normal"), self._log_text.insert("end", msg + "\n"), self._log_text.see("end"), self._log_text.configure(state="disabled")])
    def _open_output(self):
        if hasattr(self, "_res") and Path(self._res).exists(): os.startfile(self._res)

    def _start(self):
        inp, out = self._input_var.get().strip(), self._output_var.get().strip()
        if not inp or not Path(inp).exists(): return
        model_cfg = next(m for m in MODELS if m["label"] == self._model_var.get())
        self._btn_start.configure(state="disabled")
        self._log_text.configure(state="normal"); self._log_text.delete("1.0", "end"); self._log_text.configure(state="disabled")
        def on_done(success, res):
            self._res = res
            self.after(0, lambda: [self._btn_start.configure(state="normal"), self._btn_open.configure(state="normal") if success else None])
        threading.Thread(target=run_separation, args=(Path(inp), Path(out), model_cfg, self._denoise_var.get(), self._log, on_done), daemon=True).start()

if __name__ == "__main__":
    App().mainloop()
