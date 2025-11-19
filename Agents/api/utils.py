# utils.py
import json
from typing import Any, Dict, List

from Agents.web_agent.web_tools import get_saved_candidates


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def candidate_to_product(idx: int, cand: Dict[str, Any]) -> Dict[str, Any]:
    """
    Преобразует одного кандидата из RESULT_STORE в Product для Go.
    cand["description"] может быть как dict, так и строкой.
    """
    raw_desc = cand.get("description")

    # 1. Приводим к dict + строке
    if isinstance(raw_desc, dict):
        desc = raw_desc
        desc_str = json.dumps(desc, ensure_ascii=False)
    elif isinstance(raw_desc, str):
        try:
            parsed = json.loads(raw_desc)
            desc = parsed if isinstance(parsed, dict) else {}
        except Exception:
            desc = {}
        desc_str = raw_desc
    else:
        desc = {}
        desc_str = ""

    price = _to_float(desc.get("price", 0.0), 0.0)
    rating = _to_float(desc.get("rating", 0.0), 0.0)
    reviews = _to_int(desc.get("ammountOfReviews", 0), 0)
    size = desc.get("size") or ""
    count = _to_int(desc.get("countOfProduct", 1), 1)

    return {
        "id": int(idx),
        "name": cand.get("product_name", ""),
        "link": cand.get("url", ""),
        # Go ждёт строку, поэтому description — JSON-строка
        "description": desc_str,
        "price": price,
        "picture": cand.get("image_url") or "",
        "rating": rating,
        "ammountOfReviews": reviews,
        "size": size,
        "countOfProduct": count,
    }


def candidates_to_products(clear: bool = True) -> List[Dict[str, Any]]:
    """
    Забирает всех сохранённых кандидатов у web-агента и приводит к Go Product.
    """
    raw = get_saved_candidates(clear=clear)  # {index: {...}}
    products: List[Dict[str, Any]] = []

    for idx, cand in raw.items():
        products.append(candidate_to_product(idx, cand))

    products.sort(key=lambda p: p["id"])
    return products
