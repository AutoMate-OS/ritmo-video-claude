#!/usr/bin/env python3
"""CONTROLLO DEL RITMO sul video finito (prima di dire "fatto"):
  - ogni taglio della partitura c'e' davvero nel video, e a che distanza (ms)
  - tagli nel video che la partitura non prevede (salti non voluti)
  - fermi: tratti senza movimento oltre la soglia
  - silenzio reale prima dei tagli "importanti"
  - loudness e picco
Uso: python ritmo/controlla.py video.mp4 cue.json [--soglia-fermo 0.6]"""
import argparse, subprocess, re, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from audio import carica, leggi, loudness, db


def movimento(video):
    o = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf",
                        "scale=270:-2,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
                        "-f", "null", "-"], capture_output=True, text=True).stdout
    t = [float(x) for x in re.findall(r"pts_time:([\d.]+)", o)]
    y = [float(x) for x in re.findall(r"YAVG=([\d.]+)", o)]
    return np.array(t), np.array(y)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("cue"); ap.add_argument("--soglia-fermo", type=float, default=0.6)
    x = ap.parse_args()
    C = leggi(x.cue)
    t, y = movimento(x.video)
    soglia_taglio = max(12.0, float(np.percentile(y, 97)))
    tagli = [float(t[i]) for i in range(1, len(y) - 1) if y[i] > soglia_taglio and y[i] >= y[i - 1] and y[i] >= y[i + 1]]
    attesi = [e for e in C["eventi"] if e.get("visivo") in ("taglio", "stacco") and e["t"] > 0.05]   # al fotogramma 0 un taglio non si misura
    ko = 0
    print("TAGLI PREVISTI")
    for e in attesi:
        d = min((abs(c - e["t"]) for c in tagli), default=9)
        ok = d <= 0.05
        ko += not ok
        print(f"  {'ok' if ok else 'NO'}  {e['id']:<22} {e['t']:6.2f}s  scarto {d * 1000:4.0f} ms")
    extra = [c for c in tagli if min((abs(c - e["t"]) for e in attesi), default=9) > 0.12]
    print(f"TAGLI NON IN PARTITURA: {len(extra)}", " ".join(f"{c:.2f}" for c in extra[:20]))
    fermi, i0 = [], None
    for ti, yi in zip(t, y):
        if yi < 0.15:
            i0 = ti if i0 is None else i0
        else:
            if i0 is not None and ti - i0 > x.soglia_fermo:
                fermi.append((i0, ti))
            i0 = None
    print(f"FERMI > {x.soglia_fermo}s: {len(fermi)}", " ".join(f"{a:.1f}-{b:.1f}" for a, b in fermi))
    a = carica(x.video, 48000, mono=True)
    print("SILENZIO PRIMA DEI TAGLI IMPORTANTI (dB rispetto alla media)")
    media = db(a)
    for e in attesi:
        if e.get("importante"):
            s = a[int((e["t"] - 0.35) * 48000):int((e["t"] - 0.03) * 48000)]
            # tolta la voce: conta solo se la voce in quel tratto tace
            print(f"  {e['id']:<22} {db(s) - media:+5.1f} dB")
    L = loudness(x.video)
    print(f"LOUDNESS {L['lufs']} LUFS (social: -14/-16), picco {L['picco']} dBFS (max -1)")
    print("ESITO:", "ok" if ko == 0 and not fermi else f"{ko} tagli fuori posto, {len(fermi)} fermi: guarda i fotogrammi")


if __name__ == "__main__":
    main()
