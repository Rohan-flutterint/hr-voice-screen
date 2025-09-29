import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from llm_io import chat_json
from prompts import SYSTEM_RUBRIC, USER_RUBRIC

_model = None
def _emb():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def semantic_similarity(a, b):
    if not a.strip() or not b.strip():
        return 0.0
    em = _emb()
    va = em.encode([a]); vb = em.encode([b])
    sim = float(cosine_similarity(va, vb)[0][0])  # -1..1
    sim = max(0.0, (sim + 1)/2)                  # 0..1
    return sim * 100.0

def rubric_score(question, ideal, cand):
    js = chat_json(SYSTEM_RUBRIC, USER_RUBRIC.format(
        question=question, ideal_answer=ideal, candidate_answer=cand
    ))
    cov = js.get("coverage",0); cor = js.get("correctness",0); cla = js.get("clarity",0)
    total15 = cov + cor + cla
    feedback = js.get("feedback","");
    followup = js.get("followup","");
    return (total15/15.0)*100.0, {"coverage":cov,"correctness":cor,"clarity":cla,"feedback":feedback,"followup":followup}

def final_score(question, ideal, cand):
    sem = semantic_similarity(cand, ideal)
    rub, details = rubric_score(question, ideal, cand)
    final = 0.6*sem + 0.4*rub
    return round(final,1), round(sem,1), round(rub,1), details