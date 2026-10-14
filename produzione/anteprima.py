#!/usr/bin/env python3
"""ICT RADAR 24 — Generatore di anteprime (copia dal Progetto)."""

import base64, html, json, os, re, sys

RUBRICHE = {
    "radar": "#00D8C4", "italia": "#00A868", "allerta": "#FFB020",
    "segnalato": "#00D8C4", "sulradar": "#7B5CFF", "puntodivista": "#00D8C4",
    "virgolette": "#8C97A8", "topdelmese": "#F4F6F9", "gartner": "#7B5CFF",
    "cofano": "#7B5CFF",
}

TAGLIO_IG = 125
TAGLIO_LI = 140
LIMITE_DOC_TITLE = 58

# Le menzioni LinkedIn nel testo che si programma, dal 14 ottobre 2026 (manuale §3-ter,
# «I tag dalla rubrica»): @[urn:li:organization:ID|Nome] o @[urn:li:person:ID|Nome].
# Su LinkedIn si vede solo il Nome, quindi l'anteprima mostra il Nome e conta il taglio
# dei 140 caratteri su quello, non sulla stringa intera. Aggiunto il 15 ottobre 2026.
MENZIONE = re.compile(r"@\[(urn:li:([A-Za-z]+):[^|\]\s]+)\|([^\]\n]+)\]")
TETTO_MENZIONI = 3


def incorpora(percorso):
    with open(percorso, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


def testo_html(t):
    return html.escape(t).replace("\n", "<br>")


def spezza(testo, limite):
    if len(testo) <= limite:
        return testo, ""
    taglio = testo.rfind(" ", 0, limite)
    if taglio < limite * 0.6:
        taglio = limite
    return testo[:taglio], testo[taglio:]


def segmenti(testo):
    """Il testo in pezzi (visibile, urn): urn è None per il testo normale."""
    out, pos = [], 0
    for m in MENZIONE.finditer(testo):
        if m.start() > pos:
            out.append((testo[pos:m.start()], None))
        out.append((m.group(3), m.group(1)))
        pos = m.end()
    if pos < len(testo):
        out.append((testo[pos:], None))
    return out


def visibile(testo):
    """Il testo come lo legge chi scorre il feed: le menzioni ridotte al nome."""
    return "".join(v for v, _ in segmenti(testo))


def taglia_segmenti(segs, n):
    prima, dopo, contati = [], [], 0
    for v, urn in segs:
        if contati >= n:
            dopo.append((v, urn))
        elif contati + len(v) <= n:
            prima.append((v, urn))
        else:
            k = n - contati
            prima.append((v[:k], urn))
            dopo.append((v[k:], urn))
        contati += len(v)
    return prima, dopo


def html_segmenti(segs):
    return "".join(
        f'<span class="menzione" title="{html.escape(urn)}">{testo_html(v)}</span>'
        if urn else testo_html(v)
        for v, urn in segs)


def blocco_didascalia(testo, limite, etichetta_taglio, menzioni=False):
    """Con menzioni=True (solo il post LinkedIn) le menzioni si vedono come nome e il
    taglio si conta sul testo visibile. Altrove il testo resta com'è, perché lì una
    menzione LinkedIn uscirebbe davvero come testo grezzo."""
    segs = segmenti(testo) if menzioni else [(testo, None)]
    vis = "".join(v for v, _ in segs)
    sopra, nascosto = spezza(vis, limite)
    prima, dopo = taglia_segmenti(segs, len(sopra))
    out = [f'<p class="didascalia">{html_segmenti(prima)}']
    if nascosto:
        out.append(f'<span class="taglio">... {etichetta_taglio}</span>')
        out.append(f'<span class="resto">{html_segmenti(dopo)}</span>')
    out.append("</p>")
    return "".join(out)


def conteggio_li(testo):
    n_m = len(MENZIONE.findall(testo))
    if not n_m:
        return f"{len(testo)} caratteri"
    return (f"{len(visibile(testo))} caratteri visibili · {len(testo)} nel testo inviato · "
            f"{n_m} {'menzione' if n_m == 1 else 'menzioni'}")


def primo_commento(li):
    return li.get("firstCommentText", li.get("primoCommento", ""))


def controlla_menzioni(spec):
    """Le menzioni come stanno nel testo che si programma, non come le dichiara la spec,
    più i controlli che si possono fare senza la rubrica: tetto, posti vietati, forma."""
    li = spec.get("linkedin") or {}
    ig = spec.get("instagram") or {}
    varianti = li.get("varianti", [])
    trovate, problemi, avvisi = [], [], []
    for j, v in enumerate(varianti):
        testo = v.get("testo", "")
        nome_var = v.get("nome", f"Variante {j + 1}")
        ms = MENZIONE.findall(testo)
        for urn, tipo, nome in ms:
            trovate.append((nome_var if len(varianti) > 1 else "LinkedIn", nome, urn, tipo))
        if len(ms) > TETTO_MENZIONI:
            problemi.append(f"{nome_var}: {len(ms)} menzioni, il tetto è {TETTO_MENZIONI}.")
        if testo.count("@[") > len(ms):
            problemi.append(f"{nome_var}: una menzione scritta male (manca l'urn o la barra "
                            "prima del nome). Uscirebbe come testo con le parentesi quadre.")
    altrove = [
        ("nella didascalia Instagram: lì uscirebbe come testo, e i tag Instagram "
         "restano a mano", ig.get("testo", "")),
        ("nel primo commento: lì non va mai", primo_commento(li)),
        ("nel titolo del documento: lì non va mai", li.get("documentTitle", "")),
        ("nei testi alternativi: lì non va mai",
         " ".join(spec.get("alt", []) + spec.get("storie_alt", []))),
    ]
    for dove, testo in altrove:
        if "@[" in testo:
            problemi.append(f"Menzione {dove}.")
    m = spec.get("menzioni") or {}
    dichiarati = {}
    for v in m.get("elenco", []):
        s = (v.get("urn") or "").strip()
        trovata = MENZIONE.search(s)
        if trovata:
            dichiarati[trovata.group(1)] = trovata.group(0)
        elif s.startswith("urn:li:"):
            dichiarati[s] = None
    nel_testo = {urn: f"@[{urn}|{nome}]" for _, nome, urn, _ in trovate}
    for urn, intera in nel_testo.items():
        if urn not in dichiarati:
            avvisi.append(f"Nel testo ma non nell'elenco della specifica: {intera}")
        elif dichiarati[urn] and dichiarati[urn] != intera:
            avvisi.append(f"Stesso identificativo, nome diverso: nel testo {intera}, "
                          f"nella specifica {dichiarati[urn]}")
    for urn in dichiarati:
        if urn not in nel_testo:
            avvisi.append(f"Nell'elenco della specifica ma non nel testo: {urn}")
    return trovate, problemi, avvisi


def sezione_menzioni(spec):
    m = spec.get("menzioni")
    trovate, problemi, avvisi = controlla_menzioni(spec)
    if m is None and not trovate and not problemi:
        return ""
    m = m or {}
    if trovate:
        righe = "".join(
            f'<tr><td class="piattaforma">{html.escape(dove)}</td>'
            f'<td class="nome-tag"><span class="menzione">{html.escape(nome)}</span></td>'
            f'<td class="urn">{html.escape(urn)}<br>'
            f'<span class="tipo">{"persona" if tipo == "person" else "pagina"}</span></td></tr>'
            for dove, nome, urn, tipo in trovate)
        nel_testo = (f'<table class="menzioni"><thead><tr><th>Dove</th>'
                     f'<th>Nome che si vede</th><th>Identificativo che pubblica</th>'
                     f'</tr></thead><tbody>{righe}</tbody></table>')
    else:
        nel_testo = ('<p class="nessuna">Nessuna menzione nel post LinkedIn: '
                     'i nomi escono senza chiocciola.</p>')
    lista_problemi = ""
    if problemi:
        lista_problemi = ('<ul class="problemi">' +
                          "".join(f"<li>{html.escape(p)}</li>" for p in problemi) + "</ul>")
    lista_avvisi = ""
    if avvisi:
        lista_avvisi = ('<ul class="dubbi">' +
                        "".join(f"<li>{html.escape(a)}</li>" for a in avvisi) + "</ul>")
    riga = ""
    if m.get("riga"):
        riga = (f'<p class="sottotitolo">Il blocco dei tag della consegna</p>'
                f'<p class="riga-tag">{testo_html(m["riga"])}</p>')
    voci = m.get("elenco", [])
    elenco = ""
    if voci:
        righe = "".join(
            f'<tr><td class="piattaforma">{html.escape(v.get("piattaforma", ""))}</td>'
            f'<td class="nome-tag">{html.escape(v.get("nome", ""))}'
            + (f'<br><span class="nota-voce">{html.escape(v["nota"])}</span>'
               if v.get("nota") else "") +
            f'</td><td class="urn">{html.escape(v.get("urn", "")) or "senza chiocciola"}</td></tr>'
            for v in voci)
        elenco = (f'<p class="sottotitolo">Dalla specifica</p>'
                  f'<table class="menzioni"><thead><tr><th>Dove</th>'
                  f'<th>Nome visualizzato</th><th>Identificativo</th>'
                  f'</tr></thead><tbody>{righe}</tbody></table>')
    dubbi = m.get("dubbi", [])
    lista_dubbi = ""
    if dubbi:
        lista_dubbi = ("<ul class=\"dubbi\">" +
                       "".join(f"<li>{html.escape(d)}</li>" for d in dubbi) +
                       "</ul>")
    return f"""
    <section class="canale" id="menzioni">
      <header class="intestazione-canale"><h2>Menzioni</h2></header>
      <div class="cornice"><div class="corpo-cornice">
        {lista_problemi}{nel_testo}{lista_avvisi}{riga}{elenco}{lista_dubbi}
      </div></div>
      <p class="nota">La prima tabella è letta dal testo che si programma, non dalla
      specifica. L'approvazione cade sull'identificativo, non sul nome: il nome
      visualizzato lo scriviamo noi e può puntare altrove. Le righe in rosso vanno
      corrette prima di programmare.</p>
    </section>"""


def sezione_scartate(spec):
    """Le candidate rimaste fuori, da valutare prima dell'approvazione. Aggiunta il 13
    ottobre 2026: quel giorno la lista era solo nel messaggio di consegna e Simone non
    l'ha vista. Da qui sta nell'anteprima, sopra le menzioni; se manca lo dice in rosso."""
    if spec.get("rubrica") not in ("radar", "italia", "radar-italia"):
        return ""
    voci = spec.get("scartate")
    if voci is None:
        corpo = ('<p class="nessuna" style="color:#c0392b;font-weight:600">ATTENZIONE: '
                 'nella spec manca la lista delle notizie scartate. Va scritta prima di '
                 'chiedere l\'approvazione (campo «scartate»).</p>')
    elif not voci:
        corpo = '<p class="nessuna">Nessuna scartata che valga la pena valutare oggi.</p>'
    else:
        corpo = "<ol class=\"dubbi\">" + "".join(
            f"<li><strong>{html.escape(v.get('titolo', ''))}</strong><br>"
            f"{html.escape(v.get('fonte', ''))}<br><em>{html.escape(v.get('perche', ''))}</em></li>"
            for v in voci) + "</ol>"
    return f"""
    <section class="canale" id="scartate">
      <header class="intestazione-canale"><h2>Notizie scartate da valutare</h2></header>
      <div class="cornice"><div class="corpo-cornice">{corpo}</div></div>
      <p class="nota">Hanno superato la verifica 1. Se ne vuoi una, si produce e si verifica
      come le altre prima che entri.</p>
    </section>"""


def sezione_storie(spec):
    storie = spec.get("storie", [])
    if not storie:
        return ""
    base = spec.get("base", "")
    alt = spec.get("storie_alt", [])
    figure = []
    for i, percorso in enumerate(storie):
        pieno = os.path.join(base, percorso) if base else percorso
        dati = incorpora(pieno)
        testo_alt = alt[i] if i < len(alt) else ""
        kb = os.path.getsize(pieno) // 1024
        figure.append(f"""
        <figure class="slide">
          <img src="{dati}" alt="{html.escape(testo_alt)}">
          <figcaption>
            <span class="num">{html.escape(os.path.basename(percorso))}</span>
            <span class="peso">{kb} KB</span>
            <span class="alt">{html.escape(testo_alt) or
                               '<em>testo alternativo mancante</em>'}</span>
          </figcaption>
        </figure>""")
    return f"""
      <div class="intestazione-canale" style="margin-top:34px">
        <h2>Le Storie del Radar</h2>
        <span class="orario">{html.escape(spec.get('ora_storie', ''))}</span>
      </div>
      <div class="striscia">{''.join(figure)}</div>
      <p class="nota">Una per ogni slide notizia, in 9:16, con il testo copiato
      dalla slide d'origine e non riscritto. Nessuna didascalia: su Metricool il
      campo <code>text</code> non viene inviato.</p>"""


def costruisci(spec):
    colore = RUBRICHE.get(spec.get("rubrica", "radar"), "#00D8C4")
    slide = spec.get("slide", [])
    alt = spec.get("alt", [])
    base = spec.get("base", "")

    figure = []
    for i, percorso in enumerate(slide):
        pieno = os.path.join(base, percorso) if base else percorso
        dati = incorpora(pieno)
        testo_alt = alt[i] if i < len(alt) else ""
        kb = os.path.getsize(pieno) // 1024
        figure.append(f"""
        <figure class="slide">
          <img src="{dati}" alt="{html.escape(testo_alt)}">
          <figcaption>
            <span class="num">{i + 1:02d} / {len(slide):02d}</span>
            <span class="peso">{kb} KB</span>
            <span class="alt">{html.escape(testo_alt) or
                               '<em>testo alternativo mancante</em>'}</span>
          </figcaption>
        </figure>""")

    ig = spec.get("instagram")
    li = spec.get("linkedin")

    sezione_ig = ""
    if ig:
        sezione_ig = f"""
    <section class="canale" id="instagram">
      <header class="intestazione-canale">
        <h2>Instagram</h2>
        <span class="orario">{html.escape(ig.get('ora', ''))}</span>
      </header>
      <div class="cornice">
        <div class="riga-profilo">
          <span class="pallino" style="background:{colore}"></span>
          <span class="handle">ictradar24</span>
        </div>
        <div class="posto-immagine">
          <img src="{incorpora(os.path.join(base, slide[0]) if base else slide[0])}"
               alt="prima slide">
        </div>
        <div class="corpo-cornice">
          <p class="azioni">Mi piace · Commenta · Condividi · Salva</p>
          {blocco_didascalia(ig.get('testo', ''), TAGLIO_IG, 'altro')}
        </div>
      </div>
      <p class="nota">Instagram mostra circa {TAGLIO_IG} caratteri prima di
      «altro». Quello che sta sopra la linea e' tutto cio' che la maggior parte
      delle persone leggera'.</p>
    </section>"""

    sezione_li = ""
    if li:
        varianti = li.get("varianti", [])
        titolo_doc = li.get("documentTitle", "")
        n = len(titolo_doc)
        stato = "ok" if n <= LIMITE_DOC_TITLE else "errore"
        tab = "".join(
            f'<button class="tab{" attiva" if j == 0 else ""}" '
            f'data-var="{j}">{html.escape(v.get("nome", f"Variante {j+1}"))}</button>'
            for j, v in enumerate(varianti))
        corpi = "".join(
            f'<div class="variante{" attiva" if j == 0 else ""}" data-var="{j}">'
            f'{blocco_didascalia(v.get("testo", ""), TAGLIO_LI, "vedi altro", menzioni=True)}'
            f'<p class="conteggio">{conteggio_li(v.get("testo", ""))}</p></div>'
            for j, v in enumerate(varianti))

        sezione_li = f"""
    <section class="canale" id="linkedin">
      <header class="intestazione-canale">
        <h2>LinkedIn</h2>
        <span class="orario">{html.escape(li.get('ora', ''))}</span>
      </header>
      {f'<div class="tabs">{tab}</div>' if len(varianti) > 1 else ''}
      <div class="cornice">
        <div class="riga-profilo">
          <span class="pallino quadro" style="background:{colore}"></span>
          <span class="handle">ICT Radar 24</span>
        </div>
        <div class="corpo-cornice">{corpi}</div>
        <div class="documento">
          <span class="etichetta-doc">Documento</span>
          <span class="titolo-doc">{html.escape(titolo_doc)}</span>
          <span class="conta-doc {stato}">{n} / {LIMITE_DOC_TITLE} caratteri</span>
        </div>
        <div class="commento">
          <span class="etichetta-commento">Primo commento</span>
          {blocco_didascalia(primo_commento(li), 250, 'vedi altro')}
        </div>
      </div>
      <p class="nota">LinkedIn taglia intorno ai {TAGLIO_LI} caratteri su
      telefono, contati sul testo che si vede: una menzione vale quanto il suo nome.
      Il titolo del documento compare sopra il carosello e oltre i
      {LIMITE_DOC_TITLE} caratteri Metricool rifiuta il post.</p>
    </section>"""

    return f"""<title>{html.escape(spec.get('titolo', 'Anteprima'))}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Instrument+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;700&display=swap');

:root {{
  color-scheme: light;
  --ground: #EFF2F5;
  --surface: #FFFFFF;
  --ink: #0F1A26;
  --ink-soft: #5A6875;
  --line: #DCE3E9;
  --accent: {colore};
  --accent-testo: #006F66;
  --allarme: #B4341F;
  --menzione: #0A66C2;
  --display: 'Bricolage Grotesque', 'Trebuchet MS', sans-serif;
  --corpo: 'Instrument Sans', system-ui, sans-serif;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --ground: #0A1424;
    --surface: #111F35;
    --ink: #F4F6F9;
    --ink-soft: #8C97A8;
    --line: #1E3049;
    --accent-testo: {colore};
    --allarme: #FF8A73;
    --menzione: #70B5F9;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --ground: #0A1424;
  --surface: #111F35;
  --ink: #F4F6F9;
  --ink-soft: #8C97A8;
  --line: #1E3049;
  --accent-testo: {colore};
  --allarme: #FF8A73;
  --menzione: #70B5F9;
}}

body {{
  margin: 0; background: var(--ground); color: var(--ink);
  font-family: var(--corpo); font-size: 15px; line-height: 1.55;
}}
.guscio {{ max-width: 1180px; margin: 0 auto; padding-inline: 20px;
           padding-block: 32px 64px; }}

.testata {{ display: flex; flex-wrap: wrap; align-items: baseline;
            gap: 10px 18px; padding-bottom: 18px;
            border-bottom: 2px solid var(--accent); margin-bottom: 32px; }}
.testata h1 {{ font-family: var(--display); font-weight: 800; font-size: 30px;
               line-height: 1.1; margin: 0; text-wrap: balance; }}
.meta {{ font-family: var(--mono); font-size: 11px; letter-spacing: .09em;
         text-transform: uppercase; color: var(--ink-soft); }}

.impalcatura {{ display: grid; gap: 34px;
                grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); }}
@media (max-width: 860px) {{ .impalcatura {{ grid-template-columns: 1fr; }} }}

h2 {{ font-family: var(--display); font-weight: 600; font-size: 17px;
      margin: 0; }}
.intestazione-canale {{ display: flex; align-items: baseline; gap: 12px;
                        margin-bottom: 12px; }}
.orario {{ font-family: var(--mono); font-size: 12px; color: var(--accent-testo); }}

.striscia {{ display: grid; gap: 18px 16px;
             grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); }}
.slide {{ margin: 0; min-width: 0; }}
.slide img {{ width: 100%; max-width: 100%; display: block; border-radius: 6px;
              border: 1px solid var(--line); }}
figcaption {{ display: grid; gap: 4px; margin-top: 8px; }}
.num, .peso {{ font-family: var(--mono); font-size: 11px; color: var(--ink-soft); }}
.peso {{ justify-self: start; }}
.alt {{ font-size: 12.5px; color: var(--ink-soft); line-height: 1.45; }}

.canale + .canale {{ margin-top: 34px; }}
.cornice {{ background: var(--surface); border: 1px solid var(--line);
            border-radius: 10px; overflow: hidden; }}
.riga-profilo {{ display: flex; align-items: center; gap: 9px;
                 padding: 12px 14px; border-bottom: 1px solid var(--line); }}
.pallino {{ width: 26px; height: 26px; border-radius: 50%; }}
.pallino.quadro {{ border-radius: 4px; }}
.handle {{ font-weight: 600; font-size: 14px; }}
.posto-immagine img {{ width: 100%; display: block; }}
.corpo-cornice {{ padding: 14px; }}
.azioni {{ font-size: 12px; color: var(--ink-soft); margin: 0 0 10px; }}

.didascalia {{ margin: 0; white-space: normal; }}
.taglio {{ display: block; margin: 10px 0 8px; padding-top: 8px;
           border-top: 1px dashed var(--accent); font-family: var(--mono);
           font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
           color: var(--accent-testo); }}
.resto {{ color: var(--ink-soft); }}
.conteggio {{ font-family: var(--mono); font-size: 11px; color: var(--ink-soft);
              margin: 12px 0 0; }}

.tabs {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }}
.tab {{ font-family: var(--corpo); font-size: 13px; padding: 6px 12px;
        border: 1px solid var(--line); background: transparent;
        color: var(--ink-soft); border-radius: 999px; cursor: pointer; }}
.tab.attiva {{ border-color: var(--accent); color: var(--ink);
               background: color-mix(in srgb, var(--accent) 14%, transparent); }}
.tab:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.variante {{ display: none; }}
.variante.attiva {{ display: block; }}

.documento, .commento {{ padding: 13px 14px; border-top: 1px solid var(--line);
                         display: grid; gap: 5px; }}
.etichetta-doc, .etichetta-commento {{ font-family: var(--mono); font-size: 10.5px;
     letter-spacing: .1em; text-transform: uppercase; color: var(--ink-soft); }}
.titolo-doc {{ font-weight: 600; }}
.conta-doc {{ font-family: var(--mono); font-size: 11px; }}
.conta-doc.ok {{ color: var(--accent-testo); }}
.conta-doc.errore {{ color: var(--allarme); font-weight: 700; }}

.menzioni {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.menzioni th {{ text-align: left; font-family: var(--mono); font-size: 10.5px;
                letter-spacing: .09em; text-transform: uppercase;
                color: var(--ink-soft); border-bottom: 1px solid var(--line);
                padding: 0 8px 6px 0; }}
.menzioni td {{ padding: 7px 8px 7px 0; border-bottom: 1px solid var(--line);
                vertical-align: top; }}
.menzioni .urn, .menzioni .piattaforma {{ font-family: var(--mono);
      font-size: 11.5px; color: var(--accent-testo); word-break: break-all; }}
.menzioni .piattaforma {{ word-break: normal; }}
.menzioni .nome-tag {{ font-weight: 600; }}
.nessuna {{ margin: 0; font-size: 13.5px; }}
.dubbi {{ margin: 12px 0 0; padding-left: 18px; font-size: 13px;
          color: var(--ink-soft); }}
.dubbi li + li {{ margin-top: 6px; }}
.menzione {{ color: var(--menzione); font-weight: 600; }}
.menzioni .tipo, .nota-voce {{ font-family: var(--corpo); font-size: 11.5px;
      color: var(--ink-soft); font-weight: 400; word-break: normal; }}
.problemi {{ margin: 0 0 12px; padding-left: 18px; font-size: 13px;
             color: var(--allarme); font-weight: 600; }}
.problemi li + li {{ margin-top: 6px; }}
.sottotitolo {{ font-family: var(--mono); font-size: 10.5px; letter-spacing: .09em;
                text-transform: uppercase; color: var(--ink-soft); margin: 16px 0 6px; }}
.riga-tag {{ margin: 0; font-size: 13px; line-height: 1.5; padding: 9px 11px;
             border-left: 3px solid var(--accent); background: var(--ground); }}

code {{ font-family: var(--mono); font-size: 12px; }}

.nota {{ font-size: 12.5px; color: var(--ink-soft); margin: 10px 0 0;
         max-width: 60ch; }}
</style>

<div class="guscio">
  <header class="testata">
    <h1>{html.escape(spec.get('titolo', 'Anteprima'))}</h1>
    <span class="meta">{html.escape(spec.get('rubrica', ''))} · {len(slide)} slide
      · {html.escape(spec.get('cartella', ''))}</span>
  </header>

  <div class="impalcatura">
    <div>
      <div class="intestazione-canale"><h2>Il carosello</h2>
        <span class="orario">{html.escape(spec.get('ora_carosello', ''))}</span>
      </div>
      <div class="striscia">{''.join(figure)}</div>
      <p class="nota">Le slide nell'ordine di pubblicazione, alle proporzioni
      reali. Sotto ciascuna c'e' il testo alternativo che verra' inviato.</p>
      {sezione_storie(spec)}
    </div>
    <div>{sezione_ig}{sezione_li}{sezione_scartate(spec)}{sezione_menzioni(spec)}</div>
  </div>
</div>

<script>
document.querySelectorAll('.tab').forEach(function (b) {{
  b.addEventListener('click', function () {{
    var v = b.dataset.var;
    document.querySelectorAll('.tab').forEach(function (x) {{
      x.classList.toggle('attiva', x === b);
    }});
    document.querySelectorAll('.variante').forEach(function (x) {{
      x.classList.toggle('attiva', x.dataset.var === v);
    }});
  }});
}});
</script>
"""


# Le slide fisse in coda (manuale §4.4). Aggiunto il 13 ottobre 2026: quel giorno
# l'anteprima del Radar è arrivata a Simone senza «Manca una notizia?» e senza
# «segui», perché la spec elencava solo le slide del giorno e le fisse si accodavano
# solo su Metricool. Da qui in poi l'anteprima le aggiunge da sola, così mostra il
# carosello esattamente come esce.
FISSE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "media", "fisse")
ALT_SEGNALA = ("Slide su fondo carta avorio. Linguetta nera SEGNALATO DA VOI. Titolo grande: "
    "manca una notizia? Sotto: se oggi è successo qualcosa che qui non c'è, scrivilo nei "
    "commenti; la verifichiamo come tutte le altre e, se merita, domani è nel Radar con il tuo "
    "nome. Un bottone nero con scritto scrivilo nei commenti. In basso, in grigio: chi lavora "
    "dentro il mercato vede cose che da fuori non si vedono, questa rubrica serve a quello. "
    "Poi la firma at ictradar24 e il marchio.")
ALT_SEGUI = ("Slide di chiusura su fondo arancio, con titoli in avorio e testi in nero. In alto la "
    "testata ICT Radar 24 e la firma at ictradar24. Testo grande: un minuto al giorno per sapere "
    "che cosa è successo nel mondo ICT e tech, e nel business che lo muove. Sotto: il segnale, "
    "non il rumore; le notizie ICT e business che contano per chi decide, ogni giorno. Poi: se "
    "vuoi prenderti una pausa dalla frenesia e dal rumore, segui questa pagina, e un bottone nero "
    "con scritto segui ICT Radar 24. In basso: ictradar24.com e il marchio con il blip al centro.")
ALT_SEGUI_STORIA = ("Storia di chiusura su fondo arancio: un minuto al giorno per sapere che cosa è "
    "successo nel mondo ICT e tech, e nel business che lo muove. Il segnale, non il rumore. Se vuoi "
    "prenderti una pausa dalla frenesia e dal rumore, segui questa pagina, con il bottone segui "
    "ICT Radar 24 e il marchio.")


def aggiungi_fisse(spec):
    """Accoda le slide fisse se la spec non le ha già: segnala e segui sul carosello di
    Radar e Radar Italia, solo segui su Gartner e Virgolette, segui-storia sulle Storie."""
    rub = spec.get("rubrica", "radar")
    def ha(elenco, nome):
        return any(os.path.basename(p) == nome for p in elenco)
    slide = list(spec.get("slide", []))
    alt = list(spec.get("alt", []))
    alt += [""] * (len(slide) - len(alt))
    aggiunte = []
    if rub in ("radar", "italia", "radar-italia") and not ha(slide, "segnala-post.png"):
        slide.append(os.path.join(FISSE, "segnala-post.png")); alt.append(ALT_SEGNALA)
        aggiunte.append("segnala-post.png")
    if not ha(slide, "segui-post.png"):
        slide.append(os.path.join(FISSE, "segui-post.png")); alt.append(ALT_SEGUI)
        aggiunte.append("segui-post.png")
    spec["slide"], spec["alt"] = slide, alt
    storie = list(spec.get("storie", []))
    if storie and not ha(storie, "segui-storia.png"):
        salt = list(spec.get("storie_alt", []))
        salt += [""] * (len(storie) - len(salt))
        storie.append(os.path.join(FISSE, "segui-storia.png")); salt.append(ALT_SEGUI_STORIA)
        spec["storie"], spec["storie_alt"] = storie, salt
        aggiunte.append("segui-storia.png")
    for p in spec["slide"] + spec.get("storie", []):
        pieno = os.path.join(spec.get("base", ""), p) if spec.get("base") else p
        if not os.path.exists(pieno):
            sys.exit(f"Slide non trovata: {pieno}. Le fisse si prendono da media/fisse/ del clone.")
    if aggiunte:
        print("Slide fisse accodate: " + ", ".join(aggiunte))


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 anteprima.py spec.json [uscita.html]")
    with open(sys.argv[1], encoding="utf-8") as fh:
        spec = json.load(fh)
    aggiungi_fisse(spec)
    uscita = sys.argv[2] if len(sys.argv) > 2 else "anteprima.html"
    with open(uscita, "w", encoding="utf-8") as fh:
        fh.write(costruisci(spec))
    kb = os.path.getsize(uscita) // 1024
    print(f"Anteprima scritta: {uscita} ({kb} KB)")


if __name__ == "__main__":
    main()
