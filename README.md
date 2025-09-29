# HR Voice Screener – Hackathon MVP

A voice-first HR phone-screen prototype that:
- Converts **text→voice** (TTS) to ask questions,
- Converts **voice→text** (STT) to capture answers,
- Reads **Job Description + Resume + Past Tickets** to generate tailored questions,
- **Scores** answers (semantic similarity + rubric),
- Tracks **difficulty**,
- Provides a minimal **agent flow**,
- Uses **RAG** (ChromaDB + sentence-transformers) for document understanding.

---

## Features
1. **Text → Voice** using `pyttsx3` (offline voice).
2. **Voice → Text** using OpenAI Whisper API (or local `faster-whisper`).
3. **Question Generation** from JD + Resume (+ optional tickets via RAG).
4. **Difficulty** tagging for questions.
5. **Agent** flow to run the interview.
6. **RAG** over past tickets (PDF/TXT/MD) using ChromaDB.

---

## Tech
- **UI**: Streamlit + (optional) streamlit-webrtc
- **LLM**: Ollama(local) / OpenAI (gpt-4o-mini by default)
- **STT**: Whisper (`whisper-1`) or `faster-whisper`
- **TTS**: `pyttsx3` (swap to ElevenLabs/Azure preferred)
- **RAG**: sentence-transformers (`all-MiniLM-L6-v2`) + ChromaDB (local)

---

## Setup

```bash
git clone https://github.com/Rohan-flutterint/hr-voice-screen
cd hr-voice-screen
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set OPENAI_API_KEY
```

Put the documents here:
```
data/job_description.pdf
data/resume.pdf
data/tickets/*.pdf|.txt|.md   (optional)
```

---

## Run

```bash
streamlit run app_streamlit.py
```

**In the app:**
1. Sidebar → **Build RAG Index** (ingests JD/Resume/Tickets into Chroma).
2. Click **Generate Questions** (6–10 tailored Qs).
3. **Speak Question** to play TTS.
4. **Upload a .wav** answer (or type it).
5. **Transcribe Answer** → **Score Answer** → **Next Question**.
6. At the end, view **Summary** (overall & by-difficulty).

> Note: For simplicity, we use WAV upload (reliable cross-browser). We can wire live mic capture with `streamlit-webrtc` later.

---

## Switches
- Use local STT: in `.env`, set `USE_LOCAL_STT=true` (downloads a whisper model on first run).
- Use a different LLM: set `LLM_MODEL=gpt-4o` (or any available model).
- Use ElevenLabs/Azure TTS: set flags and add API keys; implement the call in `audio_io.py`.

---

## Scoring
- **Semantic** similarity (Sentence-BERT cosine) → 0–100
- **Rubric** (coverage/correctness/clarity 0–5 each) → scaled to 0–100
- **Final** = 0.6 × semantic + 0.4 × rubric

---

## Directory Structure
```
hr-voice-screen/
   app_streamlit.py
   agent.py
   rag_index.py
   scoring.py
   prompts.py
   llm_io.py
   audio_io.py
   utils.py
   requirements.txt
   .env.example
   data/
       job_description.pdf
       resume.pdf
       tickets/
   storage/
       chroma/                      #vector DB
```

---

## Notes
- OpenAI usage incurs cost; ensure the API key is active.
- `faster-whisper` runs locally but needs CPU/GPU and model download; default to API for fastest setup.
- On macOS, we will need microphone permissions if we wire live capture later.