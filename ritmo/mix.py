#!/usr/bin/env python3
"""MIX dal cue.json: voce + tracce della musica con le loro automazioni (silenzi, basso trattenuto, drop)
+ un suono per ogni evento, abbassamento automatico della musica sotto la voce, loudness finale per i social.

Uso: python ritmo/mix.py cue.json -o mix.wav [--lufs -14]
I suoni si cercano in cue["suoni"] (cartella) come <nome>.wav/.mp3/.ogg/.flac."""
import argparse, subprocess, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from audio import SR, carica, salva, leggi, loudness


def inviluppo(n, au, traccia, sr):
    g = np.ones(n, np.float32)
    for a in au:
        if a["traccia"] not in (traccia, "*"):
            continue
        i0, i1, r = int(a["da"] * sr), int(a["a"] * sr), max(1, int(a["rampa"] * sr))
        seg = np.full(max(0, min(n, i1) - max(0, i0)), a["livello"], np.float32)
        if len(seg) == 0:
            continue
        # rampe morbide ai bordi (mai scatti)
        k = min(r, len(seg) // 2)
        if k:
            seg[:k] = np.linspace(1, a["livello"], k); seg[-k:] = np.linspace(a["livello"], 1, k)
        g[max(0, i0):max(0, i0) + len(seg)] = np.minimum(g[max(0, i0):max(0, i0) + len(seg)], seg)
    return g


def segui(x, sr, att=0.03, rel=0.6):
    """inviluppo della voce (0..1) con attacco veloce e rilascio lento"""
    w = int(sr * 0.02)
    e = np.sqrt(np.convolve(x ** 2, np.ones(w) / w, "same"))
    e = np.clip(e / (np.percentile(e[e > 1e-4], 90) if np.any(e > 1e-4) else 1), 0, 1)
    out = np.zeros_like(e); a, r = np.exp(-1 / (att * sr)), np.exp(-1 / (rel * sr)); v = 0.0
    for i, s in enumerate(e[:: 48]):        # calcolo a passi di 1 ms, poi interpolo
        v = a * v + (1 - a) * s if s > v else r * v + (1 - r) * s
        out[i * 48:(i + 1) * 48] = v
    return out


def cerca(cartella, nome):
    for ext in (".wav", ".mp3", ".ogg", ".flac"):
        p = Path(cartella) / (nome + ext)
        if p.exists():
            return p
    sys.exit(f"Suono non trovato: {nome} in {cartella}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cue"); ap.add_argument("-o", "--out", default="mix.wav"); ap.add_argument("--lufs", type=float, default=-14)
    x = ap.parse_args()
    base = Path(x.cue).parent
    C = leggi(x.cue)
    n = int(C["durata"] * SR)
    mix = np.zeros((2, n), np.float32)
    v = carica(base / C["voce"])[:, :n] * C.get("voce_volume", 1.0)
    mix[:, :v.shape[1]] += v
    M = C.get("musica")
    if M:
        duck = 1 - M["ducking"] * segui(np.pad(v.mean(0), (0, n - v.shape[1])), SR)
        fo = int(M["fade_out"] * SR)
        coda = np.ones(n, np.float32); coda[-fo:] = np.linspace(1, 0, fo) ** 2
        segs = M.get("segmenti") or [{"da": 0, "a": C["durata"], "offset": M["offset"]}]
        for nome, f in M["tracce"].items():
            a = carica(base / f)
            tr = np.zeros((2, n), np.float32)
            for sg in segs:                          # ogni segmento: il pezzo di brano giusto, con 15 ms di raccordo ai bordi
                i0, i1 = int(sg["da"] * SR), min(n, int(sg["a"] * SR))
                s0 = int((sg["da"] - sg["offset"]) * SR)
                k = min(i1 - i0, a.shape[1] - s0)
                if k <= 0 or s0 < 0:
                    continue
                pz = a[:, s0:s0 + k].copy(); r = min(k // 2, int(.015 * SR))
                pz[:, :r] *= np.linspace(0, 1, r); pz[:, k - r:] *= np.linspace(1, 0, r)
                tr[:, i0:i0 + k] += pz
            mix += tr * inviluppo(n, C["automazioni"], nome, SR) * duck * coda * M["volume"]
    for e in C["eventi"]:
        if not e.get("suono"):
            continue
        s = carica(cerca(base / C["suoni"], e["suono"]))
        if e.get("dur"):
            s = s[:, :int(e["dur"] * SR)]
            f = min(s.shape[1], int(0.03 * SR)); s[:, -f:] *= np.linspace(1, 0, f)
        p = e.get("pan", 0.0)                       # -1 sinistra .. +1 destra, potenza costante
        g = np.array([np.cos((p + 1) * np.pi / 4), np.sin((p + 1) * np.pi / 4)], np.float32)[:, None] * np.sqrt(2)
        i0 = int(e["t"] * SR); j0 = max(0, -i0); i0 = max(0, i0)
        k = min(n - i0, s.shape[1] - j0)
        if k > 0:
            mix[:, i0:i0 + k] += s[:, j0:j0 + k] * g * e.get("vol", 0.5)
    pre = Path(x.out).with_suffix(".pre.wav")
    salva(pre, mix)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pre), "-af",
                    f"loudnorm=I={x.lufs}:TP=-1.5:LRA=11,alimiter=limit=0.8:level=disabled,aresample={SR}", "-c:a", "pcm_s24le", x.out], check=True)
    pre.unlink()
    L = loudness(x.out)
    print(f"{x.out}: {C['durata']}s, {sum(1 for e in C['eventi'] if e.get('suono'))} suoni, {L['lufs']} LUFS, picco {L['picco']} dBFS")


if __name__ == "__main__":
    main()
