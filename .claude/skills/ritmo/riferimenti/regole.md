# Le regole del ritmo, con i numeri

Misurate separando in tracce un reel di motion design da 499 commenti (voce, batteria/effetti, basso, resto) e applicate al video RITMO.

| Regola | Numero | Come si controlla |
|---|---|---|
| Livelli | voce in cima; effetti 1-3 dB sotto la voce; musica 8-10 dB sotto | `analizza.py` (livelli per traccia ogni 0,5 s) |
| Un suono per ogni movimento | clic per lettera/parola (20-60 ms), whoosh 50 ms prima di un cambio scena, colpo sul taglio | `partitura.py` R1: taglio senza suono e fuori battito |
| Silenzio prima del taglio importante | 0,35-0,6 s con musica a zero | `partitura.py` R2; `controlla.py` (dB prima del taglio) |
| Basso trattenuto | assente fino alla parola chiave, entra sul suo inizio | `partitura.py` R3 (stampa quando entra il basso) |
| Tagli sul battito dopo il drop | scarto ≤ 60 ms dal battito | `partitura.py` R4 |
| Niente suono forte su una parola che riparte dopo una pausa | volume ≤ 0,35 nei 120 ms prima | `partitura.py` R5 (`sopra_voce: true` se è voluto) |
| Due suoni nello stesso istante = se ne sente uno | distanza ≥ 50 ms | `partitura.py` R6 |
| Apertura | musica piena + immagini forti nei primi 3 s; un effetto che toglie (silenzio) solo dopo ≥ 2,5 s di "pieno" | a occhio + `analizza.py` sul tuo mix |
| Fermi | nessun tratto senza movimento oltre 0,6 s | `controlla.py` |
| Loudness | -14/-16 LUFS, picco ≤ -1 dBFS | `controlla.py` |
| Ogni fotogramma | niente testi sovrapposti, niente fuori zona (9:16: x 60-1020, y 200-1520), niente tratti senza testo oltre 0,3 s senza una ragione visiva | `controlla-pagina.mjs` |
