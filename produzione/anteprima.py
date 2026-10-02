#!/usr/bin/env python3
"""ICT RADAR 24 — Generatore di anteprime (copia dal Progetto)."""

import base64, html, json, os, sys

RUBRICHE = {
    "radar": "#00D8C4", "italia": "#00A868", "allerta": "#FFB020",
    "segnalato": "#00D8C4", "sulradar": "#7B5CFF", "puntodivista": "#00D8C4",
    "virgolette": "#8C97A8", "topdelmese": "#F4F6F9", "gartner": "#7B5CFF",
    "cofano": "#7B5CFF",
}

TAGLIO_IG = 125
TAGLIO_LI = 140
LIMITE_DOC_TITLE = 58


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


def blocco_didascalia(testo, limite, etichetta_taglio):
    visibile, nascosto = spezza(testo, limite)
    out = [f'<p class="didascalia">{testo_html(visibile)}']
    if nascosto:
        out.append(f'<span class="taglio">... {etichetta_taglio}</span>')
        out.append(f'<span class="resto">{testo_html(nascosto)}</span>')
    out.append("</p>")
    return "".join(out)


def sezione_menzioni(spec):
    m = spec.get("menzioni")
    if m is None:
        return ""
    voci = m.get("elenco", [])
    dubbi = m.get("dubbi", [])
    if voci:
        righe = "".join(
            f'<tr><td class="piattaforma">{html.escape(v.get("piattaforma", ""))}</td>'
            f'<td class="nome-tag">{html.escape(v.get("nome", ""))}</td>'
            f'<td class="urn">{html.escape(v.get("urn", ""))}</td></tr>'
            for v in voci)
        tabella = (f'<table class="menzioni"><thead><tr><th>Dove</th>'
                   f'<th>Nome visualizzato</th><th>Identificativo che pubblica</th>'
                   f'</tr></thead><tbody>{righe}</tbody></table>')
    else:
        tabella = ('<p class="nessuna">Nessuna menzione in questo pezzo: '
                   'nel testo i nomi restano senza chiocciola.</p>')
    lista_dubbi = ""
    if dubbi:
        lista_dubbi = ("<ul class=\"dubbi\">" +
                       "".join(f"<li>{html.escape(d)}</li>" for d in dubbi) +
                       "</ul>")
    return f"""
    <section class="canale" id="menzioni">
      <header class="intestazione-canale"><h2>Menzioni</h2></header>
      <div class="cornice"><div class="corpo-cornice">
        {tabella}{lista_dubbi}
      </div></div>
      <p class="nota">L'approvazione cade sull'identificativo, non sul nome:
      il nome visualizzato lo scriviamo noi e puo' puntare altrove.</p>
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
            f'{blocco_didascalia(v.get("testo", ""), TAGLIO_LI, "vedi altro")}'
            f'<p class="conteggio">{len(v.get("testo", ""))} caratteri</p></div>'
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
          {blocco_didascalia(li.get('primoCommento', ''), 250, 'vedi altro')}
        </div>
      </div>
      <p class="nota">LinkedIn taglia intorno ai {TAGLIO_LI} caratteri su
      telefono. Il titolo del documento compare sopra il carosello e oltre i
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
.menzioni .nome-tag {{ font-weight: 600; }}
.nessuna {{ margin: 0; font-size: 13.5px; }}
.dubbi {{ margin: 12px 0 0; padding-left: 18px; font-size: 13px;
          color: var(--ink-soft); }}
.dubbi li + li {{ margin-top: 6px; }}

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
    <div>{sezione_ig}{sezione_li}{sezione_menzioni(spec)}</div>
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


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 anteprima.py spec.json [uscita.html]")
    with open(sys.argv[1], encoding="utf-8") as fh:
        spec = json.load(fh)
    uscita = sys.argv[2] if len(sys.argv) > 2 else "anteprima.html"
    with open(uscita, "w", encoding="utf-8") as fh:
        fh.write(costruisci(spec))
    kb = os.path.getsize(uscita) // 1024
    print(f"Anteprima scritta: {uscita} ({kb} KB)")


if __name__ == "__main__":
    main()
