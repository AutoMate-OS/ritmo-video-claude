# Istruzioni per l'agente (Claude, Codex): dai ritmo a un video

Quando l'utente chiede di "dare ritmo", "mettere a tempo", "montare sulla musica" un video, segui la skill `.claude/skills/ritmo/SKILL.md` (metodo in 7 passi, regole in `riferimenti/regole.md`, formato della partitura in `riferimenti/partitura.md`).

1. Controlla che ci siano `python3`, `ffmpeg` e le librerie di `requirements.txt`. Se manca qualcosa, dillo e spiega come installarlo; non installare niente senza il suo ok.
2. Lavora solo nella cartella del progetto dell'utente. Non cancellare e non sovrascrivere i suoi file audio o video: scrivi i risultati in file nuovi.
3. Mai scrivere secondi a mano nella partitura: ogni evento si aggancia a una parola (`tempi.py`) o a un battito (`griglia.py`).
4. Prima di dire "fatto": `partitura.py` senza avvisi, `controlla-pagina.mjs` (se il video è in HTML) senza problemi, `controlla.py` sul video finito. Mostra all'utente cosa dicono.
Regole: niente rete oltre l'installazione delle librerie; niente musica o suoni di cui non conosci la licenza.
