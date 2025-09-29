import os, re
import chromadb
from chromadb.utils import embedding_functions
from PyPDF2 import PdfReader

DB_DIR = "storage/chroma"
COLLECTION = "hr_docs"

def _read_any(path):
    if path.lower().endswith(".pdf"):
        try:
            txt = ""
            for p in PdfReader(path).pages:
                txt += p.extract_text() or ""
            return txt
        except Exception:
            return ""
    else:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

def chunk_text(t, maxlen=800):
    t = re.sub(r"\s+"," ", t).strip()
    return [t[i:i+maxlen] for i in range(0, len(t), maxlen)]

def get_chroma():
    client = chromadb.PersistentClient(path=DB_DIR)
    emb = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    col = client.get_or_create_collection(name=COLLECTION, embedding_function=emb)
    return col

def ingest(paths):
    col = get_chroma()
    docs, ids, metas = [], [], []
    counter = 0
    for path in paths:
        raw = _read_any(path)
        if not raw:
            continue
        for ch in chunk_text(raw):
            docs.append(ch)
            ids.append(f"doc-{counter}")
            metas.append({"source": os.path.basename(path)})
            counter += 1
    if docs:
        col.add(documents=docs, ids=ids, metadatas=metas)
    return counter

def query(q, k=5):
    col = get_chroma()
    res = col.query(query_texts=[q], n_results=k)
    docs = res.get("documents",[[]])[0]
    metas = res.get("metadatas",[[]])[0]
    return [(d, m.get("source","")) for d, m in zip(docs, metas)]