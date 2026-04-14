"""REST API FastAPI per integrazione con Delphi 13."""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from diario.config import DEFAULT_LLM_MODEL, DEFAULT_WHISPER_MODEL
from diario.services.transcribe import trascrivi
from diario.services.normalize import normalizza
from diario.services.preview import genera_html

app = FastAPI(
    title="Diario API",
    description="Trascrizione vocale con correzione automatica. Per integrazione con Delphi 13.",
    version="0.1.0",
)


# ===== Response models =====

class TrascrizioneResponse(BaseModel):
    trascrizione: str
    """Testo trascritto e corretto pronto per l'incolla nel gestionale."""


# ===== Endpoints =====

@app.get("/health")
def health():
    """Verifica che il server sia attivo e la API key configurata."""
    return {
        "status": "ok",
        "openai_configured": bool(os.environ.get("OPENAI_API_KEY")),
        "whisper_model": DEFAULT_WHISPER_MODEL,
        "llm_model": DEFAULT_LLM_MODEL,
    }


@app.post("/trascrivi", response_model=TrascrizioneResponse)
async def trascrivi_endpoint(
    audio: UploadFile = File(..., description="File audio (WAV, MP3, M4A, OGG, FLAC, WEBM)"),
    language: str = Form("it"),
    modello: str = Form(DEFAULT_LLM_MODEL),
):
    """Endpoint principale Delphi: POST audio → GET testo trascritto e corretto.

    Il testo restituito e' gia' normalizzato (errori fonetici corretti).
    Pronto per essere incollato direttamente nel campo del gestionale.
    """
    api_key = _get_api_key()

    async with _upload_to_tempfile(audio) as tmp_path:
        try:
            testo = await run_in_threadpool(
                trascrivi, tmp_path, api_key=api_key, language=language
            )
            testo = await run_in_threadpool(
                normalizza, testo, api_key=api_key, model=modello
            )
            return TrascrizioneResponse(trascrizione=testo)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/trascrivi-html", response_class=HTMLResponse)
async def trascrivi_html_endpoint(
    audio: UploadFile = File(..., description="File audio"),
    titolo: str = Form(""),
    autore: str = Form(""),
    language: str = Form("it"),
    modello: str = Form(DEFAULT_LLM_MODEL),
):
    """Variante: restituisce direttamente la pagina HTML preview con clipboard.

    Utile se Delphi vuole aprire una WebView con la preview integrata.
    """
    api_key = _get_api_key()

    async with _upload_to_tempfile(audio) as tmp_path:
        try:
            testo = await run_in_threadpool(
                trascrivi, tmp_path, api_key=api_key, language=language
            )
            testo = await run_in_threadpool(
                normalizza, testo, api_key=api_key, model=modello
            )
            html = genera_html(testo, titolo=titolo, autore=autore)
            return HTMLResponse(content=html)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# ===== Helpers =====

@asynccontextmanager
async def _upload_to_tempfile(audio: UploadFile) -> AsyncIterator[Path]:
    """Salva UploadFile in tempfile e lo elimina all'uscita (threadpool-safe)."""
    content = await audio.read()

    def _write() -> str:
        with tempfile.NamedTemporaryFile(
            suffix=_ext(audio.filename), delete=False
        ) as tmp:
            tmp.write(content)
            return tmp.name

    tmp_name = await run_in_threadpool(_write)
    tmp_path = Path(tmp_name)
    try:
        yield tmp_path
    finally:
        await run_in_threadpool(tmp_path.unlink, missing_ok=True)


def _get_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY non configurata sul server"
        )
    return key


def _ext(filename: str | None) -> str:
    if not filename:
        return ".wav"
    ext = Path(filename).suffix.lower()
    return ext if ext in (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm") else ".wav"
