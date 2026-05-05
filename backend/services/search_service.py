"""
search_service.py
=================
Visual similarity search using ResNet-50 + cosine similarity.

Dataset layout expected (flat folder — matches your existing setup):
    images/
        bags_001.jpg
        heels_042.jpg
        jeans_007.jpg
        ...   (filename must START with the category name)

Cache:
    features_cache.pkl  — auto-built on first run, reloaded on restart.

Dependencies:
    pip install torch torchvision scikit-learn Pillow
"""

import io
import os
import pickle

import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity

# ── Model setup ───────────────────────────────────────────────────────────────
model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
model = torch.nn.Sequential(*list(model.children())[:-1])   # strip classifier head
model.eval()

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE        = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(_HERE, "images")
CACHE_FILE   = os.path.join(_HERE, "features_cache.pkl")

# ── In-memory store ───────────────────────────────────────────────────────────
image_features:   list[np.ndarray] = []
image_paths:      list[str]        = []
image_categories: list[str]        = []

# ── Category helpers ──────────────────────────────────────────────────────────
KNOWN_CATEGORIES = [
    "bags", "heels", "jeans", "skirts",
    "sneakers", "tshirts", "wallets", "cafri",
]


def get_category(filename: str) -> str:
    """Infer category from the start of the filename, e.g. 'bags_001.jpg' → 'bags'."""
    lower = os.path.basename(filename).lower()
    for cat in KNOWN_CATEGORIES:
        if lower.startswith(cat):
            return cat
    return "other"


# ── Feature extraction ────────────────────────────────────────────────────────
def extract_features(image_bytes: bytes) -> np.ndarray:
    """Return a flat (2048,) float32 feature vector for raw image bytes."""
    image  = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = transform(image).unsqueeze(0)
    with torch.no_grad():
        features = model(tensor)
    return features.numpy().flatten()


# ── Dataset loader ────────────────────────────────────────────────────────────
def load_dataset() -> None:
    """
    Call once at FastAPI startup (inside the lifespan context).
    Loads from cache if available, otherwise scans images/ and builds cache.
    """
    global image_features, image_paths, image_categories

    # ── Try cache first ───────────────────────────────────────────────────────
    if os.path.exists(CACHE_FILE):
        print("📦 Cache found — loading features from disk...")
        try:
            with open(CACHE_FILE, "rb") as f:
                image_features, image_paths, image_categories = pickle.load(f)
            print(
                f"✅ Loaded {len(image_paths)} images from cache. "
                f"Categories: {set(image_categories)}"
            )
            return
        except Exception as e:
            print(f"⚠️  Cache corrupt ({e}), rebuilding from images...")
            image_features, image_paths, image_categories = [], [], []

    # ── Build from raw images ─────────────────────────────────────────────────
    print(f"🔍 Scanning dataset at: {DATASET_PATH}")
    if not os.path.isdir(DATASET_PATH):
        print(f"❌ Dataset path not found: {DATASET_PATH}  — start with an empty index.")
        return

    supported = (".jpg", ".jpeg", ".png", ".webp")
    img_names  = [
        f for f in os.listdir(DATASET_PATH)
        if f.lower().endswith(supported)
    ]
    print(f"   Found {len(img_names)} image files.")

    for img_name in img_names:
        path = os.path.join(DATASET_PATH, img_name)
        try:
            with open(path, "rb") as f:
                vec = extract_features(f.read())
            image_features.append(vec)
            image_paths.append(img_name)
            image_categories.append(get_category(img_name))
        except Exception as e:
            print(f"⚠️  Skipping {img_name}: {e}")

    print(
        f"✅ Extracted features for {len(image_paths)} images. "
        f"Categories: {set(image_categories)}"
    )

    # ── Persist cache ─────────────────────────────────────────────────────────
    try:
        with open(CACHE_FILE, "wb") as f:
            pickle.dump((image_features, image_paths, image_categories), f)
        print(f"💾 Cache saved → {CACHE_FILE}")
    except Exception as e:
        print(f"⚠️  Could not save cache: {e}")


# ── Search ────────────────────────────────────────────────────────────────────
def get_results(
    image_bytes: bytes,
    category:    str = "All",
    top_k:       int = 10,
) -> list[dict]:
    """
    Run visual similarity search.

    Returns a list of dicts:
        [{"image": "http://...", "score": 0.91, "category": "bags"}, ...]
    sorted by descending similarity, filtered to score > 0.3.
    """
    if not image_features:
        return []

    query_vec = extract_features(image_bytes)

    # ── Category filter ───────────────────────────────────────────────────────
    cat_lower = category.lower() if category else "all"
    if cat_lower not in ("all", ""):
        indices           = [i for i, c in enumerate(image_categories) if c == cat_lower]
        filtered_features = [image_features[i] for i in indices]
        filtered_paths    = [image_paths[i]     for i in indices]
    else:
        filtered_features = image_features
        filtered_paths    = image_paths

    if not filtered_features:
        return []

    # ── Cosine similarity ─────────────────────────────────────────────────────
    sims = cosine_similarity([query_vec], filtered_features)[0]
    ranked = sorted(zip(filtered_paths, sims), key=lambda x: x[1], reverse=True)[:top_k]

    return [
        {
            "image":    f"http://127.0.0.1:8000/images/{img}",
            "score":    float(score),
            "category": get_category(img),
        }
        for img, score in ranked
        if float(score) > 0.3
    ]


# ── Cache management ──────────────────────────────────────────────────────────
def rebuild_cache() -> dict:
    """
    Wipe the pickle cache and rebuild from scratch.
    Call via POST /rebuild (defined in main.py).
    """
    global image_features, image_paths, image_categories
    image_features, image_paths, image_categories = [], [], []
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    load_dataset()
    return {"rebuilt": True, "total": len(image_paths)}


def dataset_stats() -> dict[str, int]:
    """Return per-category image counts for the /stats endpoint."""
    from collections import Counter
    return dict(Counter(image_categories))
