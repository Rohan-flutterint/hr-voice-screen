from prompts import SYSTEM_QUESTION_GEN, USER_QUESTION_GEN
from rag_index import query
from llm_io import chat_json

def generate_questions(jd_text, resume_text, role_hint=""):
    tickets_snips = query(f"{role_hint or 'relevant tickets'} for screening", k=5)
    joined = "\n---\n".join([f"[{src}] {doc[:600]}" for doc, src in tickets_snips])
    js = chat_json(SYSTEM_QUESTION_GEN, USER_QUESTION_GEN.format(
        jd=jd_text[:6000], resume=resume_text[:6000], tickets=joined[:4000]
    ))
    if isinstance(js, list):
        return js
    return js.get("questions", [])

class HRFlow:
    def __init__(self, questions):
        self.questions = questions
        self.idx = 0
        self.results = []

    def has_next(self):
        return self.idx < len(self.questions)

    def current(self):
        return self.questions[self.idx] if self.has_next() else None

    def accept_answer(self, transcript, score_tuple, details):
        q = self.current()
        self.results.append({
            "question": q.get("question",""),
            "difficulty": q.get("difficulty",""),
            "ideal_answer": q.get("ideal_answer",""),
            "candidate_answer": transcript,
            "score": score_tuple[0],
            "sem_score": score_tuple[1],
            "rubric_score": score_tuple[2],
            "rubric_details": details
        })
        self.idx += 1

    def summary(self):
        if not self.results:
            return {"overall": 0.0, "by_difficulty":{}, "items":[]}
        overall = sum(r["score"] for r in self.results)/len(self.results)
        by_diff = {}
        for r in self.results:
            d = r.get("difficulty") or "unknown"
            by_diff.setdefault(d, []).append(r["score"])
        by_diff = {k: round(sum(v)/len(v),1) for k,v in by_diff.items()}
        return {"overall": round(overall,1), "by_difficulty": by_diff, "items": self.results}