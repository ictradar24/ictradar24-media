#!/usr/bin/env python3
"""
ICT RADAR 24 — Renderer delle slide
====================================
Genera caroselli e storie nel sistema visivo «Carta e Segnale», in vigore dal
13 ottobre 2026 (brand book §4, §5, §6, §7).

USO
    python3 render.py contenuto.json

Il JSON descrive le slide; questo file contiene tutte le costanti di marca.
Non modificare colori, font o margini qui dentro senza aggiornare il brand book.

DIPENDENZE: Pillow con raqm (per la crenatura). Font in
/mnt/skills/examples/canvas-design/canvas-fonts/

LE REGOLE IN BREVE
- Un colore solo, Arancio Segnale, su un fondo di Carta: il dato grande, il
  folio, la riga Italia e il marchio. Tutto il resto è Inchiostro.
- Il campo dice che cosa fa la pagina: Carta = riportiamo un fatto; Inchiostro
  = interpretiamo (perché conta, famiglia Voce); Arancio pieno = parla la
  testata (chiusura «segui») o non si può aspettare (copertina dell'Allerta).
- La rubrica si riconosce dalla linguetta e dal filetto di testa: semplice per
  il Radar, riga arancio da 12 px per l'Italia, doppio per Gartner NBA Edition,
  tratteggiato per Sotto il cofano, sottile su Inchiostro per la famiglia Voce.
- Il marchio sta su ogni slide, in basso a destra, e il blip ha quattro
  posizioni fisse: fuori in copertina, rilevato sulle notizie, vicino sul
  perché conta, al centro sulla chiusura.
"""

import json, os, re, sys
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────────────────────
# COSTANTI DI MARCA — brand book §4 (colore) e §5 (tipografia)
# ─────────────────────────────────────────────────────────────

FONTDIR = "/mnt/skills/examples/canvas-design/canvas-fonts/"
TESTATA = FONTDIR + "Gloock-Regular.ttf"        # titoli, numeri, logotipo
TESTO   = FONTDIR + "WorkSans-Regular.ttf"      # corpo, sommario, fonti
TESTO_B = FONTDIR + "WorkSans-Bold.ttf"
TAB     = FONTDIR + "BigShoulders-Bold.ttf"     # linguette, folio, tabellone
TAB_R   = FONTDIR + "BigShoulders-Regular.ttf"  # date, criteri, metadati

CARTA   = (243, 238, 227)   # #F3EEE3  il fondo dei fatti
INK     = (23, 21, 15)      # #17150F  testo; il fondo della voce
SEG     = (233, 83, 14)     # #E9530E  Arancio Segnale, l'unico accento
PIOMBO  = (110, 104, 93)    # #6E685D  testo secondario su Carta
FILO    = (207, 200, 186)   # #CFC8BA  filetti su Carta
CARTA_2 = (185, 178, 164)   # #B9B2A4  testo secondario su Inchiostro
FILO_2  = (58, 54, 46)      # #3A362E  filetti su Inchiostro

# Rubriche — brand book §3 bis: campo, filetto, linguetta, nome in linguetta
RUBRICHE = {
    "radar":        dict(campo="carta", filetto="semplice", piena=True,  nome="Radar"),
    "italia":       dict(campo="carta", filetto="riga",     piena=True,  nome="Italia"),
    "allerta":      dict(campo="carta", filetto="semplice", piena=True,  nome="Allerta"),
    "segnalato":    dict(campo="carta", filetto="semplice", piena=True,  nome="Segnalato da voi"),
    "gartner":      dict(campo="carta", filetto="doppio",   piena=True,  nome="Gartner NBA Edition"),
    "cofano":       dict(campo="carta", filetto="tratteggiato", piena=True, nome="Sotto il cofano"),
    "sulradar":     dict(campo="ink",   filetto="sottile",  piena=False, nome="Sul radar"),
    "puntodivista": dict(campo="ink",   filetto="sottile",  piena=False, nome="Punto di vista"),
    "virgolette":   dict(campo="ink",   filetto="sottile",  piena=False, nome="Virgolette"),
    "topdelmese":   dict(campo="ink",   filetto="sottile",  piena=False, nome="Top del mese"),
}
# nome lungo in copertina, dove c'è spazio
NOME_COPERTINA = {"radar": "Radar quotidiano", "italia": "Radar Italia"}

# Formati — brand book §7. Unità logiche su 1080 di larghezza.
POST   = dict(W=1080, H=1350, ML=90, MT=120, MB=140)
STORIA = dict(W=1080, H=1920, ML=90, MT=300, MB=360)

# Risoluzione del file finale: il doppio delle unità logiche (dal 13 ottobre 2026)
USCITA = 2
SS = 2 * USCITA  # si disegna a 4x e si riduce a 2x, per bordi netti

# Le quattro posizioni del blip, su un marchio di lato 100 (brand book §5)
BLIP = {"fuori": (98, 2), "rilevato": (69, 31), "vicino": (60, 40), "centro": (50, 50)}


# ─────────────────────────────────────────────────────────────
# PRIMITIVE
# ─────────────────────────────────────────────────────────────

def f(path, size):
    return ImageFont.truetype(path, int(size * SS))


def mix(colore, fondo, alpha):
    return tuple(int(colore[k] * alpha + fondo[k] * (1 - alpha)) for k in range(3))


def canvas(fmt, campo):
    img = Image.new("RGB", (fmt["W"] * SS, fmt["H"] * SS), campo)
    return img, ImageDraw.Draw(img)


def wrap(d, testo, font, max_w):
    righe, cur = [], ""
    for w in testo.split():
        prova = (cur + " " + w).strip()
        if d.textlength(prova, font=font) <= max_w * SS:
            cur = prova
        else:
            if cur:
                righe.append(cur)
            cur = w
    if cur:
        righe.append(cur)
    return righe


def blocco(d, x, y, testo, font, fill, interlinea, max_w):
    """Scrive un paragrafo dalla y in alto; restituisce la y successiva (unità logiche)."""
    for riga in wrap(d, testo, font, max_w):
        d.text((x * SS, y * SS), riga, font=font, fill=fill)
        y += interlinea
    return y


def altezza(d, testo, font, interlinea, max_w):
    return len(wrap(d, testo, font, max_w)) * interlinea


def adatta(d, testo, path, corpi, interlinea_rel, max_w, max_h):
    """Sceglie il corpo più grande, fra quelli dati, con cui il testo sta in max_h."""
    for c in corpi:
        inter = c * interlinea_rel
        if altezza(d, testo, f(path, c), inter, max_w) <= max_h:
            return c, inter
    c = corpi[-1]
    return c, c * interlinea_rel


def spaziato(d, x, y, testo, font, fill, tracking, anchor="ls"):
    """Testo con spaziatura fra lettere (per Big Shoulders). x,y in unità logiche; restituisce la larghezza logica."""
    px = x * SS
    for ch in testo:
        d.text((px, y * SS), ch, font=font, fill=fill, anchor=anchor)
        px += d.textlength(ch, font=font) + tracking * SS
    return (px - tracking * SS) / SS - x


def larghezza_spaziata(d, testo, font, tracking):
    return (sum(d.textlength(ch, font=font) for ch in testo) + tracking * SS * (len(testo) - 1)) / SS


def linguetta(d, x, y, testo, campo, piena=True, arancio=False):
    """Il rettangolo con il nome della rubrica. y è il bordo superiore; alta 44. Restituisce la larghezza."""
    t = testo.upper()
    fnt = f(TAB, 30)
    larg = larghezza_spaziata(d, t, fnt, 3)
    x0, y0, x1, y1 = x * SS, y * SS, (x + larg + 34) * SS, (y + 44) * SS
    if piena:
        fondo = SEG if arancio else (CARTA if campo == INK else INK)
        colore_testo = CARTA if (arancio or campo != INK) else INK
        d.rectangle([x0, y0, x1, y1], fill=fondo)
    else:
        bordo = CARTA if campo == INK else INK
        colore_testo = bordo
        d.rectangle([x0, y0, x1, y1], outline=bordo, width=3 * SS)
    spaziato(d, x + 18, y + 33, t, fnt, colore_testo, 3)
    return larg + 34


def folio(d, fmt, n, tot, campo, y=None):
    """«02 / 07» a destra: il numero corrente in arancio, il totale in piombo."""
    if y is None:
        y = fmt["MT"] + 36
    fb, fr = f(TAB, 34), f(TAB_R, 34)
    a, b = f"{n:02d}", f" / {tot:02d}"
    la, lb = d.textlength(a, font=fb) / SS, d.textlength(b, font=fr) / SS
    x = fmt["W"] - fmt["ML"] - la - lb
    d.text((x * SS, y * SS), a, font=fb, fill=SEG, anchor="ls")
    d.text(((x + la) * SS, y * SS), b, font=fr,
           fill=(CARTA_2 if campo == INK else PIOMBO), anchor="ls")


def filetto(d, fmt, y, tipo, campo):
    """Il filetto di testa sotto l'intestazione; restituisce la y sotto il filetto."""
    x0, x1 = fmt["ML"] * SS, (fmt["W"] - fmt["ML"]) * SS
    ink = CARTA if campo == INK else INK
    if tipo == "riga":
        d.rectangle([x0, y * SS, x1, (y + 12) * SS], fill=SEG); return y + 12
    if tipo == "doppio":
        d.rectangle([x0, y * SS, x1, (y + 3) * SS], fill=ink)
        d.rectangle([x0, (y + 9) * SS, x1, (y + 12) * SS], fill=ink); return y + 12
    if tipo == "tratteggiato":
        passo, tratto = 24 * SS, 14 * SS
        px = x0
        while px < x1:
            d.rectangle([px, y * SS, min(px + tratto, x1), (y + 3) * SS], fill=ink); px += passo
        return y + 3
    if tipo == "sottile":
        d.rectangle([x0, y * SS, x1, (y + 2) * SS], fill=FILO_2 if campo == INK else FILO); return y + 2
    d.rectangle([x0, y * SS, x1, (y + 3) * SS], fill=ink); return y + 3


def marchio(d, x, y, lato, colore, fondo, blip="rilevato"):
    """Il quadrante: ghiera pesante, anello interno sottile, blip. (x,y) angolo in alto a sinistra, unità logiche."""
    s = lato / 100.0
    cx, cy = (x + 50 * s) * SS, (y + 50 * s) * SS
    r1, w1 = 44 * s * SS, 11 * s * SS
    r2, w2 = 22 * s * SS, 3.5 * s * SS
    d.ellipse([cx - r1, cy - r1, cx + r1, cy + r1], outline=colore, width=int(round(w1)))
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], outline=mix(colore, fondo, 0.7), width=int(round(w2)))
    bx, by = BLIP.get(blip, BLIP["rilevato"])
    rb = (10.5 if blip == "centro" else 9) * s * SS
    px, py = (x + bx * s) * SS, (y + by * s) * SS
    d.ellipse([px - rb, py - rb, px + rb, py + rb], fill=colore)


def marchio_angolo(d, fmt, campo, blip, lato=84):
    """Il marchio in basso a destra, sopra il margine di sicurezza."""
    colore = INK if campo == SEG else SEG
    x = fmt["W"] - fmt["ML"] - lato
    y = fmt["H"] - fmt["MB"] - lato
    marchio(d, x, y, lato, colore, campo, blip)


def piede(d, fmt, campo, blip, testo=None, etichetta=None, destra=None):
    """Filetto sottile, riga di piede a sinistra (fonte, data, nota), marchio a destra."""
    y_f = fmt["H"] - fmt["MB"] - 108
    d.rectangle([fmt["ML"] * SS, y_f * SS, (fmt["W"] - fmt["ML"]) * SS, (y_f + 2) * SS],
                fill=(FILO_2 if campo == INK else (mix(INK, SEG, 0.35) if campo == SEG else FILO)))
    marchio_angolo(d, fmt, campo, blip)
    if testo:
        col = CARTA_2 if campo == INK else (INK if campo == SEG else PIOMBO)
        fnt = f(TESTO, 25)
        maxw = fmt["W"] - fmt["ML"] * 2 - 120
        righe = wrap(d, testo, fnt, maxw - (90 if etichetta else 0))
        y = fmt["H"] - fmt["MB"] - 10 - 32 * len(righe)
        if etichetta:
            fe = f(TESTO_B, 25)
            d.text((fmt["ML"] * SS, (y + 25) * SS), etichetta, font=fe, fill=(CARTA if campo == INK else INK), anchor="ls")
            lx = fmt["ML"] + d.textlength(etichetta, font=fe) / SS + 10
        else:
            lx = fmt["ML"]
        for i, r in enumerate(righe):
            d.text(((lx if i == 0 else fmt["ML"]) * SS, (y + 25) * SS), r, font=fnt, fill=col, anchor="ls")
            y += 32
    if destra:
        spaziato_dx(d, fmt["W"] - fmt["ML"] - 84 - 30, fmt["H"] - fmt["MB"] - 14, destra.upper(), f(TAB, 30), INK if campo == SEG else (CARTA if campo == INK else INK), 3)


def spaziato_dx(d, x_destro, y, testo, font, fill, tracking):
    larg = larghezza_spaziata(d, testo, font, tracking)
    spaziato(d, x_destro - larg, y, testo, font, fill, tracking)


def testata(d, fmt, campo, y_base, corpo=66):
    """Il logotipo «ICT Radar 24» in Gloock, dalla sinistra, sulla linea di base y_base."""
    fnt = f(TESTATA, corpo)
    x = fmt["ML"]
    col = CARTA if campo in (INK, SEG) else INK
    d.text((x * SS, y_base * SS), "ICT Radar ", font=fnt, fill=col, anchor="ls")
    x += d.textlength("ICT Radar ", font=fnt) / SS
    d.text((x * SS, y_base * SS), "24", font=fnt, fill=(CARTA if campo == SEG else SEG), anchor="ls")


def data_destra(d, fmt, campo, y_base, testo):
    fnt = f(TAB_R, 30)
    col = CARTA if campo == SEG else (CARTA_2 if campo == INK else PIOMBO)
    spaziato_dx(d, fmt["W"] - fmt["ML"], y_base, testo.upper(), fnt, col, 2.4)


def intestazione(d, fmt, rub, s, n, tot, campo):
    """Linguetta (+ eventuale tema) a sinistra, folio a destra, filetto. Restituisce la y del corpo."""
    nome = rub["nome"]
    arancio = rub is RUBRICHE["italia"]
    larg = linguetta(d, fmt["ML"], fmt["MT"], nome, campo, rub["piena"], arancio)
    et = (s.get("etichetta") or "").strip()
    # l'etichetta della specifica è un tema («LEGGE DI BILANCIO») o una numerazione («01 / 06»):
    # la numerazione la porta il folio; il tema va accanto alla linguetta
    if et and not re.match(r"^\d+\s*/\s*\d+$", et) and et.upper() != nome.upper():
        spaziato(d, fmt["ML"] + larg + 22, fmt["MT"] + 33, et.upper(), f(TAB_R, 30),
                 CARTA_2 if campo == INK else PIOMBO, 2.4)
    if n:
        folio(d, fmt, n, tot, campo)
    y = filetto(d, fmt, fmt["MT"] + 44 + 18, rub["filetto"], campo)
    return y + 44


def salva(img, fmt, percorso):
    img.resize((fmt["W"] * USCITA, fmt["H"] * USCITA), Image.LANCZOS).save(
        percorso, "PNG", optimize=True)


def elenco_voci(voci):
    """Accetta ["testo", ...] oppure [[n, "testo"], ...]. Senza numero, numera da 3: la
    slide 1 è la copertina e la 2 è la notizia dell'hook, le altre vengono dopo."""
    out = []
    for i, v in enumerate(voci):
        if isinstance(v, (list, tuple)):
            out.append((int(v[0]), str(v[1])))
        else:
            out.append((i + 3, str(v)))
    return out


# ─────────────────────────────────────────────────────────────
# TIPI DI SLIDE — brand book §7 (anatomia del carosello)
# ─────────────────────────────────────────────────────────────

def slide_copertina(s, fmt, rub, n, tot, chiave):
    campo = INK if rub["campo"] == "ink" else CARTA
    if campo == INK:
        return slide_voce(s, fmt, rub, n, tot, chiave)
    if chiave == "allerta":
        campo = SEG
    img, d = canvas(fmt, campo)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    fascia = chiave == "italia"
    if fascia:
        d.rectangle([0, 0, fmt["W"] * SS, 200 * SS], fill=SEG)
        testata(d, fmt, SEG, 164)
        if s.get("piede"):
            data_destra(d, fmt, SEG, 164, s["piede"])
        y = 200 + 56
    else:
        testata(d, fmt, campo, 164)
        if s.get("piede"):
            data_destra(d, fmt, campo, 164, s["piede"])
        y = filetto(d, fmt, 186, "semplice", campo) + 44
    # linguetta e folio
    # «linguetta» nella specifica sostituisce il nome della rubrica solo in copertina
    # (Gartner: «Gartner® NBA Edition», prima menzione con il ® della policy di Gartner)
    nome = s.get("linguetta") or NOME_COPERTINA.get(chiave, rub["nome"])
    linguetta(d, ml, y, nome, campo, True, fascia)
    if n:
        folio(d, fmt, n, tot, campo, y + 36)
    y += 44 + 34
    # il blocco in basso: «E poi» (o il tabellone) e il piede
    y_piede = fmt["H"] - fmt["MB"] - 108
    voci = s.get("epoi") or []
    tabellone = s.get("tabellone") or []
    righe_basso = []
    if tabellone:
        righe_basso = [(str(p).upper(), str(v)) for p, v in tabellone]
    elif voci:
        righe_basso = [(f"{k:02d}", t) for k, t in elenco_voci(voci)]
    fnt_voce = f(TESTO, 30)
    h_basso = 0
    if righe_basso:
        # stessa larghezza e stessi passi del disegno qui sotto (rientro 300 per il tabellone,
        # 64 per «E poi»): con la stima a maxw - 80 una voce su due righe sforava nel piede
        rientro = 300 if tabellone else 64
        h_basso = 42 + sum(12 + 2 + 38 * max(1, len(wrap(d, t, fnt_voce, maxw - rientro))) + 8 for _, t in righe_basso) + 2
    limite = y_piede - 30 - h_basso
    corpi = [s.get("corpo_hook")] if s.get("corpo_hook") else [92, 86, 80, 74, 68, 62]
    c, inter = adatta(d, s["hook"], TESTATA, corpi, 1.03, maxw, limite - y - 40)
    col_hook = INK
    y = blocco(d, ml, y, s["hook"], f(TESTATA, c), col_hook, inter, maxw)
    if not righe_basso and s.get("sottotitolo"):
        c2, inter2 = adatta(d, s["sottotitolo"], TESTO, [36, 33, 30], 1.4, maxw, limite - y - 30)
        blocco(d, ml, y + 30, s["sottotitolo"], f(TESTO, c2), INK if campo == SEG else PIOMBO, inter2, maxw)
    if righe_basso:
        # il sommario sta al piede; se fra hook e sommario resta un vuoto grande, sale sotto l'hook
        yy = y_piede - 30 - h_basso
        if yy - y > 130:
            yy = y + 130
        spaziato(d, ml, yy + 28, "IL TABELLONE" if tabellone else "E POI", f(TAB, 28), SEG if campo != SEG else INK, 3)
        yy += 42
        fk = f(TAB, 30 if tabellone else 34)
        for k, t in righe_basso:
            d.rectangle([ml * SS, yy * SS, (fmt["W"] - ml) * SS, (yy + 2) * SS], fill=FILO if campo != SEG else mix(INK, SEG, .35))
            yy += 12
            spaziato(d, ml, yy + 30, k, fk, SEG if campo != SEG else INK, 2)
            yy = blocco(d, ml + (300 if tabellone else 64), yy + 2, t, fnt_voce, INK, 38, maxw - (300 if tabellone else 64)) + 8
        d.rectangle([ml * SS, yy * SS, (fmt["W"] - ml) * SS, (yy + 2) * SS], fill=FILO if campo != SEG else mix(INK, SEG, .35))
    piede(d, fmt, campo, "fuori", destra=None)
    spaziato(d, ml, fmt["H"] - fmt["MB"] - 14,
             ("EDIZIONE DELLE 17 · SFOGLIA →" if chiave == "italia" else "SFOGLIA →"),
             f(TAB, 30), INK, 3)
    return img


def slide_voce(s, fmt, rub, n, tot, chiave):
    """Famiglia Voce (Virgolette, Sul radar, Punto di vista, Top del mese): campo Inchiostro, linguetta vuota."""
    img, d = canvas(fmt, INK)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    et = s.get("etichetta") or rub["nome"]
    linguetta(d, ml, fmt["MT"], et, INK, piena=False)
    if n:
        folio(d, fmt, n, tot, INK)
    y = filetto(d, fmt, fmt["MT"] + 44 + 18, "sottile", INK) + 44
    y_piede = fmt["H"] - fmt["MB"] - 108
    citazione = chiave == "virgolette" and et.upper() == "VIRGOLETTE"
    if citazione:
        # le virgolette grandi, in Carta al 22 per cento, sopra la frase
        d.text((ml * SS - 20 * SS, (y + 150) * SS), "«", font=f(TESTATA, 440), fill=mix(CARTA, INK, 0.22), anchor="ls")
        y += 150
    sotto = s.get("sottotitolo")
    h_sotto = 0
    fs = f(TESTO, 34)
    if sotto:
        h_sotto = 40 + altezza(d, sotto, fs, 48, maxw - 100)
    corpi = [s.get("corpo_hook")] if s.get("corpo_hook") else [72, 66, 60, 54, 48]
    c, inter = adatta(d, s["hook"], TESTATA, corpi, 1.12, maxw, y_piede - 30 - h_sotto - y)
    y = blocco(d, ml, y, s["hook"], f(TESTATA, c), CARTA, inter, maxw)
    if sotto:
        blocco(d, ml, y + 40, sotto, fs, CARTA_2, 48, maxw - 100)
    piede(d, fmt, INK, "rilevato", testo=s.get("piede"))
    return img


def slide_notizia(s, fmt, rub, n, tot, chiave):
    campo = INK if rub["campo"] == "ink" else CARTA
    img, d = canvas(fmt, campo)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    y = intestazione(d, fmt, rub, s, n, tot, campo)
    y_piede = fmt["H"] - fmt["MB"] - 108
    col_t = CARTA if campo == INK else INK
    if s.get("dato"):
        dato = s["dato"]
        c_d = 176 if len(dato) <= 5 else (150 if len(dato) <= 8 else 118)
        fd = f(TESTATA, c_d)
        h_d = c_d * 0.92 + 34 + 4
        fc = f(TESTO, 38); inter_c = 54
        h_c = altezza(d, s["corpo"], fc, inter_c, maxw) + 30
        c, inter = adatta(d, s["titolo"], TESTATA, [64, 58, 52, 46], 1.06, maxw, y_piede - 24 - y - h_d - h_c)
        y = blocco(d, ml, y, s["titolo"], f(TESTATA, c), col_t, inter, maxw)
        y += 34
        d.text(((ml - 4) * SS, (y + c_d * 0.74) * SS), dato, font=fd, fill=SEG, anchor="ls")
        y += c_d * 0.92 + 4
        blocco(d, ml, y + 30, s["corpo"], fc, col_t, inter_c, maxw)
    else:
        fc = f(TESTO, 42); inter_c = 59
        h_c = altezza(d, s["corpo"], fc, inter_c, maxw) + 44
        c, inter = adatta(d, s["titolo"], TESTATA, [76, 70, 64, 58, 52], 1.05, maxw, y_piede - 24 - y - h_c)
        y = blocco(d, ml, y, s["titolo"], f(TESTATA, c), col_t, inter, maxw)
        blocco(d, ml, y + 44, s["corpo"], fc, col_t, inter_c, maxw)
    fonte = s.get("fonte", "")
    etich = None
    m = re.match(r"^(Fonti?|Fonte)\s*:\s*(.*)$", fonte, re.I)
    if m:
        etich, fonte = m.group(1), m.group(2)
    elif fonte:
        etich = "Fonti" if (";" in fonte or " e " in fonte) else "Fonte"
    piede(d, fmt, campo, "rilevato", testo=fonte or None, etichetta=etich)
    return img


def slide_perche(s, fmt, rub, n, tot, chiave):
    """Il «perché conta»: campo Inchiostro, la voce della redazione dentro un pezzo di cronaca."""
    img, d = canvas(fmt, INK)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    linguetta(d, ml, fmt["MT"], "Perché conta", INK, piena=True)
    if n:
        folio(d, fmt, n, tot, INK)
    y = filetto(d, fmt, fmt["MT"] + 44 + 18, "semplice", INK) + 44
    y_piede = fmt["H"] - fmt["MB"] - 108
    c, inter = adatta(d, s["testo"], TESTATA, [70, 64, 58, 52, 46], 1.1, maxw, y_piede - 30 - y)
    blocco(d, ml, y, s["testo"], f(TESTATA, c), CARTA, inter, maxw)
    piede(d, fmt, INK, "vicino", testo="La lettura della redazione, a partire dai fatti qui sopra.")
    return img


def slide_elenco(s, fmt, rub, n, tot, chiave):
    """Voci con pallino: pieno per la famiglia Rilevamento, vuoto per la Voce."""
    campo = INK if rub["campo"] == "ink" else CARTA
    img, d = canvas(fmt, campo)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    y = intestazione(d, fmt, rub, s, n, tot, campo)
    col_t = CARTA if campo == INK else INK
    col_s = CARTA_2 if campo == INK else PIOMBO
    if s.get("titolo"):
        y = blocco(d, ml, y, s["titolo"], f(TESTATA, 72), col_t, 78, maxw)
        if s.get("sottotitolo"):
            spaziato(d, ml, y + 30, s["sottotitolo"].upper(), f(TAB_R, 28), col_s, 2.4)
            y += 50
        y += 30
    for voce in s["voci"]:
        cx, cy = ml * SS, (y + 16) * SS
        if voce.get("vuoto"):
            d.ellipse([cx, cy, cx + 20 * SS, cy + 20 * SS], outline=SEG, width=int(3 * SS))
        else:
            d.ellipse([cx, cy, cx + 20 * SS, cy + 20 * SS], fill=SEG)
        d.text(((ml + 48) * SS, y * SS), voce["nome"], font=f(TESTATA, 46), fill=col_t)
        if voce.get("desc"):
            d.text(((ml + 48) * SS, (y + 60) * SS), voce["desc"], font=f(TESTO, 30), fill=col_s)
            y += 140
        else:
            y += 100
    piede(d, fmt, campo, "rilevato", testo=s.get("piede"))
    return img


def slide_premio(s, fmt, rub, n, tot, chiave):
    """Gartner NBA Edition: il tabellone. Nome del premio in Big Shoulders, vincitore in Gloock arancio."""
    img, d = canvas(fmt, CARTA)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    y = intestazione(d, fmt, rub, s, n, tot, CARTA)
    premio = s["premio"].upper()
    c = 150 if len(premio) <= 12 else 104
    fp = f(TAB, c)
    righe = wrap(d, premio, fp, maxw)
    for r in righe:
        d.text((ml * SS, (y + c * 0.9) * SS), r, font=fp, fill=INK, anchor="ls")
        y += c * 0.9 + 6
    spaziato(d, ml, y + 36, s["criterio"].upper(), f(TAB_R, 32), PIOMBO, 2.6)
    y += 36 + 54
    fv = f(TESTATA, 150)
    for r in wrap(d, s["vincitore"], fv, maxw):
        d.text((ml * SS, (y + 150 * 0.75) * SS), r, font=fv, fill=SEG, anchor="ls")
        y += 150 * 0.95
    if s.get("nota"):
        blocco(d, ml, y + 34, s["nota"], f(TESTO, 38), INK, 54, maxw - 100)
    piede(d, fmt, CARTA, "rilevato", testo=s.get("fonte"), etichetta=("Fonte" if s.get("fonte") else None))
    return img


def slide_nonassegnati(s, fmt, rub, n, tot, chiave):
    img, d = canvas(fmt, CARTA)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    y = intestazione(d, fmt, rub, s, n, tot, CARTA)
    y = blocco(d, ml, y, s["titolo"], f(TESTATA, 64), INK, 68, maxw)
    y += 40
    for v in s["voci"]:
        d.rectangle([ml * SS, y * SS, (fmt["W"] - ml) * SS, (y + 2) * SS], fill=FILO)
        y += 22
        d.text((ml * SS, (y + 56 * 0.9) * SS), v["premio"].upper(), font=f(TAB, 56), fill=INK, anchor="ls")
        y += 56 * 0.9 + 10
        spaziato(d, ml, y + 20, v["criterio"].upper(), f(TAB_R, 26), PIOMBO, 2.2)
        y += 40
        y = blocco(d, ml, y, v["motivo"], f(TESTO, 32), INK, 44, maxw) + 26
    piede(d, fmt, CARTA, "rilevato", testo=s.get("fonte"))
    return img


def slide_quintetto(s, fmt, rub, n, tot, chiave):
    img, d = canvas(fmt, CARTA)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    y = intestazione(d, fmt, rub, s, n, tot, CARTA)
    d.text((ml * SS, (y + 104 * 0.9) * SS), s["premio"].upper(), font=f(TAB, 104), fill=INK, anchor="ls")
    y += 104 * 0.9 + 6
    spaziato(d, ml, y + 30, s["criterio"].upper(), f(TAB_R, 30), PIOMBO, 2.4)
    y += 30 + 36
    fnome, fq = f(TESTATA, 58), f(TAB, 30)
    for v in s["voci"]:
        d.rectangle([ml * SS, y * SS, (fmt["W"] - ml) * SS, (y + 2) * SS], fill=FILO)
        base = y + 16 + 58 * 0.75
        d.text((ml * SS, base * SS), v["nome"], font=fnome, fill=INK, anchor="ls")
        spaziato_dx(d, fmt["W"] - ml, base, v["quadrante"].upper(), fq, SEG, 3)
        y += 16 + 58 * 0.9 + 12
    d.rectangle([ml * SS, y * SS, (fmt["W"] - ml) * SS, (y + 2) * SS], fill=FILO)
    if s.get("nota"):
        blocco(d, ml, y + 26, s["nota"], f(TESTO, 30), INK, 42, maxw)
    piede(d, fmt, CARTA, "rilevato", testo=s.get("fonte"))
    return img


def slide_fonte(s, fmt, rub, n, tot, chiave):
    """Chiusura di Gartner NBA Edition: fonte, natura editoriale, disclaimer obbligatorio."""
    img, d = canvas(fmt, CARTA)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    s2 = dict(s); s2["etichetta"] = s.get("etichetta") or rub["nome"]
    y = intestazione(d, fmt, rub, s2, n, tot, CARTA)
    spaziato(d, ml, y + 28, "LA FONTE", f(TAB, 28), SEG, 3)
    y = blocco(d, ml, y + 48, s["fonte"], f(TESTO, 34), INK, 48, maxw)
    if s.get("nota"):
        y = blocco(d, ml, y + 30, s["nota"], f(TESTATA, 40), SEG, 48, maxw)
    if s.get("disclaimer"):
        blocco(d, ml, y + 34, s["disclaimer"], f(TESTO, 25), PIOMBO, 35, maxw)
    piede(d, fmt, CARTA, "rilevato", destra="@ictradar24")
    return img


def slide_storia(s, fmt, rub, n, tot, chiave):
    """Storia 9:16: gli stessi campi della slide notizia, nello stesso sistema."""
    campo = INK if rub["campo"] == "ink" else CARTA
    img, d = canvas(fmt, campo)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    s2 = dict(s)
    y = intestazione(d, fmt, rub, s2, None, None, campo)
    if s.get("data"):
        data_destra(d, fmt, campo, fmt["MT"] + 36, s["data"])
    y_piede = fmt["H"] - fmt["MB"] - 108
    col_t = CARTA if campo == INK else INK
    if s.get("dato"):
        dato = s["dato"]
        c_d = 200 if len(dato) <= 5 else (160 if len(dato) <= 8 else 124)
        fd = f(TESTATA, c_d)
        fc = f(TESTO, 42); inter_c = 59
        h_c = altezza(d, s["corpo"], fc, inter_c, maxw) + 34
        c, inter = adatta(d, s["titolo"], TESTATA, [72, 66, 60, 54], 1.06, maxw, y_piede - 30 - y - (c_d * 0.92 + 40) - h_c)
        y = blocco(d, ml, y, s["titolo"], f(TESTATA, c), col_t, inter, maxw)
        y += 40
        d.text(((ml - 4) * SS, (y + c_d * 0.74) * SS), dato, font=fd, fill=SEG, anchor="ls")
        y += c_d * 0.92
        blocco(d, ml, y + 34, s["corpo"], fc, col_t, inter_c, maxw)
    else:
        fc = f(TESTO, 44); inter_c = 62
        h_c = altezza(d, s["corpo"], fc, inter_c, maxw) + 48
        c, inter = adatta(d, s["titolo"], TESTATA, [84, 76, 70, 64, 58], 1.05, maxw, y_piede - 30 - y - h_c)
        y = blocco(d, ml, y, s["titolo"], f(TESTATA, c), col_t, inter, maxw)
        blocco(d, ml, y + 48, s["corpo"], fc, col_t, inter_c, maxw)
    fonte = s.get("fonte", "")
    etich = None
    m = re.match(r"^(Fonti?|Fonte)\s*:\s*(.*)$", fonte, re.I)
    if m:
        etich, fonte = m.group(1), m.group(2)
    elif fonte:
        etich = "Fonti" if (";" in fonte or " e " in fonte) else "Fonte"
    piede(d, fmt, campo, "rilevato", testo=fonte or None, etichetta=etich)
    return img


def slide_segui(s, fmt, rub, n, tot, chiave):
    """Chiusura fissa: la testata che chiede di seguire la pagina. Campo arancio: qui parla la testata.

    NON si rigenera a ogni uscita: i due PNG stanno in media/fisse/ e la procedura
    quotidiana ne accoda l'URL (manuale §4.4). Il blip è al centro: ricevuto.
    Il blocco di testo si adatta: il titolo scende di corpo finché titolo, corpo,
    chiusura e bottone stanno sopra il filetto del piede.
    """
    img, d = canvas(fmt, SEG)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    storia = fmt is STORIA
    testata(d, fmt, SEG, fmt["MT"] + 60, 82)
    spaziato_dx(d, fmt["W"] - ml, fmt["MT"] + 60, "@ICTRADAR24", f(TAB, 34), INK, 3)
    y0 = filetto(d, fmt, fmt["MT"] + 82, "semplice", SEG) + (90 if storia else 46)
    y_f = fmt["H"] - fmt["MB"] - 170
    corpi_tit = [92, 84, 76, 70, 64] if storia else [76, 70, 64, 58, 54]
    g1, g2, g3 = (42, 40, 34) if storia else (30, 30, 26)
    f_corpo, i_corpo = (f(TESTO, 40), 55) if storia else (f(TESTO, 38), 50)
    h_bottone = 76 if s.get("bottone") else 0
    for tit in corpi_tit:
        f_tit, f_cta = f(TESTATA, tit), f(TESTATA, min(56, tit - 8))
        i_cta = min(62, tit - 8) * 1.1
        h = (altezza(d, s["titolo"], f_tit, tit * 1.02, maxw) + g1
             + altezza(d, s["corpo"], f_corpo, i_corpo, maxw - 120) + g2
             + altezza(d, s["cta"], f_cta, i_cta, maxw) + (g3 + h_bottone if h_bottone else 0))
        if y0 + h <= y_f - 40:
            break
    y = blocco(d, ml, y0, s["titolo"], f_tit, CARTA, tit * 1.02, maxw)
    y = blocco(d, ml, y + g1, s["corpo"], f_corpo, INK, i_corpo, maxw - 120)
    y = blocco(d, ml, y + g2, s["cta"], f_cta, CARTA, i_cta, maxw)
    if s.get("bottone"):
        # il «bottone»: un rettangolo inchiostro con il testo in Carta, come i pulsanti del sito
        t = s["bottone"].upper()
        fb = f(TAB, 40)
        larg = larghezza_spaziata(d, t, fb, 3) + 64
        yb = y + g3
        d.rectangle([ml * SS, yb * SS, (ml + larg) * SS, (yb + 76) * SS], fill=INK)
        spaziato(d, ml + 32, yb + 54, t, fb, CARTA, 3)
    d.rectangle([ml * SS, y_f * SS, (fmt["W"] - ml) * SS, (y_f + 2) * SS], fill=mix(INK, SEG, 0.35))
    marchio(d, fmt["W"] - ml - 150, fmt["H"] - fmt["MB"] - 150, 150, INK, SEG, "centro")
    # il piede porta il sito: il payoff sta già nel corpo, che è la tagline dei profili
    spaziato(d, ml, fmt["H"] - fmt["MB"] - 14, "ICTRADAR24.COM", f(TAB, 30), INK, 3)
    return img


def slide_segnala(s, fmt, rub, n, tot, chiave):
    """Penultima slide fissa: l'invito a segnalare nei commenti le notizie che mancano.

    Campo Carta, come le slide che riportano un fatto e come la slide della fonte:
    qui non parla la testata (quello è l'arancio della chiusura), parla la rubrica
    «Segnalato da voi». Sta dopo tutte le slide dell'uscita e prima della chiusura
    «segui». NON si rigenera a ogni uscita: il PNG sta in media/fisse/ e la
    procedura quotidiana ne accoda l'URL prima di quello della chiusura (manuale §4.4).
    Niente folio: la posizione cambia a ogni carosello. Il blip è «rilevato».
    Titolo, corpo e bottone partono dall'alto; la nota sta in fondo, sopra il piede.
    """
    img, d = canvas(fmt, CARTA)
    ml, maxw = fmt["ML"], fmt["W"] - fmt["ML"] * 2
    storia = fmt is STORIA
    linguetta(d, ml, fmt["MT"], RUBRICHE["segnalato"]["nome"], CARTA, piena=True)
    y0 = filetto(d, fmt, fmt["MT"] + 44 + 18, "semplice", CARTA) + (100 if storia else 70)
    y_f = fmt["H"] - fmt["MB"] - 108
    f_nota, i_nota = f(TESTO, 27), 37
    y_nota = y_f
    if s.get("nota"):
        y_nota = y_f - 40 - altezza(d, s["nota"], f_nota, i_nota, maxw - 100)
    corpi_tit = [132, 120, 108, 96, 84] if storia else [118, 108, 98, 88, 78]
    g1, g2 = (56, 60) if storia else (48, 56)
    f_corpo, i_corpo = (f(TESTO, 46), 63) if storia else (f(TESTO, 44), 60)
    h_bottone = 84 if s.get("bottone") else 0
    for tit in corpi_tit:
        f_tit = f(TESTATA, tit)
        h = (altezza(d, s["titolo"], f_tit, tit * 1.0, maxw) + g1
             + altezza(d, s["corpo"], f_corpo, i_corpo, maxw - 60)
             + ((g2 + h_bottone) if h_bottone else 0))
        if y0 + h <= y_nota - 60:
            break
    y = blocco(d, ml, y0, s["titolo"], f_tit, INK, tit * 1.0, maxw)
    y = blocco(d, ml, y + g1, s["corpo"], f_corpo, INK, i_corpo, maxw - 60)
    if s.get("bottone"):
        t = s["bottone"].upper()
        fb = f(TAB, 44)
        larg = larghezza_spaziata(d, t, fb, 3) + 72
        yb = y + g2
        d.rectangle([ml * SS, yb * SS, (ml + larg) * SS, (yb + 84) * SS], fill=INK)
        spaziato(d, ml + 36, yb + 59, t, fb, CARTA, 3)
    if s.get("nota"):
        blocco(d, ml, y_nota, s["nota"], f_nota, PIOMBO, i_nota, maxw - 100)
    piede(d, fmt, CARTA, "rilevato", destra="@ictradar24")
    return img

TIPI = {
    "copertina": slide_copertina,
    "voce":      slide_voce,
    "notizia":   slide_notizia,
    "perche":    slide_perche,
    "elenco":    slide_elenco,
    "premio":    slide_premio,
    "nonassegnati": slide_nonassegnati,
    "quintetto": slide_quintetto,
    "fonte":     slide_fonte,
    "storia":    slide_storia,
    "segui":     slide_segui,
    "segnala":   slide_segnala,
}


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main(percorso_json):
    with open(percorso_json, encoding="utf-8") as fh:
        spec = json.load(fh)

    chiave = spec["rubrica"]
    rub = RUBRICHE.get(chiave, RUBRICHE["radar"])
    fmt = STORIA if spec.get("formato") == "storia" else POST
    outdir = spec.get("output", "/mnt/user-data/outputs/slide")
    os.makedirs(outdir, exist_ok=True)

    totale = len(spec["slide"])
    prodotti = []
    for i, s in enumerate(spec["slide"], 1):
        # Una slide può dichiarare una propria rubrica: serve al blocco Italia dentro il
        # Radar, che prende linguetta arancio e riga Italia al posto del filetto semplice.
        chiave_slide = s.get("rubrica") or chiave
        rub_slide = RUBRICHE.get(chiave_slide, rub)
        n = None if fmt is STORIA else i
        img = TIPI[s["tipo"]](s, fmt, rub_slide, n, totale, chiave_slide)
        nome = s.get("file") or f"{i:02d}-{s.get('nome', s['tipo'])}.png"
        salva(img, fmt, os.path.join(outdir, nome))
        prodotti.append(nome)

    print(f"Rubrica: {chiave}  |  formato: {fmt['W'] * USCITA}x{fmt['H'] * USCITA} px"
          f" ({fmt['W']}x{fmt['H']} logici)")
    for nme in prodotti:
        kb = os.path.getsize(os.path.join(outdir, nme)) // 1024
        print(f"  {nme}  ({kb} KB)")
    cartella = spec.get("cartella", "AAAA-MM-GG-rubrica")
    print(f"\nCartella locale: {outdir}")
    print(f"Su GitHub:       media/{cartella}/")
    print("URL pubblico:    https://raw.githubusercontent.com/ictradar24/"
          f"ictradar24-media/main/media/{cartella}/NN-nome.png")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 render.py contenuto.json")
    main(sys.argv[1])
