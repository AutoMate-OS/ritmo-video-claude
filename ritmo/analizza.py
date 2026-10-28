#!/usr/bin/env python3
"""ANALIZZA UN VIDEO DI RIFERIMENTO: cosa succede nel suono, parola per parola e taglio per taglio.
Claude guarda i fotogrammi ma non sente: questo script gli da' l'orecchio.

Uso: python ritmo/analizza.py riferimento.mp4 [-o analisi/] [--senza-tracce] [--senza-voce]
Esce in analisi/:
  tracce/        voce, batteria/effetti, basso, resto (demucs, se installato)
  parole.json    le parole dette con i tempi (faster-whisper, se installato)
  analisi.md     tabella ogni 0,5 s: livello di ogni traccia, parola, taglio visivo + elenco eventi (attacchi, silenzi, ingresso basso)
  spettro.png    spettrogramma di ogni traccia con parole (verticali) e tagli visivi (rossi)
  fogli_NN.png   fotogrammi a 4 al secondo per guardare le immagini
Poi Claude scrive accanto a ogni riga la REGOLA che ne esce (vedi la skill, passo 1)."""
import argparse, subprocess, shutil, sys, re
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from audio import carica, salva, scrivi, db


def tagli_video(video):
    o = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf",
                        "scale=320:-2,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
                        "-f", "null", "-"], capture_output=True, text=True).stdout
    t = np.array([float(x) for x in re.findall(r"pts_time:([\d.]+)", o)])
    y = np.array([float(x) for x in re.findall(r"YAVG=([\d.]+)", o)])
    if not len(y):
        return [], t, y
    s = max(15.0, float(np.percentile(y, 97)))
    return [float(t[i]) for i in range(1, len(y) - 1) if y[i] > s and y[i] >= y[i - 1] and y[i] >= y[i + 1]], t, y


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("-o", "--out", default="analisi")
    ap.add_argument("--senza-tracce", action="store_true"); ap.add_argument("--senza-voce", action="store_true")
    ap.add_argument("--lingua", default=None); ap.add_argument("--modello", default="medium")
    x = ap.parse_args()
    out = Path(x.out); (out / "tracce").mkdir(parents=True, exist_ok=True)
    tutto = carica(x.video, 44100)
    salva(out / "tracce/tutto.wav", tutto, 44100)
    nomi = ["tutto"]
    if not x.senza_tracce:
        try:
            subprocess.run([sys.executable, "-m", "demucs", "-n", "htdemucs", "-o", str(out / "sep"), str(out / "tracce/tutto.wav")],
                           check=True, capture_output=True)
            for k, it in [("vocals", "voce"), ("drums", "batteria"), ("bass", "basso"), ("other", "resto")]:
                shutil.move(str(out / f"sep/htdemucs/tutto/{k}.wav"), str(out / f"tracce/{it}.wav")); nomi.append(it)
            shutil.rmtree(out / "sep", ignore_errors=True)
        except Exception as e:
            print("demucs non disponibile, analizzo solo il mix:", str(e)[:120], "(pip install demucs)")
    sr = 22050
    T = {n: carica(out / f"tracce/{n}.wav", sr, mono=True) for n in nomi}
    parole = []
    if not x.senza_voce:
        try:
            from faster_whisper import WhisperModel
            a = carica(out / f"tracce/{'voce' if 'voce' in T else 'tutto'}.wav", 16000, mono=True)
            seg, info = WhisperModel(x.modello, device="auto", compute_type="int8").transcribe(a, language=x.lingua, word_timestamps=True)
            parole = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for s in seg for w in s.words]
            scrivi(out / "parole.json", parole)
        except Exception as e:
            print("faster-whisper non disponibile, niente parole:", str(e)[:120], "(pip install faster-whisper)")
    tagli, mt, my = tagli_video(x.video)
    import librosa
    dur = len(T["tutto"]) / sr
    res = {"durata": round(dur, 2), "tagli_video": [round(c, 2) for c in tagli]}
    bpm, bt = librosa.beat.beat_track(y=T["tutto"] - T.get("voce", 0) if "voce" in T else T["tutto"], sr=sr, units="time")
    res["bpm_stimato"] = round(float(np.atleast_1d(bpm)[0]), 1)
    att = {}
    for n in nomi[1:] or nomi:
        att[n] = [round(float(t), 2) for t in librosa.onset.onset_detect(y=T[n], sr=sr, units="time", delta=0.25)]
    res["attacchi"] = att
    # silenzi del mix (quasi-silenzi lunghi almeno 0,25 s) e ingresso del basso
    h = int(sr * 0.05); E = np.array([db(T["tutto"][i:i + h]) for i in range(0, len(T["tutto"]) - h, h)])
    ref = np.percentile(E, 80); q = E < ref - 18; sil, i0 = [], None
    for i, v in enumerate(q):
        if v and i0 is None: i0 = i
        if not v and i0 is not None:
            if (i - i0) * 0.05 >= 0.25: sil.append([round(i0 * 0.05, 2), round(i * 0.05, 2)])
            i0 = None
    res["silenzi"] = sil
    if "basso" in T:
        Eb = np.array([db(T["basso"][i:i + h]) for i in range(0, len(T["basso"]) - h, h)])
        on = Eb > np.percentile(Eb, 90) - 12
        res["basso_entra"] = [round(i * 0.05, 2) for i in range(1, len(on)) if on[i] and not on[i - 1]]
    scrivi(out / "analisi.json", res)
    # tabella ogni 0,5 s
    righe = ["| t | " + " | ".join(nomi) + " | parola | taglio |", "|---" * (len(nomi) + 3) + "|"]
    for k in range(int(dur / 0.5) + 1):
        a, b = k * 0.5, k * 0.5 + 0.5
        lv = [f"{db(T[n][int(a * sr):int(b * sr)]):.0f}" for n in nomi]
        pw = " ".join(p["w"] for p in parole if a <= p["s"] < b)
        tg = " ".join(f"{c:.2f}" for c in tagli if a <= c < b)
        righe.append(f"| {a:.1f} | " + " | ".join(lv) + f" | {pw} | {tg} |")
    md = [f"# Analisi ritmo: {Path(x.video).name}", "",
          f"Durata {res['durata']} s · tempo stimato {res['bpm_stimato']} BPM · tagli visivi: {', '.join(map(str, res['tagli_video']))}",
          f"Silenzi del mix: {res['silenzi']}", f"Il basso entra a: {res.get('basso_entra', '-')}", "",
          "Livelli in dB per traccia ogni 0,5 s (piu' vicino a 0 = piu' forte; sotto -50 = assente).", ""] + righe + [
          "", "## Attacchi per traccia (s)"] + [f"- **{n}**: {', '.join(map(str, v))}" for n, v in att.items()] + [
          "", "## Da scrivere (Claude)", "Per ogni momento forte: t · voce · suono · immagine · REGOLA. Poi le 4-6 regole del suono di questo video."]
    (out / "analisi.md").write_text("\n".join(md), encoding="utf-8")
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, librosa.display
        fig, ax = plt.subplots(len(nomi) + 1, 1, figsize=(max(16, dur * 1.4), 3 * (len(nomi) + 1)), sharex=True)
        for i, n in enumerate(nomi):
            S = librosa.amplitude_to_db(np.abs(librosa.stft(T[n], n_fft=2048, hop_length=256)), ref=np.max)
            librosa.display.specshow(S, sr=sr, hop_length=256, x_axis="time", y_axis="log", ax=ax[i], vmin=-70); ax[i].set_title(n, loc="left")
        ax[-1].plot(mt, my, color="k"); ax[-1].set_title("movimento delle immagini (picchi = tagli)", loc="left")
        for a_ in ax:
            for p in parole: a_.axvline(p["s"], color="c", lw=.6, alpha=.7)
            for c in tagli: a_.axvline(c, color="r", lw=1.5, alpha=.7)
        for p in parole: ax[0].text(p["s"], 6000, p["w"], color="w", fontsize=11, rotation=60)
        ax[-1].set_xticks(np.arange(0, dur, 0.5)); plt.tight_layout(); plt.savefig(out / "spettro.png", dpi=60)
    except Exception as e:
        print("spettrogramma saltato:", str(e)[:100], "(pip install matplotlib)")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(x.video), "-vf", "fps=4,scale=360:-2,tile=8x6", "-frames:v", "9",
                    str(out / "fogli_%02d.png")], check=False)
    print(f"fatto -> {out}/analisi.md, spettro.png, fogli_*.png ({len(parole)} parole, {len(tagli)} tagli, silenzi {sil})")


if __name__ == "__main__":
    main()
