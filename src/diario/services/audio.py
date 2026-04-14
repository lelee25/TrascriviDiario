"""Registrazione audio da microfono."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wav
import sounddevice as sd

DEFAULT_SAMPLE_RATE = 44100
DEFAULT_CHANNELS = 1


def registra(
    durata_sec: int | None = None,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    output_path: str | Path | None = None,
) -> Path:
    """Registra audio dal microfono e salva in WAV.

    Args:
        durata_sec: Secondi di registrazione. None = continua fino a Ctrl+C.
        sample_rate: Sample rate in Hz.
        output_path: Path output WAV. Se None usa un file temporaneo.

    Returns:
        Path del file WAV salvato.
    """
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        output_path = Path(tmp.name)
        tmp.close()
    else:
        output_path = Path(output_path)

    print("[REC] Registrazione avviata... (Ctrl+C per fermare)")

    if durata_sec:
        audio = sd.rec(
            int(durata_sec * sample_rate),
            samplerate=sample_rate,
            channels=DEFAULT_CHANNELS,
            dtype=np.int16,
        )
        sd.wait()
        print(f"[REC] Registrazione completata ({durata_sec}s)")
    else:
        frames = []

        def callback(indata, frames_count, time_info, status):
            frames.append(indata.copy())

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=DEFAULT_CHANNELS,
                dtype=np.int16,
                callback=callback,
            ):
                while True:
                    sd.sleep(100)
        except KeyboardInterrupt:
            print("\n[REC] Registrazione fermata")

        if not frames:
            raise RuntimeError("Nessun audio registrato")

        audio = np.concatenate(frames, axis=0)

    audio = np.squeeze(audio)
    wav.write(str(output_path), sample_rate, audio)
    print(f"[REC] Salvato: {output_path}")
    return output_path
