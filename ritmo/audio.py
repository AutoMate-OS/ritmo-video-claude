"""Funzioni comuni: lettura/scrittura audio con ffmpeg, livelli, tempi. Nessuna rete."""
import json, subprocess, shutil, sys
import numpy as np

SR = 48000


def serve(cmd):
    if not shutil.which(cmd):
        sys.exit(f"Manca '{cmd}': installalo (ffmpeg.org) e riprova.")


def carica(path, sr=SR, mono=False):
    """Qualsiasi file audio/video -> array float32 (canali, campioni)."""
    serve("ffmpeg")
    ch = 1 if mono else 2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).reshape(-1, ch).T.copy()
    return a[0] if mono else a


def salva(path, a, sr=SR):
    serve("ffmpeg")
    a = np.atleast_2d(a).astype(np.float32)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", str(a.shape[0]), "-i", "-",
                    "-c:a", "pcm_s24le", str(path)], input=a.T.tobytes(), check=True)


def db(x):
    return float(20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-9))


def durata(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]))


def loudness(path):
    """Loudness integrata (LUFS) e picco vero (dBFS) misurati da ffmpeg."""
    o = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr.split("Summary:")[-1]
    num = lambda k: float(o.split(k)[1].split()[0])
    return {"lufs": num("I:"), "picco": num("Peak:")}


def leggi(path):
    return json.load(open(path, encoding="utf-8"))


def scrivi(path, obj):
    json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
