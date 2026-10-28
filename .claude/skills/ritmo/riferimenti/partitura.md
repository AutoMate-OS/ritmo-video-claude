# Formato della partitura (partitura.json)

```json
{
 "voce": "voce.wav", "parole": "parole.json", "durata": {"dopo_voce": 2.2}, "suoni": "suoni",
 "musica": {
  "griglia": "griglia.json",
  "tracce": {"armonia": "tracce/other.wav", "batteria": "tracce/drums.wav", "basso": "tracce/bass.wav"},
  "segmenti": [
   {"da": 0, "a": {"parola": "musica", "fine": true}, "aggancio": {"misura": 20, "su": 0.0}},
   {"da": {"parola": "Il", "offset": -0.9}, "a": "fine", "aggancio": {"misura": 20, "su": {"parola": "Adesso"}}}
  ],
  "volume": 0.42, "ducking": 0.4, "fade_out": 1.4
 },
 "automazioni": [
  {"traccia": "basso", "da": 0, "a": {"parola": "Adesso"}, "livello": 0, "rampa": 0.01},
  {"traccia": "*", "da": {"parola": "silenzio", "fine": true}, "a": {"parola": "così"}, "livello": 0, "rampa": 0.08}
 ],
 "eventi": [
  {"id": "cosi", "t": {"parola": "così"}, "suono": "impact-soft-1", "vol": 0.62, "visivo": "taglio", "importante": true, "sopra_voce": true},
  {"id": "clic", "t": 0, "ripeti": {"parole_da": {"parola": "ogni"}, "parole_a": {"parola": "clic"}}, "suono": ["click-sharp", "tap"], "vol": 0.48, "visivo": "parola-cade"},
  {"id": "lettere", "t": 0, "ripeti": {"battiti": 5, "ogni": 1, "da": {"parola": "RITMO", "n": 2}}, "suono": "pop-2", "visivo": "lettera"}
 ]
}
```

## Ancore (il campo `t`, `da`, `a`)
- `{"parola": "così"}` inizio della parola (prima la parola esatta, poi l'inizio di parola); `"n": 2` = la seconda volta che compare; `"fine": true` = fine della parola; `"offset": -0.12` = 0,12 s prima.
- `{"battito_dopo": {...ancora...}, "k": 2}` = il terzo battito dopo l'ancora.
- `{"misura": 20}` = inizio della battuta 20 del brano (dopo l'aggancio).
- `"aggancia": true` = sposta l'ancora sul battito più vicino (entro 0,12 s).
- `0.0` (un numero) solo per l'inizio del video. `"fine"`, `"fine_voce"`.

## Ripetizioni (`ripeti`)
- `{"parole_da": {...}, "parole_a": {...}}` un evento per ogni parola dell'intervallo.
- `{"battiti": 5, "ogni": 1, "da": {...}}` un evento per battito.
- `{"misure": 4, "da": {...}}` un evento per battuta.
- `suono` può essere una lista: si alternano (così lo stesso suono non si sente due volte di fila).

## Campi dell'evento
`id`, `suono` (nome del file in `suoni/` senza estensione), `vol` (0-1), `pan` (-1 sinistra … +1 destra), `dur` (taglia il suono), `visivo` (`taglio`/`stacco` vengono controllati; il resto è un'etichetta per l'animazione), `importante` (vuole il silenzio prima), `sopra_voce` (suono forte voluto su una parola), `muto` (taglio voluto senza suono).

## Cosa esce
- `cue.json`: tutti gli eventi in secondi, segmenti e automazioni della musica, battiti e parole nel tempo del video → `mix.py`, `controlla.py`.
- `tempi.js`: `window.RITMO = {durata, parole, battiti, misure, eventi: {id: [secondi...]}}` → l'animazione.
