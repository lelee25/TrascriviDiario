"""Configurazione centrale di Diario."""

from __future__ import annotations

import os

DEFAULT_WHISPER_MODEL: str = os.environ.get("DIARIO_WHISPER_MODEL", "gpt-4o-transcribe")
"""Modello OpenAI per trascrizione audio.

Default: gpt-4o-transcribe (WER ~2.5% su benchmark 2025-2026, 4x meglio di
whisper-1). Stesso endpoint /v1/audio/transcriptions, supporta parametro prompt.
Override via env var DIARIO_WHISPER_MODEL.
"""

DEFAULT_LLM_MODEL: str = os.environ.get("DIARIO_LLM_MODEL", "gpt-5.4-mini")
"""Modello LLM per correzione post-ASR.

Default: gpt-5.4-mini (OpenAI, marzo 2026). Usato con temperature=0 e prompt
ultra-restrittivo: corregge solo errori fonetici evidenti senza alterare il testo.
Override via env var DIARIO_LLM_MODEL.
"""
