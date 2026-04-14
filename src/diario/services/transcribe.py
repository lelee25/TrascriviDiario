"""Trascrizione audio via OpenAI (gpt-4o-transcribe)."""

from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from diario.config import DEFAULT_WHISPER_MODEL


# Prompt narrativo (best practice OpenAI Cookbook): una frase coerente guida
# il decoding meglio di un glossario sintetico. Stimato ~170 token, entro
# il limite di 224 del tokenizer multilingual di Whisper/gpt-4o-transcribe.
DEFAULT_PROMPT = (
    "Registrazione vocale in italiano. Il parlante detta testo, note, appunti "
    "o diari clinici. Esempio: Paziente riferisce dolore. Pressione 130/85 mmHg, "
    "frequenza cardiaca 72 bpm, saturazione 98 percento. Diagnosi K02.51, I10. "
    "Prescrivo nimesulide 100 mg, ibuprofene 600 mg, amoxicillina e acido "
    "clavulanico 1 g ogni 12 ore, paracetamolo 1000 mg, ramipril 5 mg, "
    "omeprazolo 20 mg, metformina 500 mg, cardioaspirina 100 mg, warfarin. "
    "Terminologia: carie occlusale, test del freddo, test di percussione, "
    "endodonzia, pulpite acuta reversibile, gengivite, sopragengivale, "
    "intarsio in composito, eugenolo, mucose rosee, linfonodi, auscultazione."
)


def trascrivi(
    audio_path: str | Path,
    api_key: str | None = None,
    language: str = "it",
    prompt: str | None = None,
    model: str | None = None,
) -> str:
    """Trascrive un file audio usando OpenAI.

    Args:
        audio_path: Path del file audio (WAV, MP3, M4A, OGG, FLAC, WEBM).
        api_key: Chiave API OpenAI. Se None usa env var OPENAI_API_KEY.
        language: Codice lingua ISO-639-1 (default "it").
        prompt: Prompt di steering. Se None usa DEFAULT_PROMPT.
        model: Modello trascrizione. Se None usa DEFAULT_WHISPER_MODEL.

    Returns:
        Testo trascritto.

    Raises:
        ValueError: se la trascrizione e' vuota o se viene rilevato prompt
            leakage (bug noto di gpt-4o-transcribe su audio silenzioso).
    """
    client = OpenAI(api_key=api_key)
    used_prompt = prompt or DEFAULT_PROMPT
    used_model = model or DEFAULT_WHISPER_MODEL

    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model=used_model,
            file=f,
            language=language,
            prompt=used_prompt,
            response_format="text",
        )

    result = response.strip() if isinstance(response, str) else ""

    if not result:
        raise ValueError(
            "Nessuna voce rilevata nell'audio. "
            "Riprova parlando piu' vicino al microfono."
        )

    _guard_prompt_leakage(result, used_prompt)
    return result


def _guard_prompt_leakage(transcription: str, prompt: str) -> None:
    """Rileva il bug di gpt-4o-transcribe che su audio silenzioso restituisce
    il prompt come trascrizione invece del parlato reale."""
    if not transcription or not prompt:
        return

    norm_t = " ".join(transcription.lower().split())
    norm_p = " ".join(prompt.lower().split())

    if norm_t == norm_p:
        raise ValueError(
            "Audio non udibile: il modello ha restituito il prompt di esempio. "
            "Riprova la registrazione."
        )

    leakage_markers = (
        "registrazione vocale in italiano. il parlante detta",
        "esempio: paziente riferisce dolore",
    )
    for marker in leakage_markers:
        if marker in norm_t:
            raise ValueError(
                "Rilevato prompt leakage (audio silenzioso o troppo corto). "
                "Riprova la registrazione."
            )
