#!/usr/bin/env python3
import json, re, sys
ERRORI = {
    "piu": "più", "perche": "perché", "poiche": "poiché", "benche": "benché",
    "affinche": "affinché", "giacche": "giacché", "finche": "finché",
    "cioe": "cioè", "gia": "già", "cosi": "così", "puo": "può", "pero": "però",
    "qualita": "qualità", "citta": "città", "societa": "società",
    "novita": "novità", "attivita": "attività", "realta": "realtà",
    "verita": "verità", "identita": "identità", "universita": "università",
    "liberta": "libertà", "velocita": "velocità", "capacita": "capacità",
    "priorita": "priorità", "meta": "metà", "eta": "età", "sara": "sarà",
    "saro": "sarò", "avra": "avrà", "avro": "avrò", "fara": "farà",
    "faro": "farò", "andra": "andrà", "potra": "potrà", "dovra": "dovrà",
    "verra": "verrà", "dara": "darà", "restera": "resterà", "sapra": "saprà",
    "lunedi": "lunedì", "martedi": "martedì", "mercoledi": "mercoledì",
    "giovedi": "giovedì", "venerdi": "venerdì",
    "piu'": "più", "perche'": "perché", "e'": "è", "gia'": "già",
    "cosi'": "così", "puo'": "può", "pero'": "però",
}
AMBIGUE = {"e", "ne", "se", "si", "da", "la", "li", "di", "do", "sta", "sto"}
ECCEZIONI = {"meta"}

def controlla(etichetta, testo):
    errori, ambigue = [], []
    for m in re.finditer(r"[\w']+", testo, re.UNICODE):
        parola = m.group(0); basso = parola.lower()
        if basso in ERRORI:
            ctx = testo[max(0, m.start()-35):m.end()+35].replace("\n", " ")
            nota = " (verifica: potrebbe essere il nome proprio)" if basso in ECCEZIONI else ""
            errori.append((parola, ERRORI[basso], ctx.strip(), nota))
        elif basso in AMBIGUE:
            ctx = testo[max(0, m.start()-30):m.end()+30].replace("\n", " ")
            ambigue.append((parola, ctx.strip()))
    return etichetta, errori, ambigue

def stampa(r):
    te = ta = 0
    for et, errori, ambigue in r:
        te += len(errori); ta += len(ambigue)
        for p, g, ctx, nota in errori:
            print(f"ERRORE  {et}: {p} -> {g}{nota}\n   ...{ctx}...")
    print(f"\nERRORI CERTI: {te}    DA LEGGERE A MANO: {ta}")
    return te, ta

def main():
    arg = sys.argv[1]
    dati = json.load(open(arg, encoding="utf-8"))
    r = []
    def add(k, v):
        if isinstance(v, str): r.append(controlla(k, v))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                if isinstance(x, str): r.append(controlla(f"{k}[{i}]", x))
        elif isinstance(v, dict):
            for kk, vv in v.items(): add(f"{k}/{kk}", vv)
    for k, v in dati.items(): add(k, v)
    e, a = stampa(r)
    sys.exit(1 if e else 0)

if __name__ == "__main__":
    main()
