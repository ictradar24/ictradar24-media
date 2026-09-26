# ictradar24-media

Archivio pubblico delle immagini pubblicate da **ICT Radar 24**.

Il repository esiste per una ragione tecnica: Metricool non accetta file caricati,
accetta URL pubblici. GitHub serve ogni file a un indirizzo stabile tramite
`raw.githubusercontent.com`, senza bisogno di autenticazione e senza scadenza.

## Struttura

```
media/
└── AAAA-MM-GG-rubrica/
    ├── 01-copertina.png
    ├── 02-notizia-1.png
    └── …
```

**La data davanti** ordina cronologicamente e rende ogni cartella univoca: al secondo
numero della stessa rubrica non c'è confusione possibile con il primo.

**Il nome deve essere autoesplicativo.** La cartella deve dire cosa contiene senza
bisogno di contesto esterno.

**Le cartelle vecchie non si cancellano.** Metricool referenzia i file per URL:
eliminarli rompe i post già programmati e quelli già pubblicati.

## Suffissi per rubrica

| Rubrica | Suffisso |
|---|---|
| Radar Quotidiano | `radar` |
| Radar Italia | `italia` |
| Allerta | `allerta` |
| Sul radar | `sulradar` |
| Punto di vista | `puntodivista` |
| Virgolette | `virgolette` |
| Top del mese | `topdelmese` |
| Gartner NBA Edition | `gartner-nba` |
| Sotto il cofano | `cofano` |
| Storie | `storia-HHMM` |

Per le Storie l'ora distingue le scansioni della stessa giornata: `storia-0830`,
`storia-1545`, `storia-1845` nei giorni feriali, `storia-1052` nel weekend.

## Formato dei file

Numerazione a due cifre nell'ordine di pubblicazione, nome descrittivo dopo il trattino.

- Caroselli: PNG 1080 × 1350 px
- Storie: PNG 1080 × 1920 px

**Le immagini non vengono mai compresse.** Un test di riduzione a 32 colori ha prodotto
bande visibili sulla texture degli archi del marchio. I file restano a piena qualità,
tipicamente 50–180 KB ciascuno.

## URL pubblico

```
https://raw.githubusercontent.com/ictradar24/ictradar24-media/main/media/AAAA-MM-GG-rubrica/NN-nome.png
```

---

Le specifiche grafiche e le regole editoriali stanno nei documenti di progetto:
`ICT-Radar-24-Brand-Identity.md` e `ICT-Radar-24-Manuale-Operativo.md`.
