# produzione

Gli strumenti che generano le slide di ICT Radar 24.

| File | A cosa serve |
|---|---|
| `render.py` | Genera le slide dal JSON di specifica. Contiene tutte le costanti di marca: colori, font, margini, formati |
| `accenti.py` | Controlla gli accenti nei testi italiani. Separa gli errori certi dalle occorrenze da leggere a mano |
| `anteprima.py` | Compone l'anteprima di un'uscita come pagina unica |

Stanno qui e non altrove per una ragione pratica: una sessione che lavora a
un'uscita clona comunque questo repository, quindi li trova senza doverseli
far passare dalla conversazione.

`render.py` è l'implementazione delle sezioni 4, 5 e 7 del brand book. Non si
toccano colori, font o margini qui dentro senza aggiornare quel documento.
