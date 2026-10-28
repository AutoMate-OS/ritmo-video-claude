#!/usr/bin/env python3
"""GRIGLIA DELLA MUSICA: tempo, battiti, inizio di ogni battuta (il "uno") ed energia di ogni battuta.
Con questi numeri Claude sa dove cade un colpo anche senza sentirlo.

Uso:
  python ritmo/griglia.py musica.mp3                 -> griglia.json
  python ritmo/griglia.py musica.mp3 --tracce sep/   (cartella con drums.wav/bass.wav di demucs: "uno" piu' sicuro)
  python ritmo/griglia.py musica.mp3 --bpm 150 --uno 32.05   (griglia esatta data a mano: tempo + un colpo sicuro, quando quella automatica sbaglia)

griglia.json = {"bpm": 143.6, "battito": 0.418, "battiti": [...], "misure": [...], "energia_misure": [[t, dB], ...]}"""
import argparse, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from audio import carica, scrivi


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("musica"); ap.add_argument("--tracce", help="cartella con drums.wav e bass.wav (demucs)")
    ap.add_argument("--per-misura", type=int, default=4); ap.add_argument("-o", "--out", default="griglia.json")
    ap.add_argument("--bpm", type=float, help="tempo esatto (insieme a --uno)"); ap.add_argument("--uno", type=float, help="secondo di un 'uno' sicuro (es. il colpo del drop)")
    x = ap.parse_args()
    import librosa
    sr = 22050
    y = carica(x.musica, sr, mono=True)
    if x.bpm and x.uno is not None:      # griglia a mano: battiti esatti, il primo "uno" e' quello indicato
        passo = 60 / x.bpm; dur = len(y) / sr
        k0 = -int(x.uno / passo); bt = np.array([x.uno + k * passo for k in range(k0, int((dur - x.uno) / passo) + 1)])
        bt = bt[bt >= 0]; fase = int(round((x.uno - bt[0]) / passo)) % x.per_misura; misure = bt[fase::x.per_misura]
        return fine(x, y, sr, bt, passo, misure, fase)
    _, b = librosa.beat.beat_track(y=y, sr=sr, units="time")
    bt = np.asarray(b, float)
    # bpm dalla mediana degli intervalli (piu' stabile della stima globale)
    passo = float(np.median(np.diff(bt)))
    # "uno" della battuta: la fase in cui cadono i colpi bassi piu' forti (cassa/basso)
    low = y
    if x.tracce:
        p = Path(x.tracce)
        low = sum(carica(p / f, sr, mono=True) for f in ("drums.wav", "bass.wav") if (p / f).exists())
    S = np.abs(librosa.stft(low, n_fft=2048, hop_length=256))
    f = librosa.fft_frequencies(sr=sr, n_fft=2048)
    env = S[(f > 30) & (f < 160)].sum(0)
    tt = librosa.frames_to_time(np.arange(len(env)), sr=sr, hop_length=256)
    forza = np.array([env[(tt >= t - 0.03) & (tt <= t + 0.05)].max(initial=0) for t in bt])
    n = x.per_misura
    fase = int(np.argmax([forza[k::n].mean() for k in range(n)]))
    misure = bt[fase::n]
    return fine(x, y, sr, bt, passo, misure, fase)


def fine(x, y, sr, bt, passo, misure, fase):
    n = x.per_misura
    en = []
    for i, t in enumerate(misure):
        t2 = misure[i + 1] if i + 1 < len(misure) else t + passo * n
        seg = y[int(t * sr):int(t2 * sr)]
        en.append([round(float(t), 3), round(float(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)), 1)])
    out = {"bpm": round(60 / passo, 1), "battito": round(passo, 4), "battiti": [round(float(t), 3) for t in bt],
           "misure": [round(float(t), 3) for t in misure], "energia_misure": en}
    scrivi(x.out, out)
    print(f"{out['bpm']} BPM, {len(bt)} battiti, {len(misure)} battute (uno = fase {fase}) -> {x.out}")


if __name__ == "__main__":
    main()
