# Multi-Modal Evidence Review System

A robust damage-claim verification pipeline powered by **Groq Llama 4 Scout** (free tier).

## What it does

For each damage claim, the system:

1. **Parses** the user's chat conversation to extract what they're claiming (damage type, object part)
2. **Inspects** submitted images using Groq Llama 4 vision capabilities
3. **Checks** evidence sufficiency against the evidence-requirements checklist
4. **Evaluates** user history for risk context
5. **Decides** whether the claim is `supported`, `contradicted`, or `not_enough_information`
6. **Outputs** a structured row with justification, risk flags, severity, and supporting image IDs

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

Get a **free** API key from [Groq Console](https://console.groq.com/keys).

```bash
# Linux / macOS
export GROQ_API_KEYS="key1,key2,key3"

# Windows PowerShell
$env:GROQ_API_KEYS = "key1,key2,key3"
```
*(You can pass multiple comma-separated keys to enable automatic Key Rotation!)*

### 3. Run on the test set

```bash
python main.py
```

This reads `dataset/claims.csv` and writes `output.csv` at the repo root.

### 4. Run on the sample set (for development)

```bash
python main.py --sample
```

### 5. Evaluate

```bash
python evaluation/main.py
```

This processes `sample_claims.csv`, compares against expected outputs, and generates `evaluation/evaluation_report.md`.

## Architecture

```
code/
├── main.py              # Main pipeline (entry point)
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── README.md            # This file
└── evaluation/
    ├── main.py           # Evaluation script
    └── evaluation_report.md   # Generated after evaluation run
```

### Pipeline design

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│ Load claim   │────▶│ Load images  │────▶│ Build prompt  │
│ + user hist  │     │ (1-3 per     │     │ (claim +      │
│ + ev. reqs   │     │  claim)      │     │  context)     │
└─────────────┘     └──────────────┘     └──────┬────────┘
                                                │
                                                ▼
                    ┌──────────────┐     ┌───────────────┐
                    │ Validate &   │◀────│ Groq Llama 4  │
                    │ normalise    │     │ VLM           │
                    │ output       │     │ (JSON mode)   │
                    └──────┬───────┘     └───────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Write CSV    │
                    │ output row   │
                    └──────────────┘
```

### Key design decisions

**1. Prompt Engineering & Reasoning**
- **One VLM call per claim** – all images sent together for holistic analysis
- **Structured JSON output** – uses Groq's `response_format={"type": "json_object"}` for reliable parsing
- **Chain-of-Thought (CoT)** – The model generates a `reasoning` field first, forcing it to analyze severity and image content before returning its final decision.
- **Calibrated Risk & Severity** – Specific strict definitions for severity and risk flags were added to prevent model hallucinations and over-flagging.

**2. Resilience & Reliability**
- **Validation & Consistency Enforcement** – A strict validation layer normalizes all VLM outputs and enforces logical consistency (e.g. `valid_image = false` instantly triggers `claim_status = not_enough_information`).
- **Model Fallback Chain** – Automatically rotates through working Groq Llama 4 models (Scout, Maverick) if one hits its rate limits.
- **API Key Rotation** – If all models exhaust their free quota on one API key, the system automatically rotates to the next API key in `GROQ_API_KEYS`.
- **Persistent Error Handling** – 5 retries with exponential backoff for 503 Server Unavailable errors, successfully exhausting failing models without crashing.
- **Rate limiting** – 2.0s between requests (safe within 60 RPM free tier).

## Configuration

| Env variable | Default | Description |
|---|---|---|
| `GROQ_API_KEYS` | *(required)* | Comma-separated list of Groq API keys |
| `GROQ_MODEL` | `meta-llama/llama-4-scout-17b-16e-instruct` | Primary Groq model identifier |

## Cost

**$0** – uses the Groq free tier with automatic model rotation to stay within quotas.
