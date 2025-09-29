import os, json, streamlit as st
from dotenv import load_dotenv
load_dotenv()


from streamlit_webrtc import webrtc_streamer, WebRtcMode
from audio_io import tts_to_wav_bytes, transcribe_wav_bytes
from rag_index import ingest
from utils import load_texts
from agent import generate_questions, HRFlow
from scoring import final_score



st.set_page_config(page_title="HR Voice Screener", page_icon="🎙️", layout="centered")
st.title("🎙️ HR Voice Screener")

with st.sidebar:
    st.header("Setup")
    jd_path = st.text_input("Job Description file", "data/job_description.pdf")
    resume_path = st.text_input("Resume file", "data/resume.pdf")
    tickets_dir = "data/tickets"
    if st.button("Build RAG Index"):
        files = []
        if os.path.exists(jd_path): files.append(jd_path)
        if os.path.exists(resume_path): files.append(resume_path)
        if os.path.isdir(tickets_dir):
            for root, _, fnames in os.walk(tickets_dir):
                for f in fnames:
                    if f.lower().endswith((".pdf",".txt",".md")):
                        files.append(os.path.join(root,f))
        added = ingest(files)
        st.success(f"Ingested {added} chunks into Chroma.")

if "flow" not in st.session_state:
    st.session_state.flow = None

col1, col2 = st.columns(2)
with col1:
    if st.button("Generate Questions"):
        jd, rs = load_texts(jd_path, resume_path)
        qs = generate_questions(jd, rs, role_hint="screening")
        if not qs:
            st.error("No questions generated. Check your API key or documents.")
        else:
            st.session_state.flow = HRFlow(qs)
            st.success(f"Prepared {len(qs)} questions.")

with col2:
    if st.button("Reset"):
        st.session_state.flow = None
        st.rerun()

def play_tts(text):
    wav = tts_to_wav_bytes(text)
    st.audio(wav, format="audio/wav")

if st.session_state.flow:
    qobj = st.session_state.flow.current()
    if qobj:
        st.subheader("Current Question")
        st.write(f"**Q:** {qobj.get('question','')}")
        st.caption(f"Difficulty: {qobj.get('difficulty','n/a')}  |  Tags: {', '.join(qobj.get('tags',[])) if qobj.get('tags') else '—'}")
        if st.button("🔊 Speak Question"):
            play_tts(qobj.get('question',''))

        st.markdown("**Answer (record/upload):**")
        st.info("For reliability, please upload a small WAV file. Live mic capture via WebRTC can be wired later.")

        audio_bytes = st.file_uploader("Upload a .wav answer", type=["wav"])

        transcript = st.text_area("Candidate Transcript (auto or manual)", height=140, placeholder="Click Transcribe or type manually...")

        if st.button("Transcribe Answer"):
            if audio_bytes is not None:
                text = transcribe_wav_bytes(audio_bytes.read())
                st.success("Transcribed uploaded audio.")
                st.session_state["last_transcript"] = text
            else:
                st.warning("Please upload a WAV for now (simple for hackathon)." )

        if "last_transcript" in st.session_state and st.session_state["last_transcript"]:
            transcript = st.session_state["last_transcript"]
            st.text_area("Candidate Transcript (auto)", value=transcript, height=140)

        manual_text = st.text_area("Or type answer here", height=120)

        if st.button("Score Answer"):
            ans = (manual_text or st.session_state.get("last_transcript"," ")).strip()
            if not ans:
                st.error("Provide an answer by voice or text.")
            else:
                score, sem, rub, details = final_score(qobj.get("question",""), qobj.get("ideal_answer",""), ans)
                st.metric("Final Score", f"{score}/100")
                st.caption(f"Semantic: {sem}/100 | Rubric: {rub}/100")
                with st.expander("Rubric Details"):
                    st.json(details)
                st.session_state.flow.accept_answer(ans, (score,sem,rub), details)

        if st.button("Next Question ➡️"):
            st.session_state.flow.idx += 1
            st.session_state.pop("last_transcript", None)
            st.rerun()
    else:
        st.subheader("Summary")
        summ = st.session_state.flow.summary()
        st.metric("Overall", f"{summ['overall']}/100")
        st.write("**By Difficulty**")
        st.json(summ["by_difficulty"])
        st.write("**Per Question Details**")
        st.json(summ["items"])