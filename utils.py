from rag_index import _read_any

def load_texts(jd_path, resume_path):
    jd = _read_any(jd_path)
    rs = _read_any(resume_path)
    return jd, rs