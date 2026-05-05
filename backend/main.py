"""
main.py
=======
FastAPI backend for the Visual Search app.

Endpoints:
    GET  /              — health check
    POST /search        — visual similarity search
    POST /price_search  — cross-platform price comparison (SerpAPI)
    GET  /stats         — per-category image counts
    POST /rebuild       — wipe & rebuild the feature cache
    GET  /images/{name} — static image serving

Run:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Dependencies:
    pip install fastapi uvicorn[standard] python-multipart \
                torch torchvision scikit-learn Pillow \
                google-search-results python-dotenv
"""

import os
import re
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from serpapi import GoogleSearch          # pip install google-search-results

from search_service import (
    dataset_stats,
    get_results,
    load_dataset,
    rebuild_cache,
)

# ── Env ───────────────────────────────────────────────────────────────────────
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
IMAGES_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

PLATFORM_MAP = {
    "amazon":   "amazon",
    "flipkart": "flipkart",
    "myntra":   "myntra",
    "meesho":   "meesho",
    "ajio":     "ajio",
    "nykaa":    "nykaa",
}

# Category → human-readable label used in search queries
CATEGORY_LABELS = {
    "bags":     "women handbag",
    "heels":    "women heels sandals",
    "jeans":    "women jeans",
    "skirts":   "women skirt",
    "sneakers": "sneakers shoes",
    "tshirts":  "women t-shirt top",
    "wallets":  "women wallet purse",
    "cafri":    "women capri pants",
    "other":    "fashion clothing",
}

# ══════════════════════════════════════════════════════════════════════════════
# Lifespan
# ══════════════════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting up — loading dataset …")
    load_dataset()
    print("✅ Dataset ready.")
    yield
    print("👋 Shutting down.")


app = FastAPI(title="Visual Search API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.isdir(IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
else:
    print(f"⚠️  images/ not found at {IMAGES_DIR}. /images route disabled.")


# ══════════════════════════════════════════════════════════════════════════════
# Schemas
# ══════════════════════════════════════════════════════════════════════════════
class PriceQuery(BaseModel):
    image_url: str
    category:  str = ""


# ══════════════════════════════════════════════════════════════════════════════
# Price-search helpers
# ══════════════════════════════════════════════════════════════════════════════
def _parse_price(raw) -> Optional[float]:
    """Safely coerce Rs.1,299 / 1299.0 / None -> float or None."""
    if raw is None:
        return None
    try:
        cleaned = re.sub(r"[^\d.]", "", str(raw))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def _map_platform(source: str) -> str:
    src = source.lower()
    for key, name in PLATFORM_MAP.items():
        if key in src:
            return name
    return "other"


def _is_local_url(url: str) -> bool:
    """Return True if the URL points to localhost — SerpAPI cannot reach these."""
    try:
        host = urlparse(url).hostname or ""
        return host in ("localhost", "127.0.0.1", "0.0.0.0") or host.startswith("192.168.")
    except Exception:
        return True


def _build_search_query(image_url: str, category: str) -> str:
    """
    Build the most specific Google Shopping query possible from the image URL.

    Priority:
      1. Keywords extracted from the image filename
         e.g. 'bags_red_leather_tote_001.jpg' -> 'women handbag red leather tote buy online india'
      2. Category label only
         e.g. 'women handbag buy online india'
      3. Generic fallback
    """
    cat_lower = (category or "").lower().strip()

    # Extract filename (without extension) from the URL
    filename  = os.path.splitext(os.path.basename(urlparse(image_url).path))[0]

    # Split on underscores, hyphens, digits and collect meaningful words
    raw_words = re.split(r"[_\-\d]+", filename)
    stopwords = {
        "img", "image", "photo", "pic", "product", "item",
        "new", "copy", "final", "orig", "thumb", "small", "large",
        *CATEGORY_LABELS.keys(),   # strip bare category names; we add the label back
    }
    keywords = [
        w.lower() for w in raw_words
        if len(w) >= 3 and w.lower() not in stopwords
    ]

    cat_label = CATEGORY_LABELS.get(cat_lower, "")

    if keywords and cat_label:
        query = f"{cat_label} {' '.join(keywords[:4])} buy online india"
    elif cat_label:
        query = f"{cat_label} buy online india"
    elif keywords:
        query = f"{' '.join(keywords[:5])} buy online india"
    else:
        query = "fashion clothing buy online india"

    print(f"[price_search] query={query!r}  file={filename!r}  cat={cat_lower!r}")
    return query


def _shopping_search(query: str) -> list[dict]:
    """Google Shopping text search — primary strategy when images are local."""
    if not SERPAPI_KEY:
        print("[price_search] WARNING: SERPAPI_KEY is not set in .env")
        return []
    try:
        params = {
            "engine":  "google_shopping",
            "q":       query,
            "gl":      "in",
            "hl":      "en",
            "api_key": SERPAPI_KEY,
            "num":     10,
        }
        raw = GoogleSearch(params).get_dict().get("shopping_results", [])
        print(f"[price_search] Shopping returned {len(raw)} raw results.")
    except Exception as e:
        print(f"[price_search] SerpAPI error: {e}")
        return []

    output = []
    for r in raw:
        price = _parse_price(r.get("extracted_price") or r.get("price"))
        if price is None:
            continue
        mrp = _parse_price(r.get("extracted_old_price") or r.get("old_price"))
        output.append({
            "platform": _map_platform(r.get("source", "")),
            "name":     r.get("title", "")[:120],
            "price":    price,
            "mrp":      mrp if (mrp and mrp > price) else None,
            "currency": "INR",
            "url":      r.get("link") or r.get("product_link") or "#",
            "in_stock": True,
            "rating":   _parse_price(r.get("rating")),
            "reviews":  r.get("reviews"),
        })
    return output


def _lens_search(image_url: str) -> list[dict]:
    """
    Google Lens visual search.
    Only works when image_url is publicly reachable (not localhost).
    """
    if not SERPAPI_KEY:
        return []
    try:
        params = {
            "engine":  "google_lens",
            "url":     image_url,
            "api_key": SERPAPI_KEY,
            "hl":      "en",
            "country": "in",
        }
        data    = GoogleSearch(params).get_dict()
        matches = data.get("visual_matches", [])
        print(f"[price_search] Lens returned {len(matches)} visual matches.")
    except Exception as e:
        print(f"[price_search] Lens error: {e}")
        return []

    output = []
    for m in matches:
        raw_price = m.get("price", {})
        price = _parse_price(
            raw_price.get("extracted_value")
            if isinstance(raw_price, dict) else raw_price
        )
        if price is None:
            continue
        output.append({
            "platform": _map_platform(m.get("source", "")),
            "name":     m.get("title", "")[:120],
            "price":    price,
            "mrp":      None,
            "currency": "INR",
            "url":      m.get("link", "#"),
            "in_stock": True,
            "rating":   None,
            "reviews":  None,
        })
    return output


def _deduplicate(results: list[dict]) -> list[dict]:
    """Keep only the cheapest listing per platform, sorted cheapest first."""
    best: dict[str, dict] = {}
    for item in results:
        plat = item["platform"]
        if plat not in best or item["price"] < best[plat]["price"]:
            best[plat] = item
    return sorted(best.values(), key=lambda x: x["price"])


# ══════════════════════════════════════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
async def health():
    return {"status": "ok", "message": "Visual Search API is running"}


@app.post("/search")
async def search(
    file:     UploadFile = File(...),
    category: str        = Form("All"),
    top_k:    int        = Form(10),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    results = get_results(image_bytes, category=category, top_k=top_k)
    return JSONResponse(content={"results": results})


@app.post("/price_search")
async def price_search(q: PriceQuery):
    """
    Decision tree:
      Local URL  (127.0.0.1 / localhost)
        -> skip Lens (it can't reach local servers)
        -> keyword Shopping query built from filename + category

      Public URL
        -> try Lens first (visual, most accurate)
        -> fall back to keyword Shopping if Lens returns nothing

    Returns [] only if SERPAPI_KEY is missing or SerpAPI itself errors out.
    Check the uvicorn terminal for [price_search] log lines to debug.
    """
    if _is_local_url(q.image_url):
        query   = _build_search_query(q.image_url, q.category)
        results = _shopping_search(query)
    else:
        results = _lens_search(q.image_url)
        if not results:
            query   = _build_search_query(q.image_url, q.category)
            results = _shopping_search(query)

    return JSONResponse(content=_deduplicate(results))


@app.get("/stats")
async def stats():
    return JSONResponse(content=dataset_stats())


@app.post("/rebuild")
async def rebuild():
    result = rebuild_cache()
    return JSONResponse(content=result)


@app.get("/images/{image_name}")
async def serve_image(image_name: str):
    path = os.path.join(IMAGES_DIR, image_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(path)
