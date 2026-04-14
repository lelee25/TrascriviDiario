"""Preview HTML con copia multi-formato negli appunti (plain/HTML/RTF)."""

from __future__ import annotations

import json
import webbrowser
from datetime import datetime
from pathlib import Path


def _esc(text: str) -> str:
    """Escape HTML minimo."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("\n", "<br>")
    )


def _testo_to_rtf(testo: str) -> str:
    """Converte testo plain in RTF minimale per il clipboard.

    Genera un RTF semplice con font Calibri — adatto per incollare in
    gestionali che accettano text/rtf dal clipboard.
    """
    def _rtf_esc(t: str) -> str:
        out = []
        for ch in t:
            cp = ord(ch)
            if ch == "\\":
                out.append("\\\\")
            elif ch == "{":
                out.append("\\{")
            elif ch == "}":
                out.append("\\}")
            elif ch == "\n":
                out.append("\\line\n")
            elif cp > 127:
                # RTF \uN richiede signed 16-bit integer (spec RTF 1.9).
                # Per codepoint > 32767 va sottratto 65536.
                signed = cp if cp <= 32767 else cp - 65536
                out.append(f"\\u{signed}?")
            else:
                out.append(ch)
        return "".join(out)

    body = _rtf_esc(testo)
    return (
        r"{\rtf1\ansi\ansicpg1252\deff0"
        r"{\fonttbl{\f0\fswiss\fcharset0 Calibri;}}"
        r"\paperw11906\paperh16838\margl720\margr720\margt720\margb720"
        r"{\pard \ql \f0 \fs24 \sa80 "
        + body
        + r"\par}}"
    )


def genera_html(
    testo: str,
    titolo: str = "",
    autore: str = "",
    data: str | None = None,
) -> str:
    """Genera pagina HTML con preview testo e pulsante copia multi-formato.

    Il clipboard riceve 3 formati simultaneamente tramite handler oncopy:
    - text/rtf     → gestionale medico / Delphi
    - text/html    → Word, Outlook, Mail (stili inline)
    - text/plain   → textarea, editor semplici

    Args:
        testo: Testo trascritto e normalizzato.
        titolo: Titolo del documento (es. "Visita del paziente X").
        autore: Nome del medico/autore.
        data: Data in formato stringa. Se None usa la data odierna.
    """
    data_str = data or datetime.now().strftime("%d/%m/%Y %H:%M")
    rtf_content = _testo_to_rtf(testo)

    # HTML per clipboard (stili inline per compatibilità Word/Outlook)
    header_html = ""
    if titolo or autore:
        header_html = (
            '<div style="font-size:13px;color:#555;margin-bottom:12px;'
            'border-bottom:1px solid #ddd;padding-bottom:6px;">'
        )
        if titolo:
            header_html += f'<strong>{_esc(titolo)}</strong> &nbsp;'
        if autore:
            header_html += f'{_esc(autore)} &nbsp;'
        header_html += f'<span style="color:#888;">{data_str}</span></div>'

    clipboard_html = (
        '<div style="font-family:Calibri,Arial,sans-serif;font-size:13px;'
        'line-height:1.6;color:#212529;max-width:720px;">'
        + header_html
        + f'<p style="white-space:pre-wrap;">{_esc(testo)}</p>'
        + '</div>'
    )

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>{_esc(titolo) if titolo else "Trascrizione"}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, 'Segoe UI', Calibri, sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 30px;
    background: #f8f9fa;
    color: #212529;
  }}
  .header {{
    text-align: center;
    border-bottom: 3px solid #1A5C8A;
    padding-bottom: 12px;
    margin-bottom: 20px;
  }}
  .header h1 {{ font-size: 20px; color: #1A5C8A; }}
  .header .meta {{ font-size: 12px; color: #666; margin-top: 4px; }}
  .card {{
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 16px;
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-wrap: break-word;
  }}
  .actions {{
    position: sticky;
    bottom: 0;
    background: #fff;
    border-top: 1px solid #dee2e6;
    padding: 12px 0;
    margin-top: 16px;
    display: flex;
    gap: 10px;
    justify-content: center;
  }}
  .btn {{
    padding: 11px 28px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }}
  .btn-copy {{
    background: #1A5C8A;
    color: white;
    box-shadow: 0 2px 8px rgba(26,92,138,0.3);
  }}
  .btn-copy:hover {{ background: #144A70; }}
  .btn-copy.copied {{ background: #2E7D32; }}
  .toast {{
    display: none;
    position: fixed;
    bottom: 70px;
    left: 50%;
    transform: translateX(-50%);
    background: #2E7D32;
    color: white;
    padding: 10px 24px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 13px;
    z-index: 1000;
  }}
  .footer {{
    text-align: center;
    font-size: 11px;
    color: #b45309;
    background: #fff8ed;
    border: 1px dashed #e5b878;
    border-radius: 6px;
    padding: 8px 12px;
    margin-top: 12px;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>{_esc(titolo) if titolo else "Trascrizione Vocale"}</h1>
  <div class="meta">
    {(_esc(autore) + " &middot; ") if autore else ""}Data: {data_str}
  </div>
</div>

<div class="card">{_esc(testo)}</div>

<div class="footer">
  &#9888; Testo generato da trascrizione vocale automatica.
  Verificare sempre il contenuto prima dell'uso.
</div>

<div class="actions">
  <button class="btn btn-copy" id="btnCopy" onclick="copyAll()">
    📋 Copia Testo
  </button>
</div>

<div id="toast" class="toast">✓ Copiato negli appunti!</div>

<script>
const rtfContent  = {json.dumps(rtf_content, ensure_ascii=False)};
const htmlContent = {json.dumps(clipboard_html, ensure_ascii=False)};
const plainContent = {json.dumps(testo, ensure_ascii=False)};
let alreadyCopied = false;

function onCopyHandler(e) {{
  e.preventDefault();
  e.clipboardData.setData("text/rtf",   rtfContent);
  e.clipboardData.setData("application/rtf", rtfContent);
  e.clipboardData.setData("text/html",  htmlContent);
  e.clipboardData.setData("text/plain", plainContent);
}}
document.addEventListener("copy", onCopyHandler);

function triggerCopy() {{
  const sel = window.getSelection();
  sel.removeAllRanges();
  const range = document.createRange();
  range.selectNodeContents(document.getElementById("copyAnchor"));
  sel.addRange(range);
  const ok = document.execCommand("copy");
  sel.removeAllRanges();
  return ok;
}}

function copyAll() {{
  if (triggerCopy()) {{
    markCopied();
    showToast("✓ Copiato! Incolla dove ti serve");
  }} else {{
    showToast("⚠ Usa Ctrl+C per copiare");
  }}
}}

function markCopied() {{
  alreadyCopied = true;
  const btn = document.getElementById("btnCopy");
  btn.textContent = "✓ Già negli appunti";
  btn.classList.add("copied");
}}

function showToast(msg) {{
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.style.display = "block";
  setTimeout(() => {{ t.style.display = "none"; }}, 2200);
}}

// Auto-copia al primo click ovunque (user gesture richiesta dal browser)
document.addEventListener("click", function firstClick(e) {{
  if (alreadyCopied || e.target.id === "btnCopy") return;
  if (triggerCopy()) markCopied();
}}, true);
</script>

<div id="copyAnchor" style="position:fixed;left:-9999px;top:-9999px;opacity:0;">.</div>
</body>
</html>"""

    return html


def apri_preview(
    testo: str,
    titolo: str = "",
    autore: str = "",
    data: str | None = None,
) -> Path:
    """Genera HTML, salva in output/ e apre nel browser.

    Returns:
        Path del file HTML generato.
    """
    html = genera_html(testo, titolo=titolo, autore=autore, data=data)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = titolo.replace(" ", "_").lower()[:30] if titolo else "trascrizione"
    out = Path("output") / f"{safe}_{ts}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    webbrowser.open(f"file://{out.resolve()}")
    return out
