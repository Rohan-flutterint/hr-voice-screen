# audio_io.py
import os, io, tempfile

# --- Optional deps (import safely so app never crashes at import time) ---
try:
    import pyttsx3          # offline TTS via NSSpeech (macOS)
except Exception:
    pyttsx3 = None

try:
    import soundfile as sf  # to re-encode WAVs
except Exception:
    sf = None

# ---------------- Env knobs ----------------
USE_LOCAL_STT = os.getenv("USE_LOCAL_STT", "false").lower() == "true"

# Default to a natural female macOS voice
VOICE_NAME = os.getenv("TTS_VOICE", "Samantha").strip()   # e.g., Samantha, Ava, Allison, Zoe
TTS_RATE   = int(os.getenv("TTS_RATE", "170"))            # 150–190 tends to sound natural

# --------------- TTS helpers ----------------
_tts_engine = None

def _tts_init():
    """
    Try to initialize pyttsx3 (macOS nsss driver). If pyobjc isn't installed or anything fails,
    return None so we can use the `say` fallback instead.
    """
    global _tts_engine
    if _tts_engine is not None:
        return _tts_engine

    if pyttsx3 is None:
        return None

    try:
        eng = pyttsx3.init()  # nsss on macOS
        try:
            eng.setProperty("rate", TTS_RATE)
        except Exception:
            pass

        # Try to pick a requested voice (match by name or id, case-insensitive).
        # On mac, Samantha id often looks like: com.apple.speech.synthesis.voice.samantha
        if VOICE_NAME:
            try:
                for v in eng.getProperty("voices"):
                    vname = (v.name or "").lower()
                    vid   = (getattr(v, "id", "") or "").lower()
                    target = VOICE_NAME.lower()
                    if target in vname or target in vid:
                        eng.setProperty("voice", getattr(v, "id", v.name))
                        break
            except Exception:
                pass

        _tts_engine = eng
        return _tts_engine
    except Exception:
        # pyttsx3 failed (often due to missing pyobjc). We'll use the mac 'say' fallback.
        return None


def _tts_silence_wav(duration_sec: float = 0.5) -> bytes:
    """Return a valid WAV of silence so the UI never breaks even if TTS fails."""
    import wave, struct
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        nchannels, sampwidth, framerate = 1, 2, 16000
        nframes = int(duration_sec * framerate)
        w.setnchannels(nchannels)
        w.setsampwidth(sampwidth)
        w.setframerate(framerate)
        for _ in range(nframes):
            w.writeframes(struct.pack("<h", 0))
    return buf.getvalue()


def tts_to_wav_bytes(text: str) -> bytes:
    """
    Make speech WAV bytes for `text`, preferring:
      1) pyttsx3 (offline) with selected voice (Samantha default),
      2) macOS `say` with -v VOICE and -r RATE as a robust fallback,
      3) a short silent WAV if both paths fail.
    """
    # --- 1) pyttsx3 path ---
    try:
        eng = _tts_init()
        if eng is not None and sf is not None:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp = f.name
            try:
                eng.save_to_file(text, tmp)
                eng.runAndWait()
                data, sr = sf.read(tmp, dtype="int16")
                out = io.BytesIO()
                sf.write(out, data, sr, format="WAV")
                return out.getvalue()
            finally:
                try: os.remove(tmp)
                except Exception: pass
    except Exception:
        # fall through to 'say' fallback
        pass

    # --- 2) macOS `say` fallback (very reliable on Mac) ---
    try:
        import subprocess
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as fa:
            aiff_path = fa.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fw:
            wav_path = fw.name
        try:
            cmd = ["say"]
            if VOICE_NAME:
                cmd += ["-v", VOICE_NAME]   # <- picks Samantha (or whatever you set)
            cmd += ["-r", str(TTS_RATE), "-o", aiff_path, text]
            subprocess.run(cmd, check=True)

            # Convert AIFF -> WAV using built-in afconvert
            subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", aiff_path, wav_path], check=True)

            with open(wav_path, "rb") as f:
                return f.read()
        finally:
            for p in (aiff_path, wav_path):
                try: os.remove(p)
                except Exception: pass
    except Exception:
        pass

    # --- 3) Last resort: valid silent WAV ---
    return _tts_silence_wav()


# ----------------- OpenAI client (lazy) for cloud STT if enabled -----------------
def _get_openai_client():
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to .env or export it.")
    from openai import OpenAI
    return OpenAI(api_key=key)


# ----------------- STT: WAV bytes -> text -----------------
def transcribe_wav_bytes(wav_bytes: bytes) -> str:
    """
    If USE_LOCAL_STT=true (default in your setup), use faster-whisper (offline).
    Otherwise use OpenAI Whisper API.
    """
    if USE_LOCAL_STT:
        from faster_whisper import WhisperModel
        model = WhisperModel("small")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            path = f.name
        try:
            segments, _ = model.transcribe(path)
            return " ".join(s.text for s in segments).strip()
        finally:
            try: os.remove(path)
            except Exception: pass
    else:
        client = _get_openai_client()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            path = f.name
        try:
            with open(path, "rb") as audio_file:
                tr = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
            return tr.text.strip()
        finally:
            try: os.remove(path)
            except Exception: pass
