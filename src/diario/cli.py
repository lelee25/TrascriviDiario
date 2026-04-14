"""CLI Diario — trascrizione vocale con correzione automatica."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from diario.config import DEFAULT_LLM_MODEL
from diario.services.audio import registra
from diario.services.transcribe import trascrivi
from diario.services.normalize import normalizza
from diario.services.preview import apri_preview

app = typer.Typer(help="Diario — trascrizione vocale con correzione automatica")
console = Console()


def _need_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        console.print("[red]OPENAI_API_KEY non impostata. Crea un file .env con la chiave.[/red]")
        raise typer.Exit(1)
    return key


def _pipeline(
    audio_path: str | Path,
    titolo: str,
    autore: str,
    modello: str,
    api_key: str,
) -> None:
    """Trascrivi -> Normalizza -> Preview browser + clipboard."""
    try:
        console.print("[bold cyan]Trascrizione...[/bold cyan]")
        testo = trascrivi(audio_path, api_key=api_key)

        console.print("[bold cyan]Correzione automatica...[/bold cyan]")
        testo = normalizza(testo, api_key=api_key, model=modello)

        console.print(Panel(
            testo[:800] + ("..." if len(testo) > 800 else ""),
            title="Testo trascritto e corretto",
            border_style="green",
        ))

        html_path = apri_preview(testo, titolo=titolo, autore=autore)
        console.print(f"\n[bold green]Preview aperta nel browser[/bold green]")
        console.print(f"[dim]{html_path}[/dim]")
        console.print("[dim]Clicca 'Copia Testo' per copiare RTF+HTML+plain negli appunti[/dim]")
    except Exception as e:
        console.print(f"[red]Errore: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def parla(
    titolo: str = typer.Option("", "--titolo", "-t", help="Titolo/descrizione del contenuto"),
    autore: str = typer.Option("", "--autore", "-a", help="Nome autore/medico"),
    durata: int = typer.Option(0, "--durata", "-d", help="Secondi di registrazione (0 = Ctrl+C)"),
    modello: str = typer.Option(DEFAULT_LLM_MODEL, "--modello", help="Modello LLM correzione"),
):
    """Registra dal microfono, trascrivi e correggi. Apre preview nel browser."""
    api_key = _need_api_key()

    if not autore:
        autore = Prompt.ask("Autore (invio per saltare)", default="")

    console.print("\n[bold cyan]Registrazione audio[/bold cyan]")
    console.print("[dim]Parla nel microfono. Ctrl+C per fermare.[/dim]\n")

    try:
        wav_path = registra(durata_sec=durata if durata > 0 else None)
    except Exception as e:
        console.print(f"[red]Errore registrazione: {e}[/red]")
        raise typer.Exit(1)

    try:
        _pipeline(wav_path, titolo, autore, modello, api_key)
    finally:
        wav_path.unlink(missing_ok=True)


@app.command()
def audio(
    percorso: str = typer.Argument(help="Percorso file audio (WAV, MP3, M4A...)"),
    titolo: str = typer.Option("", "--titolo", "-t", help="Titolo/descrizione"),
    autore: str = typer.Option("", "--autore", "-a", help="Nome autore/medico"),
    modello: str = typer.Option(DEFAULT_LLM_MODEL, "--modello", help="Modello LLM correzione"),
):
    """Trascrivi un file audio esistente. Apre preview nel browser."""
    api_key = _need_api_key()

    if not Path(percorso).exists():
        console.print(f"[red]File non trovato: {percorso}[/red]")
        raise typer.Exit(1)

    _pipeline(percorso, titolo, autore, modello, api_key)


@app.command()
def server(
    host: str = typer.Option("127.0.0.1", help="Host binding"),
    port: int = typer.Option(8910, help="Porta"),
    reload: bool = typer.Option(False, help="Auto-reload per sviluppo"),
):
    """Avvia il server REST API per integrazione con Delphi."""
    import uvicorn
    console.print(f"[bold green]Server avviato su http://{host}:{port}[/bold green]")
    console.print(f"[dim]Docs: http://{host}:{port}/docs[/dim]")
    uvicorn.run("diario.api:app", host=host, port=port, reload=reload)
