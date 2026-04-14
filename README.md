# TrascriviDiario

Trascrizione vocale in italiano con correzione automatica degli errori fonetici ASR.

**Pipeline:** registrazione microfono → `gpt-4o-transcribe` (WER 2.5%) → normalizzazione `gpt-5.4-mini` (temperature=0) → preview HTML + clipboard multi-formato (RTF + HTML + plain).

---

## Avvio rapido

```bash
git clone https://github.com/lelee25/TrascriviDiario.git
cd TrascriviDiario
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env
# → apri .env e inserisci OPENAI_API_KEY=sk-...
```

## Comandi CLI

```bash
diario parla                        # registra da microfono (Ctrl+C per fermare)
diario audio /path/to/file.m4a      # da file audio esistente
diario server                       # avvia API REST su http://127.0.0.1:8910
```

## Modelli OpenAI da abilitare

Sulla dashboard del progetto OpenAI (Settings → Project → Models), abilitare:

- `gpt-4o-transcribe` — trascrizione audio
- `gpt-5.4-mini` — correzione post-ASR

## API REST (per Delphi e altri client)

Avviare il server con `diario server`, poi:

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/health` | GET | Stato server e API key |
| `/trascrivi` | POST | Audio → testo corretto (JSON) |
| `/trascrivi-html` | POST | Audio → pagina HTML con preview e clipboard |

Esempio curl:
```bash
curl -X POST http://127.0.0.1:8910/trascrivi \
  -F "audio=@registrazione.m4a" \
  -F "language=it"
```

Risposta:
```json
{ "trascrizione": "Il paziente riferisce dolore toracico da tre giorni..." }
```

## Clipboard multi-formato

Quando si clicca **Copia Testo** nella preview browser, gli appunti ricevono simultaneamente:

- `text/rtf` → gestionale medico / Delphi
- `text/html` → Word, Outlook, Mail (con formattazione)
- `text/plain` → textarea, editor semplici

Il programma di destinazione sceglie automaticamente il formato più appropriato.

## API key

Il file `.env` **non è nel repo** (è in `.gitignore`). Ogni collaboratore crea il proprio `.env` locale.

Per un team, creare una **Project API Key** dedicata dalla dashboard OpenAI (Settings → API Keys → Create new key) con solo i modelli necessari abilitati — più sicuro di condividere la key personale.

---

## Riscrivere in Delphi 13 nativo

Il codice Python in `src/diario/` è la specifica funzionale completa per una versione nativa Delphi 13. Il collega può clonare il repo, aprire Claude Code e usare il prompt seguente:

```
Leggi il progetto Python in questa repo (src/diario/).
È un sistema di trascrizione vocale che:
1. Registra audio dal microfono
2. Invia a OpenAI /v1/audio/transcriptions (modello gpt-4o-transcribe)
3. Corregge gli errori fonetici con /v1/chat/completions (gpt-5.4-mini, temperature=0)
4. Mostra il risultato in un'interfaccia con copia multi-formato negli appunti
   (RTF + HTML + plain text simultaneamente)

Riscrivi l'intero progetto come applicazione nativa Delphi 13 (VCL o FMX).
Usa TRESTClient per le chiamate OpenAI, Windows waveIn API per la registrazione,
TEdgeBrowser per la preview HTML, TClipboard per il multi-formato.
La OPENAI_API_KEY va letta da un file .env o da una configurazione locale.
Non usare il server FastAPI — l'app Delphi chiama OpenAI direttamente.
```

### Equivalenze Python → Delphi 13

| Componente Python | Equivalente Delphi 13 |
|---|---|
| `gpt-4o-transcribe` via OpenAI SDK | `TRESTClient` + `TRESTRequest` (multipart upload) |
| `gpt-5.4-mini` normalizzazione | `TNetHTTPClient` POST JSON |
| Registrazione microfono | Windows `waveIn` API o `TPortAudio` via DLL |
| Clipboard RTF + HTML + plain | `TClipboard` + `OpenClipboard`/`SetClipboardData` Win32 |
| Preview HTML | `TEdgeBrowser` (Chromium embedded, Delphi 12+) |
| FastAPI REST server | Non serve — l'app chiama OpenAI direttamente |

### Struttura progetto Delphi generata da Claude Code

```
TrascriviDiario.dpr
├── forms/
│   ├── FormMain.pas/.dfm      ← UI principale: TMemo, TButton, TEdgeBrowser
│   └── FormSettings.pas/.dfm  ← Configurazione API key
├── services/
│   ├── AudioRecorder.pas      ← wrapper waveIn (~150 righe Pascal)
│   ├── OpenAIClient.pas       ← chiamate REST trascrivi + normalizza
│   └── ClipboardHelper.pas    ← clipboard multi-formato Win32
└── config/
    └── AppConfig.pas          ← lettura .env / INI
```

### Note importanti per Delphi

**Registrazione audio** — la parte più complessa. Richiede Windows API (`waveInOpen`, `waveInAddBuffer`, `waveInStart`) o un componente terze parti. Claude Code può scrivere il wrapper completo.

**Clipboard multi-formato** — richiede codice Win32 manuale (`OpenClipboard`, `SetClipboardData`). Non c'è un wrapper VCL nativo per RTF + HTML + plain simultaneamente, ma Claude Code lo sa implementare.

### Approccio ibrido consigliato (per iniziare subito)

Se il collega vuole un'UI Delphi funzionante rapidamente senza riscrivere il backend:

```
Delphi UI → HTTP POST → diario server (Python locale) → OpenAI
```

Il server Python (`diario server`) gira in background su `http://127.0.0.1:8910`. Delphi chiama `/trascrivi` e riceve il testo già corretto. Poi, in parallelo, si migra a versione full-native.

Vantaggi:
- Funziona subito senza riscrivere nulla
- UI Delphi testabile con backend già validato
- La migrazione a full-native diventa un refactor, non un rewrite da zero
