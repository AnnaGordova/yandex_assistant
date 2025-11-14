import json
import ast
import re

def parse_agent_response(text):
    """
    Попытка распарсить ответ модели в структуру:
    - {"status":"ok","queries":[...]}
    - {"status":"questions","questions":[...]}
    Или fallback: {"status":"raw","raw_text": text}
    """
    if not text:
        return {"status":"raw", "raw_text": ""}

    # 1) пробуем JSON
    try:
        obj = json.loads(text)
        return obj
    except Exception:
        pass

    # 2) пробуем Python literal (модель иногда отдает single quotes)
    try:
        obj = ast.literal_eval(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 3) пытаемся вытащить блок JSON {...}
    m = re.search(r"(\{[\s\S]*\})", text)
    if m:
        s = m.group(1)
        try:
            obj = json.loads(s)
            return obj
        except Exception:
            try:
                obj = ast.literal_eval(s)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

    # 4) fallback: если текст содержит вопросы (строки с '?') — собрать их
    qlines = [line.strip() for line in text.splitlines() if "?" in line]
    if qlines:
        return {"status": "questions", "questions": qlines}

    # 5) пробуем найти фразы через строки (fallback)
    lines = [line.strip("-• \t") for line in text.splitlines() if line.strip()]
    # выделим короткие строки, похожие на запросы (heuristic: contain spaces, length>3)
    cand = [l for l in lines if len(l) > 3 and len(l.split()) >= 2]
    if cand:
        return {"status": "ok", "queries": cand}

    # окончательный fallback
    return {"status": "raw", "raw_text": text}