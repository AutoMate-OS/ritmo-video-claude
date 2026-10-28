---
name: ritmo
description: Dà ritmo ai video fatti con Claude. Trasforma voce e musica in numeri (tempi di ogni parola, battiti, battute, silenzi), fa scrivere una partitura in cui ogni taglio, suono e animazione è agganciato a una parola o a un battito, fa il mix e controlla il video fotogramma per fotogramma. Usa quando l'utente chiede di montare un video a tempo, sulla musica, "con ritmo", di analizzare il suono di un video di riferimento, o di controllare un video prima di pubblicarlo.
---

# ritmo — il ritmo in numeri

Claude non sente l'audio. Ogni decisione di ritmo va presa su **numeri misurati**, mai a sensazione e mai con secondi scritti a mano. Strumenti in `ritmo/` (lancia ciascuno con `--help`).

## Il metodo (7 passi, in quest'ordine)

1. **Riferimento** (se l'utente ne ha uno): `python ritmo/analizza.py riferimento.mp4 -o analisi/` → leggi `analisi/analisi.md` e `spettro.png` e scrivi la tabella *t · voce · suono · immagine · regola*. Separa sempre le tracce: è il basso che entra, è la batteria che tace, è il silenzio prima del taglio che fanno il ritmo, non le immagini.
2. **Voce**: `python ritmo/tempi.py voce.wav copione.txt --preciso` → `parole.json`. Pause troppo lunghe si accorciano tagliando **solo dentro i silenzi misurati**, mai sulle parole.
3. **Musica**: `python ritmo/griglia.py musica.mp3 --tracce tracce/` → `griglia.json`. Se la griglia automatica sbaglia (pochi battiti, tempo strano), misura un colpo sicuro e dalla a mano: `--bpm 150 --uno 32.05`. Separa la musica in tracce (`python -m demucs -n htdemucs musica.wav`) per poter togliere e rimettere batteria e basso.
4. **Partitura**: scrivi `partitura.json` (formato in `riferimenti/partitura.md`). Ogni evento si aggancia a una parola o a un battito; i `segmenti` permettono di usare lo stesso pezzo di musica due volte (es. il drop all'inizio E sulla parola chiave); le `automazioni` fanno i silenzi e il basso trattenuto. Poi `python ritmo/partitura.py partitura.json` → `cue.json` + `tempi.js` + controlli. Correggi finché i controlli dicono "tutto ok".
5. **Animazione**: l'animazione legge `window.RITMO` da `tempi.js` (parole, battiti, eventi). Scrivila come funzione del tempo (`render(t)` calcola tutto da `t`), così ogni fotogramma è uguale a ogni render. Se usi un canvas, disegna sull'evento `hf-seek` e nascondilo quando non ha niente da disegnare.
6. **Mix**: `python ritmo/mix.py cue.json -o mix.wav` (voce sopra, musica che si abbassa sotto la voce, -14 LUFS).
7. **Controlli prima di dire "fatto"**: `node ritmo/controlla-pagina.mjs index.html` su TUTTI i fotogrammi (deve dire "nessun problema"), render, poi `python ritmo/controlla.py video.mp4 cue.json`. Guarda comunque tutto il video a 10 fotogrammi al secondo: un difetto di 3 fotogrammi non si vede a 4 al secondo.

## Le regole (dettaglio e numeri in `riferimenti/regole.md`)
- Il pezzo più bello della musica va **nei primi 3 secondi**, non a metà: a metà nessuno guarda più.
- **Un suono per ogni cosa che si muove** (clic per una lettera, colpo per un taglio, granuli per un'esplosione).
- **Mezzo secondo di silenzio** prima dei tagli importanti; il taglio cade sul colpo.
- **Il basso è una ricompensa**: entra solo sulla parola chiave.
- Liste a tempo: **una parola = un colpo = un'immagine**. Dopo il drop i tagli cadono sul battito.
- **Ogni fotogramma ha una lettura**: niente elementi vuoti, niente buchi tra una scritta che esce e quella che entra.
- La parola della chiamata all'azione si vede **una volta sola**.
