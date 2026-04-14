"""Post-processing LLM: correzione conservativa di errori di trascrizione ASR.

Basato sul pattern RLLM-CF (arXiv:2505.24347): prompt ultra-restrittivo con
temperature=0 e regola del dubbio ("se non sei sicuro, lascia invariato").

Posizione nel pipeline:
    Audio -> trascrivi() -> normalizza() -> preview/clipboard
"""

from __future__ import annotations

from openai import OpenAI

from diario.config import DEFAULT_LLM_MODEL


_SYSTEM_PROMPT = """Sei un editor specializzato nella correzione di errori di trascrizione vocale automatica (ASR) in italiano.

Il tuo UNICO compito e' correggere errori EVIDENTI di trascrizione fonetica, ovvero parole che il riconoscimento vocale ha sbagliato per somiglianza sonora.

CORREGGERE SOLO:
- Parole o nomi trascritti male per confusione fonetica (es. "polpite" → "pulpite", "enimesolide" → "nimesulide")
- Terminologia distorta foneticamente (es. "testa del freddo" → "test del freddo", "endodonsia" → "endodonzia")
- Acronimi o codici distorti (es. "K0 2.51" → "K02.51")

DIVIETI ASSOLUTI:
- NON riformulare, NON ristrutturare, NON parafrasare frasi
- NON aggiungere informazioni non presenti nel testo originale
- NON rimuovere informazioni presenti nel testo originale
- NON cambiare valori numerici: dosaggi, parametri vitali, date, durate, frequenze
- NON cambiare nomi propri di persone, pazienti, medici, strutture sanitarie
- NON correggere grammatica, punteggiatura o stile — solo errori fonetici ASR
- NON aggiungere punteggiatura dove non c'era

REGOLA DEL DUBBIO: se non sei assolutamente certo che sia un errore fonetico, LASCIA INVARIATO. E' sempre preferibile lasciare un possibile errore che correggere qualcosa di corretto.

OUTPUT: restituisci SOLO il testo corretto. Nessun commento, nessuna spiegazione."""


def normalizza(
    testo: str,
    api_key: str | None = None,
    model: str = DEFAULT_LLM_MODEL,
) -> str:
    """Corregge errori fonetici di trascrizione ASR in un testo italiano.

    Args:
        testo: Testo da correggere.
        api_key: Chiave API OpenAI. Se None usa env var OPENAI_API_KEY.
        model: Modello LLM. Default DEFAULT_LLM_MODEL.

    Returns:
        Testo corretto. In caso di errore restituisce il testo originale
        (fail-safe: meglio testo grezzo che testo alterato).
    """
    if not testo or not testo.strip():
        return testo

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": testo},
            ],
            temperature=0,
            # Stima token: ~1 token ogni 4 char per italiano.
            # Il testo corretto non dovrebbe essere piu' lungo dell'originale,
            # quindi `tokens_input + 20%` e' un upper bound generoso.
            # Cap a 4096 per evitare sprechi su testi molto lunghi.
            max_tokens=min(max(len(testo) // 4 + 200, 256), 4096),
        )
        corrected = (response.choices[0].message.content or "").strip()

        if not corrected or len(corrected) < len(testo) * 0.5:
            return testo

        return corrected

    except Exception:
        return testo
