#!/usr/bin/env python3
"""TEMPI DELLA VOCE: quando inizia e finisce ogni parola del copione, al centesimo.
Claude non sente la voce: questi numeri sono il suo orecchio.

Uso:
  python ritmo/tempi.py voce.wav copione.txt            -> parole.json  (faster-whisper, facile da installare)
  python ritmo/tempi.py voce.wav copione.txt --preciso  -> parole.json  (allineamento forzato torchaudio MMS_FA, piu' preciso)

parole.json = [{"w": "Adesso.", "s": 16.58, "e": 17.02, "pausa_prima": 1.31}, ...]  una voce per parola del copione, stesso ordine.
Il testo che esce e' SEMPRE quello del copione (mai quello che "sente" Whisper)."""
import argparse, difflib, re, sys, unicodedata
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from audio import carica, scrivi

norm = lambda w: re.sub(r"[^\w']", "", unicodedata.normalize("NFC", w.lower().replace("’", "'")))


def con_whisper(wav, parole, lingua, modello):
    from faster_whisper import WhisperModel
    a = carica(wav, 16000, mono=True)
    m = WhisperModel(modello, device="auto", compute_type="int8")
    seg, _ = m.transcribe(a, language=lingua, word_timestamps=True, initial_prompt=" ".join(parole[:40]))
    sentite = [(w.start, w.end, norm(w.word)) for s in seg for w in s.words]
    ref = [norm(p) for p in parole]
    out = [None] * len(parole)
    sm = difflib.SequenceMatcher(a=ref, b=[x[2] for x in sentite], autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            s, e, _ = sentite[blk.b + k]
            out[blk.a + k] = [s, e]
    # parole non riconosciute: interpolate tra le vicine (segnalate)
    for i, v in enumerate(out):
        if v is None:
            j = next((k for k in range(i - 1, -1, -1) if out[k]), None)
            k2 = next((k for k in range(i + 1, len(out)) if out[k]), None)
            s = out[j][1] if j is not None else 0.0
            e = out[k2][0] if k2 is not None else s + 0.3
            out[i] = [s, e]
            print(f"  attenzione: '{parole[i]}' non sentita, tempo stimato {s:.2f}s")
    return out


def con_mms(wav, parole):
    import torch, torchaudio
    b = torchaudio.pipelines.MMS_FA
    m = b.get_model(with_star=False)
    d = {c: i for i, c in enumerate(b.get_labels(star=None))}
    a = torch.from_numpy(carica(wav, b.sample_rate, mono=True))[None]
    base = lambda w: "".join(c for c in unicodedata.normalize("NFD", w.lower()) if c in d and c != "-")
    toks = [[d[c] for c in base(w)] or [d["a"]] for w in parole]
    with torch.inference_mode():
        em, _ = m(a)
    em = torch.log_softmax(em, -1)
    al, sc = torchaudio.functional.forced_align(em, torch.tensor([[t for w in toks for t in w]], dtype=torch.int32), blank=0)
    spans = torchaudio.functional.merge_tokens(al[0], sc[0].exp())
    r = a.size(1) / em.size(1) / b.sample_rate
    out, i = [], 0
    for t in toks:
        s = spans[i:i + len(t)]; i += len(t)
        out.append([s[0].start * r, s[-1].end * r])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("voce"); ap.add_argument("copione")
    ap.add_argument("--preciso", action="store_true"); ap.add_argument("--lingua", default="it")
    ap.add_argument("--modello", default="large-v3"); ap.add_argument("-o", "--out", default="parole.json")
    x = ap.parse_args()
    parole = open(x.copione, encoding="utf-8").read().split()
    t = con_mms(x.voce, parole) if x.preciso else con_whisper(x.voce, parole, x.lingua, x.modello)
    res = []
    for i, (w, (s, e)) in enumerate(zip(parole, t)):
        pausa = round(s - t[i - 1][1], 2) if i else round(s, 2)
        res.append({"w": w, "s": round(float(s), 3), "e": round(float(e), 3), "pausa_prima": pausa})
    scrivi(x.out, res)
    pause = [f"{r['w']}({r['pausa_prima']}s)" for r in res if r["pausa_prima"] >= 0.4]
    print(f"{len(res)} parole -> {x.out}. Fine voce {res[-1]['e']:.2f}s. Pause >= 0,4 s prima di: {', '.join(pause) or 'nessuna'}")


if __name__ == "__main__":
    main()
