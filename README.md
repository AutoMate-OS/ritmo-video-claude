# Dare ritmo a Claude quando fa i video

Claude anima benissimo, ma **non sente la musica**. Se gli chiedi un video "a tempo", tira a indovinare: tagli che cadono a caso, effetti sopra la voce, il drop della musica a metà quando nessuno guarda più.

Questa cartella gli dà le orecchie: trasforma voce e musica in **numeri** (quando inizia ogni parola, dove cade ogni battito, dove sono i silenzi) e gli fa scrivere una **partitura**: ogni taglio, ogni suono, ogni animazione agganciati a una parola o a un battito, mai a secondi scritti a mano. Poi controlla il risultato fotogramma per fotogramma.

È il metodo con cui abbiamo fatto il video "RITMO" di Automate OS (31,9 secondi, 1080x1920): partitura con 24 eventi (che diventano 50 tra suoni e animazioni), voce, musica divisa in tracce, 35 suoni, tagli misurati entro 26 millesimi di secondo dal punto previsto, 957 fotogrammi controllati uno per uno.

## Come si usa

1. Scarica questo repository (**Code → Download ZIP**, oppure `git clone`).
2. Installa **Python 3.10+**, **FFmpeg** e le librerie: `pip install -r requirements.txt` (per il controllo di ogni fotogramma anche **Node.js** e `npm install`).
3. Apri la cartella con **Claude Code** (o Codex) e scrivi, per esempio: **"Dai ritmo al mio video: voce.wav, musica.mp3, copione.txt"**. Parte la skill `ritmo` (in Codex: `AGENTS.md`).

Se vuoi partire da zero, incolla in Claude il prompt di `prompt.txt`.

## Cosa c'è dentro

```
prompt.txt                     il prompt da incollare in Claude
ritmo/
├── analizza.py      un video di riferimento -> tabella: voce, batteria, basso, resto, tagli, silenzi, spettrogramma
├── tempi.py         la voce -> inizio e fine di ogni parola del copione (al centesimo)
├── griglia.py       la musica -> tempo, battiti, inizio di ogni battuta (anche data a mano: --bpm --uno)
├── partitura.py     la partitura di Claude -> tempi assoluti + controlli delle regole del ritmo + tempi.js per l'animazione
├── mix.py           voce + tracce della musica (silenzi, basso trattenuto, drop) + un suono per ogni evento
├── controlla.py     il video finito: tagli al loro posto, fermi, silenzi veri, loudness
└── controlla-pagina.mjs   ogni fotogramma di un video in HTML: testi sovrapposti, fuori zona, tratti senza testo
esempio/             copione e partitura veri del video RITMO
.claude/skills/ritmo/   la skill: metodo, regole, formato della partitura
```

## Licenza

MIT. Gli effetti sonori e le musiche non sono inclusi: usa i tuoi o librerie con licenza chiara (CC0).
