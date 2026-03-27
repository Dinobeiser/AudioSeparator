"""
AudioSeparator - Vocals / Hintergrund Trenner
DEIN ORIGINAL-DESIGN mit Auto-Download & FFmpeg-Fix.
"""

import math
import os
import shutil
import threading
import subprocess
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
]

# ─────────────────────────────────────────────────────────────────────────────
# Smart Engine: FFmpeg Check & Modell Downloader
# ─────────────────────────────────────────────────────────────────────────────

def ensure_system_dependencies(log_func):
    """Prüft FFmpeg und lädt Modelle von deinem GitHub."""

    # 1. FFmpeg Check (von install.bat)
    if not shutil.which("ffmpeg"):
        log_func("System-Check: FFmpeg fehlt.")
        log_func("Versuche Installation via winget...")
        try:
            subprocess.run(["winget", "install", "Gyan.FFmpeg", "--accept-source-agreements", "--accept-package-agreements"],
                           check=True, shell=True)
            log_func("✓ FFmpeg erfolgreich installiert.")
        except Exception:
            log_func("! Automatisches FFmpeg-Setup fehlgeschlagen. Bitte manuell installieren.")

    # 2. Modell-Download
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
                # FIX: chunk_size mit Unterstrich!
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
                                    log_func(f"  ... {done}% geladen")
                    log_func(f"  ✓ {filename} bereit.")
            except Exception as e:
                log_func(f"  ! Fehler bei {filename}: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Trennungs-Logik (Dein Original-Code)
# ─────────────────────────────────────────────────────────────────────────────

def _write_float32(path, audio, sr):
    import soundfile as sf
    sf.write(str(path), audio, sr, subtype="FLOAT")

def _denoise_vocals(vocals_path, log):
    try:
        import noisereduce as nr
        import soundfile as sf
        import numpy as np
        log("Noise-Reduction auf Vocals …")
        audio, sr = sf.read(str(vocals_path), dtype="float32")
        if audio.ndim == 1:
            denoised = nr.reduce_noise(y=audio, sr=sr, prop_decrease=0.8, stationary=False)
        else:
            channels = [nr.reduce_noise(y=audio[:, ch], sr=sr, prop_decrease=0.8, stationary=False) for ch in range(audio.shape[1])]
            denoised = np.stack(channels, axis=1)
        _write_float32(vocals_path, denoised, sr)
        log("  → Noise-Reduction abgeschlossen")
    except Exception as e:
        log(f"  ! Denoise Fehler: {e}")

def _separate_audio_separator(input_path, output_dir, model_file, log):
    from audio_separator.separator import Separator
    import soundfile as sf
    output_dir.mkdir(parents=True, exist_ok=True)
    models_dir = Path(__file__).parent / "models"
    sep = Separator(output_dir=str(output_dir), output_format="wav", normalization_threshold=0.9, model_file_dir=str(models_dir))
    sep.load_model(model_file)
    log("  Trenne …")
    output_files = sep.separate(str(input_path))
    stem = input_path.stem
    vocals_out, bg_out = output_dir / f"{stem}_vocals.wav", output_dir / f"{stem}_background.wav"
    for f in output_files:
        fp = Path(f) if Path(f).is_absolute() else output_dir / Path(f).name
        if not fp.exists(): fp = output_dir / fp.name
        if not fp.exists(): continue
        name_lower = fp.name.lower()
        if "vocal" in name_lower or "voice" in name_lower: fp.replace(vocals_out)
        elif "instrum" in name_lower or "no vocal" in name_lower or "music" in name_lower: fp.replace(bg_out)
    for out_path in (vocals_out, bg_out):
        if out_path.exists():
            audio, sr = sf.read(str(out_path), dtype="float32")
            _write_float32(out_path, audio, sr)
    return vocals_out, bg_out

def _separate_ensemble(input_path, output_dir, models, log):
    import numpy as np
    import soundfile as sf
    tmp_dir = output_dir / "_tmp_ensemble"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    all_vocals, all_bg, sr_ref = [], [], None
    for i, model_file in enumerate(models):
        log(f"\n[{i+1}/{len(models)}] {model_file}")
        v, b = _separate_audio_separator(input_path, tmp_dir / f"m{i}", model_file, log)
        v_audio, sr = sf.read(str(v), dtype="float32")
        b_audio, _  = sf.read(str(b), dtype="float32")
        all_vocals.append(v_audio); all_bg.append(b_audio); sr_ref = sr
    log(f"\nMittle Modelle …")
    min_v, min_b = min(a.shape[0] for a in all_vocals), min(a.shape[0] for a in all_bg)
    vocals_out, bg_out = output_dir / f"{input_path.stem}_vocals.wav", output_dir / f"{input_path.stem}_background.wav"
    _write_float32(vocals_out, sum(a[:min_v] for a in all_vocals) / len(all_vocals), sr_ref)
    _write_float32(bg_out, sum(a[:min_b] for a in all_bg) / len(all_bg), sr_ref)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return vocals_out, bg_out

def run_separation(input_path, output_dir, model_cfg, denoise, log, on_done):
    try:
        ensure_system_dependencies(log)
        engine = model_cfg["engine"]
        if engine == "ensemble": vocals, bg = _separate_ensemble(input_path, output_dir, model_cfg["models"], log)
        elif engine == "audio-separator": vocals, bg = _separate_audio_separator(input_path, output_dir, model_cfg["model"], log)
        if denoise: _denoise_vocals(vocals, log)
        log(f"\n✓ Fertig! Ordner: {output_dir}")
        on_done(True, str(output_dir))
    except Exception as e:
        log(f"\n✗ Fehler: {e}"); on_done(False, "")

# ─────────────────────────────────────────────────────────────────────────────
# DEINE ORIGINAL GUI (Unverändert)
# ─────────────────────────────────────────────────────────────────────────────

def _draw_icon(size: int):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=max(4, size // 6), fill=(30, 30, 46, 255))
    lw, pad, cy, amp, fork_x, end_x = max(2, size // 28), int(size * 0.11), size // 2, int(size * 0.14), int(size * 0.50), size - int(size * 0.11)
    WHT, GRN, BLU = (205, 214, 244, 255), (166, 227, 161, 255), (137, 180, 250, 255)
    pts = []
    for x in range(pad, fork_x + 1):
        t = (x - pad) / max(1, fork_x - pad) * math.pi * 2.4
        pts.append((x, cy + int(math.sin(t) * amp)))
    for i in range(len(pts) - 1): d.line([pts[i], pts[i + 1]], fill=WHT, width=lw)
    fx_end, spread = fork_x + int(size * 0.10), int(size * 0.20)
    d.line([(fork_x, cy), (fx_end, cy - spread)], fill=WHT, width=lw)
    d.line([(fork_x, cy), (fx_end, cy + spread)], fill=WHT, width=lw)
    return img

def _make_icon_file():
    icon_path = Path(__file__).parent / "icon.ico"
    if icon_path.exists(): return icon_path
    try:
        from PIL import Image
        imgs = [_draw_icon(s) for s in [256, 64, 48, 32, 16]]
        imgs[0].save(str(icon_path), format="ICO", append_images=imgs[1:], sizes=[(s, s) for s in [256, 64, 48, 32, 16]])
        return icon_path
    except Exception: return None

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AudioSeparator — Vocals / Hintergrund")
        self.resizable(False, False); self.configure(bg="#1e1e2e")
        self._default_output = str(Path(__file__).parent / "getrennt")
        self._apply_icon(); self._build_ui(); self._center()

    def _apply_icon(self):
        ico = _make_icon_file()
        if ico: self.iconbitmap(str(ico))

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
        style.configure("TFrame", background=BG)
        style.configure("TLabelframe", background=BG, foreground=ACC)
        style.configure("TLabelframe.Label", background=BG, foreground=ACC, font=("Segoe UI", 10, "bold"))
        style.configure("Go.TButton", background=GRN, foreground="#1e1e2e", font=("Segoe UI", 11, "bold"), padding=8)

        PAD = {"padx": 14, "pady": 5}
        frm_in = ttk.LabelFrame(self, text="  Eingabedatei  ", padding=10); frm_in.pack(fill="x", **PAD)
        self._input_var = tk.StringVar()
        tk.Entry(frm_in, textvariable=self._input_var, bg=ENT, fg=FG, insertbackground=FG, relief="flat").pack(side="left", fill="x", expand=True, padx=(0,8))
        ttk.Button(frm_in, text="Durchsuchen", command=self._browse_input).pack(side="right")

        frm_out = ttk.LabelFrame(self, text="  Ausgabeordner  ", padding=10); frm_out.pack(fill="x", **PAD)
        self._output_var = tk.StringVar(value=self._default_output)
        tk.Entry(frm_out, textvariable=self._output_var, bg=ENT, fg=FG, insertbackground=FG, relief="flat").pack(side="left", fill="x", expand=True, padx=(0,8))
        ttk.Button(frm_out, text="Durchsuchen", command=self._browse_output).pack(side="right")

        frm_model = ttk.LabelFrame(self, text="  Modell  ", padding=10); frm_model.pack(fill="x", **PAD)
        self._model_var = tk.StringVar(value=MODELS[0]["label"])
        ttk.Combobox(frm_model, textvariable=self._model_var, values=[m["label"] for m in MODELS], state="readonly").pack(fill="x")

        self._denoise_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="Noise-Reduction auf Vocals", variable=self._denoise_var, style="TCheckbutton").pack(anchor="w", padx=14)

        self._btn_start = ttk.Button(self, text="▶  Trennen starten", command=self._start, style="Go.TButton")
        self._btn_start.pack(fill="x", padx=14, pady=10)

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
