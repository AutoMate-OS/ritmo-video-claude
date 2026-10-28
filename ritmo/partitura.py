#!/usr/bin/env python3
"""PARTITURA -> CUE: trasforma la partitura scritta da Claude (eventi agganciati a PAROLE e BATTITI, mai a secondi a mano)
in tempi assoluti, controlla le regole del ritmo e scrive:
  cue.json  -> per mix.py (audio) e controlla.py (verifica)
  tempi.js  -> window.RITMO per l'animazione HTML/GSAP: ogni animazione legge i suoi tempi da qui

Uso: python ritmo/partitura.py partitura.json      (formato: vedi .claude/skills/ritmo/riferimenti/partitura.md)"""
import argparse, re, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from audio import leggi, scrivi

norm = lambda w: re.sub(r"[^\w']", "", w.lower().replace("’", "'"))


class Tempi:
    def __init__(self, P, base):
        self.base = base
        self.parole = leggi(base / P["parole"])
        self.fine_voce = self.parole[-1]["e"]
        d = P.get("durata", {"dopo_voce": 2.0})
        self.durata = round(self.fine_voce + d["dopo_voce"], 3) if isinstance(d, dict) else float(d)
        self.offset, self.battiti, self.misure, self.segmenti = 0.0, [], [], []
        M = P.get("musica")
        if M:
            g = leggi(base / M["griglia"])
            self.g = g
            # segmenti: pezzi diversi dello stesso brano, ognuno agganciato a un momento del video (es. il drop all'inizio E su "Adesso")
            segs = M.get("segmenti") or [{"da": 0, "a": "fine", **({"aggancio": M["aggancio"]} if M.get("aggancio") else {"offset": M.get("offset", 0)})}]
            for sg in segs:
                ag = sg.get("aggancio")
                off = round(self.t(ag["su"]) - g["misure"][ag["misura"]], 3) if ag else float(sg.get("offset", 0))
                da, a = self.t(sg.get("da", 0)), self.t(sg.get("a", "fine"))
                self.segmenti.append({"da": da, "a": a, "offset": off})
                self.battiti += [round(b + off, 3) for b in g["battiti"] if da <= b + off < a]
                self.misure += [round(b + off, 3) for b in g["misure"] if da <= b + off < a]
            self.offset = self.segmenti[-1]["offset"]
            self.misure_tutte = [round(b + self.offset, 3) for b in g["misure"]]

    def parola(self, a):
        q, n = norm(a["parola"]), a.get("n", 1)
        for prova in (lambda w: w == q, lambda w: w.startswith(q)):   # prima la parola esatta, poi l'inizio
            hit = [i for i, p in enumerate(self.parole) if prova(norm(p["w"]))]
            if len(hit) >= n:
                return hit[n - 1]
        sys.exit(f"Parola non trovata nel copione: {a}")

    def t(self, a):
        if isinstance(a, (int, float)):
            return float(a)
        if a == "fine":
            return self.durata
        if a == "fine_voce":
            return self.fine_voce
        if "parola" in a:
            p = self.parole[self.parola(a)]
            v = p["e"] if a.get("fine") else p["s"]
        elif "misura" in a:
            v = self.misure_tutte[a["misura"]]
        elif "battito_dopo" in a:
            t0 = self.t(a["battito_dopo"]) - 1e-3
            bs = [b for b in self.battiti if b >= t0]
            v = bs[min(a.get("k", 0), len(bs) - 1)]
        else:
            sys.exit(f"Ancora non valida: {a}")
        v += a.get("offset", 0)
        if a.get("aggancia") and self.battiti:
            b = min(self.battiti, key=lambda x: abs(x - v))
            if abs(b - v) <= 0.12:
                v = b
        return round(v, 3)


def espandi(ev, T):
    r = ev.get("ripeti")
    if not r:
        return [dict(ev, t=T.t(ev["t"]))]
    if "parole_da" in r:
        i0, i1 = T.parola(r["parole_da"]), T.parola(r["parole_a"])
        ts = [T.parole[i]["s"] + r.get("offset", 0) for i in range(i0, i1 + 1)]
    elif "battiti" in r:
        t0 = T.t(r["da"]) - 1e-3
        bs = [b for b in T.battiti if b >= t0]
        ts = bs[: r["battiti"] * r.get("ogni", 1): r.get("ogni", 1)]
    elif "misure" in r:
        t0 = T.t(r["da"]) - 1e-3
        ts = [b for b in T.misure if b >= t0][: r["misure"]]
    elif "ogni" in r:
        t0 = T.t(r["da"]); ts = [t0 + k * r["ogni"] for k in range(r["n"])]
    else:
        sys.exit(f"ripeti non valido: {r}")
    out = []
    for k, t in enumerate(ts):
        e = {x: y for x, y in ev.items() if x != "ripeti"}
        e.update(t=round(t, 3), k=k, id=f"{ev['id']}#{k}")
        if isinstance(ev.get("suono"), list):
            e["suono"] = ev["suono"][k % len(ev["suono"])]
        out.append(e)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("partitura"); ap.add_argument("--out", default=".")
    x = ap.parse_args()
    base = Path(x.partitura).parent
    P = leggi(x.partitura)
    T = Tempi(P, base)
    ev = sorted([e for E in P.get("eventi", []) for e in espandi(E, T)], key=lambda e: e["t"])
    au = [{"traccia": a["traccia"], "da": T.t(a["da"]), "a": T.t(a["a"]), "livello": a["livello"],
           "rampa": a.get("rampa", 0.06)} for a in P.get("automazioni", [])]

    # ---------------- controlli: le regole del ritmo ----------------
    avvisi = []
    def livello(tr, t):
        v = 1.0
        for a in au:
            if a["traccia"] in (tr, "*") and a["da"] <= t < a["a"]:
                v = min(v, a["livello"])
        return v
    tracce = list((P.get("musica") or {}).get("tracce", {}).keys())
    ingresso_pieno = None
    for t in T.battiti:
        if tracce and all(livello(tr, t) >= 0.5 for tr in tracce):
            ingresso_pieno = t; break
    for e in ev:
        if e.get("visivo") in ("taglio", "stacco"):
            if not e.get("suono") and not e.get("muto") and not any(abs(b - e["t"]) < 0.04 for b in T.battiti):
                avvisi.append(f"R1 {e['id']} {e['t']:.2f}s: taglio senza suono e fuori battito (taglio muto)")
            if e.get("importante") and tracce:
                if max(livello(tr, e["t"] - d) for tr in tracce for d in (0.1, 0.2, 0.3)) > 0.2:
                    avvisi.append(f"R2 {e['id']} {e['t']:.2f}s: taglio importante senza ~0,35 s di silenzio della musica prima")
            if ingresso_pieno and e["t"] >= ingresso_pieno - 0.01 and T.battiti:
                d = min(abs(b - e["t"]) for b in T.battiti)
                if d > 0.06:
                    avvisi.append(f"R4 {e['id']} {e['t']:.2f}s: col groove pieno il taglio deve cadere sul battito (scarto {d * 1000:.0f} ms)")
        if e.get("suono") and e.get("vol", 0.5) > 0.35 and not e.get("sopra_voce"):
            for p in T.parole:
                if p["pausa_prima"] >= 0.4 and 0 <= p["s"] - e["t"] <= 0.12:
                    avvisi.append(f"R5 {e['id']} {e['t']:.2f}s: suono forte sopra '{p['w']}' che riparte dopo una pausa (abbassalo o metti sopra_voce:true se voluto)")
    con_suono = [e for e in ev if e.get("suono")]
    for a, b in zip(con_suono, con_suono[1:]):
        if b["t"] - a["t"] < 0.05 and a["id"].split("#")[0] != b["id"].split("#")[0]:
            avvisi.append(f"R6 {a['id']} e {b['id']} a {a['t']:.2f}s: due suoni nello stesso istante, se ne sente uno solo")
    if "basso" in tracce:
        t_b = next((t for t in [x / 100 for x in range(int(T.durata * 100))] if livello("basso", t) >= 0.5), None)
        if t_b is not None:
            p = min(T.parole, key=lambda p: abs(p["s"] - t_b))
            print(f"R3 il basso entra a {t_b:.2f}s (parola piu' vicina: '{p['w']}' a {p['s']:.2f}s)")

    # ---------------- uscita ----------------
    M = P.get("musica") or {}
    cue = {"durata": T.durata, "fine_voce": T.fine_voce, "voce": P["voce"], "voce_volume": P.get("voce_volume", 1.0),
           "musica": {"offset": T.offset, "segmenti": T.segmenti, "tracce": M.get("tracce", {}), "volume": M.get("volume", 0.35),
                      "ducking": M.get("ducking", 0.5), "fade_out": M.get("fade_out", 1.2)} if M else None,
           "suoni": P.get("suoni", "suoni"), "automazioni": au, "eventi": ev,
           "battiti": T.battiti, "misure": T.misure, "parole": T.parole}
    out = Path(x.out)
    scrivi(out / "cue.json", cue)
    js = {"durata": T.durata, "parole": [{"w": p["w"], "s": p["s"], "e": p["e"]} for p in T.parole], "battiti": T.battiti,
          "misure": T.misure, "eventi": {}}
    for e in ev:
        js["eventi"].setdefault(e["id"].split("#")[0], []).append(e["t"])
    (out / "tempi.js").write_text("window.RITMO = " + json.dumps(js, ensure_ascii=False) + ";\n", encoding="utf-8")

    for sg in T.segmenti:
        print(f"segmento musica {sg['da']:.2f}-{sg['a']:.2f}s del video = brano da {sg['da'] - sg['offset']:.2f}s")
    print(f"durata {T.durata}s, musica spostata di {T.offset:+.3f}s, {len(T.battiti)} battiti nel video, {len(ev)} eventi -> cue.json, tempi.js")
    print("\n  t     parola           evento                suono            visivo")
    for e in ev:
        p = max((p for p in T.parole if p["s"] <= e["t"] + 0.02), key=lambda p: p["s"], default={"w": "-"})
        print(f"{e['t']:6.2f}  {p['w'][:15]:<15}  {e['id'][:20]:<20}  {str(e.get('suono') or '-')[:15]:<15}  {e.get('visivo') or '-'}")
    print("\nCONTROLLI:", "tutto ok" if not avvisi else "")
    for a in avvisi:
        print("  -", a)


if __name__ == "__main__":
    main()
