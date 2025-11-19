import json
from web_agent.web_tools import get_saved_candidates


def candidate_to_product(idx: int, cand: dict) -> dict:
    """
    Преобразовать один saved candidate из RESULT_STORE в Product для Go.
    """
    desc_str = cand.get("description") or "{}"

    try:
        desc = json.loads(desc_str)
        if not isinstance(desc, dict):
            desc = {}
    except Exception:
        desc = {}

    def _float(key, default=0.0):
        v = desc.get(key, default)
        try:
            return float(v)
        except Exception:
            return default

    def _int(key, default=0):
        v = desc.get(key, default)
        try:
            return int(v)
        except Exception:
            return default

    price = _float("price", 0.0)
    rating = _float("rating", 0.0)
    reviews = _int("ammountOfReviews", 0)
    size = desc.get("size") or ""
    count = _int("countOfProduct", 1)

    return {
        "id": int(idx),
        "name": cand.get("product_name", ""),
        "link": cand.get("url", ""),
        # Сохраняем исходный JSON как строку — бэку будет удобно парсить
        "description": desc_str,
        "price": price,
        "picture": cand.get("image_url") or "",
        "rating": rating,
        "ammountOfReviews": reviews,
        "size": size,
        "countOfProduct": count,
    }


def candidates_to_products() -> list[dict]:
    """
    Забрать все сохранённые кандидаты у web-агента и привести к Go Product.
    """
    raw = get_saved_candidates(clear=True)  # {index: {...}}
    products: list[dict] = []
    for idx, cand in raw.items():
        products.append(candidate_to_product(idx, cand))
    # Можно отсортировать по id, чтобы порядок был предсказуем
    products.sort(key=lambda p: p["id"])
    return products
