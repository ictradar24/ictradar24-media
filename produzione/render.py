#!/usr/bin/env python3
"""
ICT RADAR 24 — Renderer delle slide
====================================
Genera caroselli e storie nel sistema visivo definito dal brand book.

USO
    python3 render.py contenuto.json

Il JSON descrive le slide; questo file contiene tutte le costanti di marca.
Non modificare colori, font o margini qui dentro senza aggiornare il brand book:
questo script è l'implementazione della sezione 4, 5 e 7 di quel documento.

DIPENDENZE: Pillow. Font in /mnt/skills/examples/canvas-design/canvas-fonts/
"""

import json, os, sys
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────────────────────
# COSTANTI DI MARCA — brand book §4 (colore) e §5 (tipografia)
# ─────────────────────────────────────────────────────────────

FONTDIR = "/mnt/skills/examples/canvas-design/canvas-fonts/"
DISP  = FONTDIR + "BricolageGrotesque-Bold.ttf"   # display
BODY  = FONTDIR + "InstrumentSans-Regular.ttf"    # testo
MONO  = FONTDIR + "JetBrainsMono-Regular.ttf"     # dati
MONOB = FONTDIR + "JetBrainsMono-Bold.ttf"        # etichette

NIGHT  = (10, 20, 36)     # #0A1424  fondo
PANEL  = (17, 31, 53)     # #111F35  livello secondario
CYAN   = (0, 216, 196)    # #00D8C4  accento primario
AMBER  = (255, 176, 32)   # #FFB020  allerta
WHITE  = (244, 246, 249)  # #F4F6F9  testo principale
STEEL  = (140, 151, 168)  # #8C97A8  testo secondario
GREEN  = (0, 168, 104)    # #00A868  rubrica Italia
VIOLET = (123, 92, 255)   # #7B5CFF  Sul radar / Gartner NBA Edition
COPPER = (178, 112, 36)   # #B27024  Forge Copper — Sotto il cofano (brand book §4)
ROSE   = (255, 61, 113)   # #FF3D71  Signal Rose — SOLO la slide di chiusura (brand book §4)

# Colore per rubrica — brand book §4
RUBRICHE = {
    "radar":     CYAN,    # Radar Quotidiano
    "italia":    GREEN,   # Radar Italia
    "allerta":   AMBER,   # Allerta
    "segnalato": CYAN,    # Segnalato da voi (slide dentro il Radar)
    "sulradar":  VIOLET,  # Sul radar
    "puntodivista": CYAN, # Punto di vista
    "virgolette": STEEL,  # Virgolette
    "topdelmese": WHITE,  # Top del mese
    "gartner":   VIOLET,  # Gartner NBA Edition
    "cofano":    COPPER,  # Sotto il cofano
}

# Formati — brand book §7
POST   = dict(W=1080, H=1350, ML=90, MT=120, MB=140)   # carosello 4:5
STORIA = dict(W=1080, H=1920, ML=90, MT=300, MB=360)   # storia 9:16
SS = 2  # supersampling: si disegna a 2x e si riduce, per bordi netti


# ─────────────────────────────────────────────────────────────
# PRIMITIVE
# ─────────────────────────────────────────────────────────────

def f(path, size):
    return ImageFont.truetype(path, size * SS)


def canvas(fmt):
    img = Image.new("RGB", (fmt["W"] * SS, fmt["H"] * SS), NIGHT)
    return img, ImageDraw.Draw(img)


def arcs(d, fmt, colore, opacita=0.07):
    """Texture degli archi — solo famiglia Rilevamento (brand book §9)."""
    ox, oy = -0.05 * fmt["W"] * SS, 1.02 * fmt["H"] * SS
    for rf, al in zip([0.62, 0.95, 1.30], [1.0, 0.8, 0.62]):
        r = rf * fmt["W"] * SS
        c = tuple(int(colore[k] * opacita * al + NIGHT[k] * (1 - opacita * al))
                  for k in range(3))
        d.arc([ox - r, oy - r, ox + r, oy + r], -90, 0, fill=c, width=int(9 * SS))


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
    """Restituisce la y successiva. interlinea in unita logiche."""
    for riga in wrap(d, testo, font, max_w):
        d.text((x * SS, y * SS), riga, font=font, fill=fill)
        y += interlinea
    return y


def mono(d, x, y, testo, font, fill, tracking):
    """Testo monospaziato con spaziatura fra lettere."""
    px = x * SS
    for ch in testo:
        d.text((px, y * SS), ch, font=font, fill=fill)
        px += d.textlength(ch, font=font) + tracking * SS


def intestazione(d, fmt, etichetta, colore, numerazione=None):
    mono(d, fmt["ML"], fmt["MT"], etichetta.upper(), f(MONOB, 26), colore, 4)
    if numerazione:
        mono(d, fmt["W"] - fmt["ML"] - 72, fmt["MT"], numerazione,
             f(MONO, 24), STEEL, 3)


def salva(img, fmt, percorso):
    img.resize((fmt["W"], fmt["H"]), Image.LANCZOS).save(
        percorso, "PNG", optimize=True)


# ─────────────────────────────────────────────────────────────
# TIPI DI SLIDE — brand book §7 (anatomia del carosello)
# ─────────────────────────────────────────────────────────────

def slide_copertina(s, fmt, colore, num):
    """Hook grande. Famiglia Rilevamento: con archi."""
    img, d = canvas(fmt)
    if s.get("archi", True):
        arcs(d, fmt, colore, 0.09)
    intestazione(d, fmt, s["etichetta"], colore, num)
    y = blocco(d, fmt["ML"], 330, s["hook"], f(DISP, s.get("corpo_hook", 92)),
               WHITE, s.get("interlinea_hook", 100), fmt["W"] - fmt["ML"] * 2)
    if s.get("sottotitolo"):
        blocco(d, fmt["ML"], y + 48, s["sottotitolo"], f(BODY, 40),
               colore, 54, fmt["W"] - fmt["ML"] * 2)
    if s.get("piede"):
        mono(d, fmt["ML"], fmt["H"] - fmt["MB"] - 20, s["piede"].upper(),
             f(MONO, 24), STEEL, 3)
    return img


def slide_notizia(s, fmt, colore, num):
    """Titolo, dato numerico in evidenza, corpo, fonte."""
    img, d = canvas(fmt)
    intestazione(d, fmt, s.get("etichetta", ""), colore, num)
    y = blocco(d, fmt["ML"], 300, s["titolo"], f(DISP, 66), WHITE, 76,
               fmt["W"] - fmt["ML"] * 2)
    if s.get("dato"):
        y = blocco(d, fmt["ML"], y + 46, s["dato"], f(DISP, 130), colore, 140,
                   fmt["W"] - fmt["ML"] * 2)
    y = blocco(d, fmt["ML"], y + 40, s["corpo"], f(BODY, 40), STEEL, 56,
               fmt["W"] - fmt["ML"] * 2)
    if s.get("fonte"):
        mono(d, fmt["ML"], fmt["H"] - fmt["MB"] - 20, s["fonte"].upper(),
             f(MONO, 24), STEEL, 3)
    return img


def slide_perche(s, fmt, colore, num):
    """Il 'perche conta'. Fondo invertito per stacco visivo."""
    img = Image.new("RGB", (fmt["W"] * SS, fmt["H"] * SS), colore)
    d = ImageDraw.Draw(img)
    # ogni rubrica con fondo invertito ha il suo scuro nella stessa tinta: un testo
    # blu notte su un campo rame leggerebbe come due colori estranei (brand book §4)
    scuro = ((6, 62, 56) if colore == CYAN else
             (4, 44, 28) if colore == GREEN else
             (26, 15, 4) if colore == COPPER else NIGHT)
    mono(d, fmt["ML"], fmt["MT"], "PERCHÉ CONTA", f(MONOB, 26), scuro, 4)
    blocco(d, fmt["ML"], 340, s["testo"], f(DISP, 70), scuro, 80,
           fmt["W"] - fmt["ML"] * 2)
    mono(d, fmt["ML"], fmt["H"] - fmt["MB"] - 20, "@ICTRADAR24",
         f(MONOB, 26), scuro, 4)
    return img


def slide_elenco(s, fmt, colore, num):
    """Voci con pallino. Pallino pieno = Rilevamento, vuoto = Voce."""
    img, d = canvas(fmt)
    intestazione(d, fmt, s["etichetta"], colore, num)
    if s.get("titolo"):
        y = blocco(d, fmt["ML"], 300, s["titolo"], f(DISP, 76), WHITE, 86,
                   fmt["W"] - fmt["ML"] * 2)
        if s.get("sottotitolo"):
            mono(d, fmt["ML"], y + 22, s["sottotitolo"].upper(),
                 f(MONO, 22), STEEL, 3)
            y += 120
    else:
        y = 300
    for voce in s["voci"]:
        col = globals().get(voce.get("colore", "").upper(), colore)
        cx, cy = fmt["ML"] * SS, (y + 16) * SS
        if voce.get("vuoto"):
            d.ellipse([cx, cy, cx + 18 * SS, cy + 18 * SS], outline=col,
                      width=int(3 * SS))
        else:
            d.ellipse([cx, cy, cx + 18 * SS, cy + 18 * SS], fill=col)
        d.text(((fmt["ML"] + 44) * SS, y * SS), voce["nome"],
               font=f(DISP, 46), fill=WHITE)
        if voce.get("desc"):
            d.text(((fmt["ML"] + 44) * SS, (y + 58) * SS), voce["desc"],
                   font=f(BODY, 32), fill=STEEL)
            y += 148
        else:
            y += 108
    return img


def slide_premio(s, fmt, colore, num):
    """Nome premio, criterio in mono, vincitore in grande."""
    img, d = canvas(fmt)
    intestazione(d, fmt, s["etichetta"], colore, num)
    y = blocco(d, fmt["ML"], 340, s["premio"], f(DISP, 76), WHITE, 86,
               fmt["W"] - fmt["ML"] * 2)
    mono(d, fmt["ML"], y + 22, s["criterio"].upper(), f(MONO, 24), STEEL, 3)
    y = blocco(d, fmt["ML"], y + 130, s["vincitore"], f(DISP, 96), CYAN, 106,
               fmt["W"] - fmt["ML"] * 2)
    if s.get("nota"):
        blocco(d, fmt["ML"], y + 34, s["nota"], f(BODY, 34), STEEL, 46,
               fmt["W"] - fmt["ML"] * 2)
    return img


def slide_fonte(s, fmt, colore, num):
    """Chiusura: fonte, natura editoriale, eventuale disclaimer obbligatorio."""
    img, d = canvas(fmt)
    intestazione(d, fmt, s.get("etichetta", "LA FONTE"), colore, num)
    y = blocco(d, fmt["ML"], 300, s["fonte"], f(BODY, 36), WHITE, 50,
               fmt["W"] - fmt["ML"] * 2)
    if s.get("nota"):
        y = blocco(d, fmt["ML"], y + 40, s["nota"], f(BODY, 32), CYAN, 44,
                   fmt["W"] - fmt["ML"] * 2)
    if s.get("disclaimer"):
        blocco(d, fmt["ML"], y + 40, s["disclaimer"], f(BODY, 27), STEEL, 37,
               fmt["W"] - fmt["ML"] * 2)
    mono(d, fmt["ML"], fmt["H"] - fmt["MB"] - 20, "@ICTRADAR24",
         f(MONOB, 26), colore, 4)
    return img


def slide_storia(s, fmt, colore, num):
    """Storia 9:16. Il testo vive dentro l'immagine: le storie non hanno didascalia."""
    img, d = canvas(fmt)
    ox, oy = -0.10 * fmt["W"] * SS, 1.02 * fmt["H"] * SS
    for rf, al in zip([0.70, 1.05, 1.40], [1.0, 0.8, 0.62]):
        r = rf * fmt["W"] * SS
        c = tuple(int(colore[k] * 0.07 * al + NIGHT[k] * (1 - 0.07 * al))
                  for k in range(3))
        d.arc([ox - r, oy - r, ox + r, oy + r], -90, 0, fill=c, width=int(9 * SS))
    d.rectangle([0, fmt["MT"] * SS, 8 * SS, (fmt["H"] - fmt["MB"]) * SS], fill=colore)
    mono(d, fmt["ML"], fmt["MT"], s["etichetta"].upper(), f(MONOB, 28), colore, 5)
    y = blocco(d, fmt["ML"], fmt["MT"] + 90, s["titolo"], f(DISP, 76), WHITE, 86,
               fmt["W"] - fmt["ML"] * 2)
    if s.get("dato"):
        y = blocco(d, fmt["ML"], y + 60, s["dato"], f(DISP, 116), colore, 124,
                   fmt["W"] - fmt["ML"] * 2)
    blocco(d, fmt["ML"], y + 50, s["corpo"], f(BODY, 40), STEEL, 56,
           fmt["W"] - fmt["ML"] * 2)
    if s.get("fonte"):
        mono(d, fmt["ML"], fmt["H"] - fmt["MB"] - 40, s["fonte"].upper(),
             f(MONO, 24), STEEL, 3)
    mono(d, fmt["ML"], fmt["H"] - fmt["MB"] + 10, "@ICTRADAR24",
         f(MONOB, 26), colore, 4)
    return img


def slide_segui(s, fmt, colore, num):
    """Chiusura fissa: chiede di seguire la pagina. Brand book §7.

    NON si rigenera a ogni uscita. Il testo e il colore sono fissi, quindi i due
    PNG stanno una volta sola su GitHub in media/fisse/ e ogni giorno si accoda
    il loro URL (manuale §4.4). Questo tipo serve a rifare quei due file se un
    giorno il testo cambia — non alla produzione quotidiana.

    Signal Rose e' usato QUI E SOLO QUI: e' il segnale che questa non e' una
    notizia ma la redazione che parla di se'.
    """
    fondo, testo, secondario = ROSE, (48, 6, 22), (74, 10, 34)
    img = Image.new("RGB", (fmt["W"] * SS, fmt["H"] * SS), fondo)
    d = ImageDraw.Draw(img)

    storia = fmt is STORIA
    maxw = fmt["W"] - fmt["ML"] * 2
    tit, inter = (84, 96) if storia else (76, 86)
    fdisp, fbody, fcta = f(DISP, tit), f(BODY, 40), f(DISP, 46)

    # il blocco delle tre battute va centrato fra intestazione e firma
    h = (len(wrap(d, s["titolo"], fdisp, maxw)) * inter + 44
         + len(wrap(d, s["corpo"], fbody, maxw)) * 56 + 52
         + len(wrap(d, s["cta"], fcta, maxw)) * 54)
    alto, basso = fmt["MT"] + 100, fmt["H"] - fmt["MB"] - 130
    y = alto + max(0, (basso - alto - h) // 2)

    mono(d, fmt["ML"], fmt["MT"], "ICT RADAR 24", f(MONOB, 26), testo, 4)
    y = blocco(d, fmt["ML"], y, s["titolo"], fdisp, testo, inter, maxw)
    y = blocco(d, fmt["ML"], y + 44, s["corpo"], fbody, secondario, 56, maxw)
    blocco(d, fmt["ML"], y + 52, s["cta"], fcta, testo, 54, maxw)
    mono(d, fmt["ML"], fmt["H"] - fmt["MB"] - 30, "@ICTRADAR24", f(MONOB, 32), testo, 6)
    return img


TIPI = {
    "copertina": slide_copertina,
    "notizia":   slide_notizia,
    "perche":    slide_perche,
    "elenco":    slide_elenco,
    "premio":    slide_premio,
    "fonte":     slide_fonte,
    "storia":    slide_storia,
    "segui":     slide_segui,
}


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main(percorso_json):
    with open(percorso_json, encoding="utf-8") as fh:
        spec = json.load(fh)

    colore = RUBRICHE.get(spec["rubrica"], CYAN)
    fmt = STORIA if spec.get("formato") == "storia" else POST
    outdir = spec.get("output", "/mnt/user-data/outputs/slide")
    os.makedirs(outdir, exist_ok=True)

    totale = len(spec["slide"])
    prodotti = []
    for i, s in enumerate(spec["slide"], 1):
        num = None if fmt is STORIA else f"{i:02d}/{totale:02d}"
        # Una slide puo' dichiarare una propria rubrica e prendere il suo colore.
        # Serve al blocco Italia dentro il Radar: brand book §4, «Un solo colore
        # per pezzo» — il verde SOSTITUISCE il cyan su quelle slide, non gli si
        # affianca, quindi qui il colore viene rimpiazzato e non sommato.
        colore_slide = RUBRICHE.get(s.get("rubrica"), colore) if s.get("rubrica") else colore
        img = TIPI[s["tipo"]](s, fmt, colore_slide, num)
        nome = s.get("file") or f"{i:02d}-{s.get('nome', s['tipo'])}.png"
        salva(img, fmt, os.path.join(outdir, nome))
        prodotti.append(nome)

    print(f"Rubrica: {spec['rubrica']}  |  formato: {fmt['W']}x{fmt['H']}")
    for n in prodotti:
        kb = os.path.getsize(os.path.join(outdir, n)) // 1024
        print(f"  {n}  ({kb} KB)")
    cartella = spec.get("cartella", "AAAA-MM-GG-rubrica")
    print(f"\nCartella locale: {outdir}")
    print(f"Su GitHub:       media/{cartella}/")
    print("URL pubblico:    https://raw.githubusercontent.com/ictradar24/"
          f"ictradar24-media/main/media/{cartella}/NN-nome.png")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 render.py contenuto.json")
    main(sys.argv[1])
