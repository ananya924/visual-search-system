import io
import time
import requests
import pandas as pd
import streamlit as st
from PIL import Image

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Visual Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
if "search_history"    not in st.session_state: st.session_state.search_history    = []
if "dark_mode"         not in st.session_state: st.session_state.dark_mode          = True
if "total_searches"    not in st.session_state: st.session_state.total_searches     = 0
if "all_scores"        not in st.session_state: st.session_state.all_scores         = []
if "modal_item"        not in st.session_state: st.session_state.modal_item         = None
if "modal_open"        not in st.session_state: st.session_state.modal_open         = False
if "price_cache"       not in st.session_state: st.session_state.price_cache        = {}
if "expanded_card"     not in st.session_state: st.session_state.expanded_card      = None

# ══════════════════════════════════════════════════════════════════════════════
# THEME
# ══════════════════════════════════════════════════════════════════════════════
DM = st.session_state.dark_mode

THEME = {
    "bg":       "#080810" if DM else "#f2f2f8",
    "surface":  "#10101a" if DM else "#ffffff",
    "surface2": "#18182a" if DM else "#ebebf6",
    "border":   "#252538" if DM else "#d8d8e8",
    "text":     "#e8e8f2" if DM else "#14141e",
    "muted":    "#606080" if DM else "#8888a0",
    "accent":   "#7c6af7",
    "accent2":  "#a78bfa",
    "grad1":    "#7c6af7",
    "grad2":    "#f472b6",
    "grad3":    "#38bdf8",
    "card_bg":  "#13131e" if DM else "#ffffff",
    "shimmer1": "#1c1c28" if DM else "#e8e8f0",
    "shimmer2": "#24243a" if DM else "#d8d8e8",
    "deal":     "#22c55e",
    "deal_bg":  "#0d2a18" if DM else "#d1fae5",
    "warn":     "#f59e0b",
}
T = THEME

PLATFORM_COLORS = {
    "amazon":   {"bg": "#FF9900", "text": "#000", "icon": "🛒"},
    "flipkart": {"bg": "#2874F0", "text": "#fff", "icon": "🛍️"},
    "myntra":   {"bg": "#FF3F6C", "text": "#fff", "icon": "👗"},
    "meesho":   {"bg": "#9B2CC6", "text": "#fff", "icon": "📦"},
    "ajio":     {"bg": "#1A1A1A", "text": "#fff", "icon": "✨"},
    "nykaa":    {"bg": "#FC2779", "text": "#fff", "icon": "💄"},
    "other":    {"bg": "#444",    "text": "#fff", "icon": "🛒"},
}

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {{
    --bg:       {T['bg']};
    --surface:  {T['surface']};
    --surface2: {T['surface2']};
    --border:   {T['border']};
    --text:     {T['text']};
    --muted:    {T['muted']};
    --accent:   {T['accent']};
    --accent2:  {T['accent2']};
    --card:     {T['card_bg']};
    --deal:     {T['deal']};
    --deal-bg:  {T['deal_bg']};
    --radius:   16px;
    --radius-sm:10px;
}}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="block-container"] {{
    background: var(--bg) !important;
    font-family: 'Outfit', sans-serif !important;
    color: var(--text) !important;
}}
[data-testid="stSidebar"] {{
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
    padding-top: 0 !important;
}}
[data-testid="stSidebar"] * {{ color: var(--text) !important; }}
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"] {{ display:none !important; }}
::-webkit-scrollbar {{ width:5px; }}
::-webkit-scrollbar-track {{ background:var(--bg); }}
::-webkit-scrollbar-thumb {{ background:var(--border); border-radius:3px; }}

@keyframes gradMove {{
    0%   {{ background-position: 0% 50%; }}
    50%  {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}
.grad-bg {{
    position: fixed; inset: 0; z-index: -1;
    background: linear-gradient(-45deg,
        {T['bg']}, {'#0d0820' if DM else '#f0eeff'},
        {'#0a1520' if DM else '#eef6ff'},
        {'#140d20' if DM else '#fff0f8'});
    background-size: 400% 400%;
    animation: gradMove 18s ease infinite;
    pointer-events: none;
}}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
.sb-brand {{ padding:24px 20px 16px; border-bottom:1px solid var(--border); margin-bottom:8px; }}
.sb-brand .logo {{
    font-size:1.15rem; font-weight:800; letter-spacing:-0.03em;
    background: linear-gradient(135deg, {T['grad1']}, {T['grad2']});
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
.sb-brand .tagline {{ font-size:.72rem; color:var(--muted); margin-top:2px; }}
.sb-section {{
    font-size:.65rem; font-weight:700; letter-spacing:.12em;
    text-transform:uppercase; color:var(--muted); padding:16px 4px 6px;
}}

/* ── Analytics ───────────────────────────────────────────────────────────── */
.analytic-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:4px 0 8px; }}
.analytic-card {{
    background:var(--surface2); border:1px solid var(--border);
    border-radius:var(--radius-sm); padding:10px 12px; text-align:center;
}}
.analytic-val {{
    font-size:1.4rem; font-weight:700;
    font-family:'JetBrains Mono',monospace;
    background: linear-gradient(135deg,{T['accent']},{T['accent2']});
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; line-height:1.2;
}}
.analytic-label {{ font-size:.62rem; color:var(--muted); text-transform:uppercase; letter-spacing:.07em; margin-top:2px; }}

/* ── Stat bar ─────────────────────────────────────────────────────────────── */
.stat-row {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; font-size:.75rem; }}
.stat-cat {{ width:62px; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.stat-bg {{ flex:1; height:5px; background:var(--surface2); border-radius:99px; overflow:hidden; }}
.stat-fill {{ height:5px; border-radius:99px; background:linear-gradient(90deg,{T['accent']},{T['accent2']}); }}
.stat-num {{ width:24px; text-align:right; color:var(--muted); font-size:.68rem; }}

/* ── Hero ─────────────────────────────────────────────────────────────────── */
.vs-hero {{ margin:0 0 6px; }}
.vs-title {{
    font-size:2.8rem; font-weight:800; letter-spacing:-0.05em;
    background: linear-gradient(135deg, {T['text']} 0%, {T['accent']} 45%, {T['grad2']} 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    line-height:1.1; margin:0;
}}
.vs-sub {{ color:var(--muted); font-size:.92rem; margin:6px 0 24px; font-weight:400; }}

/* ── Drop zone ────────────────────────────────────────────────────────────── */
.drop-zone {{
    border:1.5px dashed var(--border); border-radius:var(--radius);
    padding:3rem 2rem; text-align:center; background:var(--surface);
    transition:border-color .25s, background .25s, transform .2s;
    margin-bottom:.6rem; cursor:pointer; position:relative; overflow:hidden;
}}
.drop-zone::before {{
    content:''; position:absolute; inset:0;
    background:linear-gradient(135deg,rgba(124,106,247,.04) 0%,rgba(244,114,182,.04) 100%);
    opacity:0; transition:opacity .25s;
}}
.drop-zone:hover {{ border-color:var(--accent); transform:translateY(-1px); }}
.drop-zone:hover::before {{ opacity:1; }}
.dz-icon {{ font-size:2.2rem; margin-bottom:.7rem; display:block; }}
.dz-title {{ font-size:.95rem; font-weight:600; color:var(--text); }}
.dz-hint {{ font-size:.75rem; color:var(--muted); margin-top:5px; }}

/* ── Skeleton ─────────────────────────────────────────────────────────────── */
@keyframes shimmer {{
    0%   {{ background-position: -800px 0; }}
    100% {{ background-position:  800px 0; }}
}}
.skeleton {{
    background: linear-gradient(90deg,{T['shimmer1']} 25%,{T['shimmer2']} 50%,{T['shimmer1']} 75%);
    background-size:1600px 100%; animation:shimmer 1.6s infinite linear; border-radius:var(--radius);
}}
.sk-card {{ height:260px; margin-bottom:10px; }}
.sk-bar {{ height:9px; border-radius:99px; margin:8px 0; }}
.sk-bar.s {{ width:50%; }}
.sk-bar.m {{ width:70%; }}

/* ── Section header ───────────────────────────────────────────────────────── */
.sec-hdr {{ display:flex; align-items:center; justify-content:space-between; margin:28px 0 16px; }}
.sec-hdr h2 {{ font-size:1.05rem; font-weight:700; color:var(--text); margin:0; display:flex; align-items:center; gap:8px; }}
.sec-hdr .pill {{
    font-size:.68rem; font-weight:600; background:var(--surface2);
    color:var(--muted); border:1px solid var(--border); padding:2px 9px; border-radius:99px;
}}

/* ── Product card ─────────────────────────────────────────────────────────── */
.card {{
    background:var(--card); border:1px solid var(--border); border-radius:var(--radius);
    overflow:hidden;
    transition:transform .28s cubic-bezier(.34,1.56,.64,1), border-color .2s, box-shadow .28s;
    cursor:pointer; position:relative;
}}
.card:hover {{
    transform:translateY(-6px) scale(1.015);
    border-color:var(--accent);
    box-shadow:0 16px 48px rgba(124,106,247,.2);
}}
.card-img {{ position:relative; height:210px; background:#0d0d14; overflow:hidden; }}
.card-img img {{ width:100%; height:100%; object-fit:cover; transition:transform .38s ease; display:block; }}
.card:hover .card-img img {{ transform:scale(1.1); }}
.card-overlay {{
    position:absolute; inset:0;
    background:linear-gradient(to top,rgba(10,10,15,.9) 0%,transparent 60%);
    opacity:0; transition:opacity .25s;
    display:flex; align-items:flex-end; padding:14px;
}}
.card:hover .card-overlay {{ opacity:1; }}
.overlay-btn {{
    font-size:.75rem; color:#fff; font-weight:600;
    background:rgba(124,106,247,.8); padding:5px 12px; border-radius:99px;
    backdrop-filter:blur(4px);
}}
.card-body {{ padding:12px 14px 14px; }}

/* ── Category badge ───────────────────────────────────────────────────────── */
.cat-badge {{
    display:inline-flex; align-items:center; gap:4px;
    font-size:.63rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase;
    padding:3px 9px; border-radius:99px; margin-bottom:9px;
}}
.cat-bags     {{ background:{'#0d1f0d' if DM else '#e6f5e6'}; color:#4ade80; border:1px solid {'#1a3a1a' if DM else '#b0deb0'}; }}
.cat-heels    {{ background:{'#1a0d1f' if DM else '#f5e6ff'}; color:#d87af5; border:1px solid {'#2d1a3a' if DM else '#d0b0e0'}; }}
.cat-jeans    {{ background:{'#0d1220' if DM else '#e6eeff'}; color:#60a5fa; border:1px solid {'#1a2540' if DM else '#b0c0e8'}; }}
.cat-skirts   {{ background:{'#1f140d' if DM else '#fff3e6'}; color:#fb923c; border:1px solid {'#3a2a1a' if DM else '#e8c8a0'}; }}
.cat-sneakers {{ background:{'#0d1f1c' if DM else '#e6fff8'}; color:#34d399; border:1px solid {'#1a3a35' if DM else '#a0e0d0'}; }}
.cat-tshirts  {{ background:{'#1f0d0f' if DM else '#ffe6e8'}; color:#f87171; border:1px solid {'#3a1a1d' if DM else '#e8b0b5'}; }}
.cat-wallets  {{ background:{'#1e1a0d' if DM else '#fffbe6'}; color:#fbbf24; border:1px solid {'#3a321a' if DM else '#e8d890'}; }}
.cat-cafri    {{ background:{'#110d1f' if DM else '#f0e6ff'}; color:#a78bfa; border:1px solid {'#221a3a' if DM else '#c8b0e8'}; }}
.cat-other    {{ background:{'#161618' if DM else '#f0f0f4'}; color:#a1a1aa; border:1px solid {'#2a2a30' if DM else '#d0d0dc'}; }}

/* ── Score bar ────────────────────────────────────────────────────────────── */
.score-row {{ display:flex; align-items:center; gap:8px; margin-bottom:5px; }}
.score-bg {{ flex:1; height:4px; background:var(--surface2); border-radius:99px; overflow:hidden; }}
@keyframes grow {{ from{{width:0}} to{{width:var(--w)}} }}
.score-fill {{ height:100%; border-radius:99px; width:var(--w); animation:grow .7s cubic-bezier(.34,1.56,.64,1) forwards; }}
.score-pct {{ font-family:'JetBrains Mono',monospace; font-size:.72rem; color:var(--muted); min-width:34px; text-align:right; }}
.match-lbl {{ font-size:.7rem; font-weight:600; }}
.lbl-great {{ color:#4ade80; }}
.lbl-good  {{ color:#fbbf24; }}
.lbl-weak  {{ color:#f87171; }}

/* ── Price panel ──────────────────────────────────────────────────────────── */
.price-panel {{
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: var(--radius-sm); margin-top: 8px; overflow: hidden;
    animation: slideDown .2s ease;
}}
@keyframes slideDown {{
    from {{ opacity:0; transform:translateY(-8px); }}
    to   {{ opacity:1; transform:translateY(0); }}
}}
.price-panel-hdr {{
    padding: 8px 12px 6px; font-size: .72rem; font-weight: 700;
    letter-spacing: .06em; text-transform: uppercase; color: var(--muted);
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 6px;
}}
.price-row {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 12px; border-bottom: 1px solid var(--border); transition: background .15s;
}}
.price-row:last-child {{ border-bottom: none; }}
.price-row:hover {{ background: rgba(124,106,247,.06); }}
.price-row.best-deal {{
    background: {'rgba(34,197,94,.08)' if DM else 'rgba(34,197,94,.05)'};
    border-left: 3px solid var(--deal);
}}
.plat-badge {{
    display: inline-flex; align-items: center; gap: 5px;
    font-size: .72rem; font-weight: 700; padding: 3px 9px; border-radius: 6px;
    color: #fff; min-width: 90px;
}}
.price-amount {{
    font-family: 'JetBrains Mono', monospace; font-size: .92rem;
    font-weight: 700; color: var(--text);
}}
.deal-badge {{
    font-size: .6rem; font-weight: 800; background: var(--deal); color: #fff;
    padding: 2px 7px; border-radius: 99px; letter-spacing: .04em; text-transform: uppercase;
}}
.savings-badge {{
    font-size: .6rem; font-weight: 700;
    background: {'rgba(34,197,94,.15)' if DM else '#d1fae5'};
    color: var(--deal); padding: 2px 7px; border-radius: 99px;
}}
.price-link {{
    font-size: .7rem; color: var(--accent); text-decoration: none;
    font-weight: 600; padding: 3px 8px; border: 1px solid var(--accent);
    border-radius: 6px; transition: all .15s;
}}
.price-link:hover {{ background: var(--accent); color: #fff; }}
.price-unavailable {{
    padding: 10px 12px; font-size: .75rem; color: var(--muted); font-style: italic;
}}
.price-summary {{
    display: flex; align-items: center; gap: 8px; padding: 6px 12px 8px;
    border-top: 1px solid var(--border);
    background: {'rgba(124,106,247,.04)' if DM else 'rgba(124,106,247,.03)'};
}}
.price-summary .best-text {{ font-size: .7rem; color: var(--muted); }}
.price-summary .best-val {{
    font-family: 'JetBrains Mono', monospace;
    font-size: .82rem; font-weight: 700; color: var(--deal);
}}
.price-range-chip {{
    font-size: .68rem; font-weight: 600; background: var(--surface);
    border: 1px solid var(--border); color: var(--muted);
    padding: 2px 8px; border-radius: 99px; margin-left: auto;
}}

/* ── Modal ────────────────────────────────────────────────────────────────── */
.modal-backdrop {{
    position:fixed; inset:0; background:rgba(0,0,0,.75); z-index:1000;
    display:flex; align-items:center; justify-content:center; padding:20px;
    backdrop-filter:blur(6px); animation:fadeIn .2s ease;
}}
@keyframes fadeIn {{ from{{opacity:0}} to{{opacity:1}} }}
.modal-box {{
    background:var(--surface); border:1px solid var(--border); border-radius:20px;
    max-width:600px; width:100%; overflow:hidden;
    box-shadow:0 32px 80px rgba(0,0,0,.5); animation:slideUp .25s ease;
    max-height:90vh; overflow-y:auto;
}}
@keyframes slideUp {{
    from{{ transform:translateY(24px); opacity:0; }}
    to  {{ transform:translateY(0);    opacity:1; }}
}}
.modal-img {{ width:100%; height:280px; object-fit:cover; display:block; }}
.modal-body {{ padding:20px 24px 24px; }}
.modal-score-row {{ display:flex; align-items:center; gap:10px; margin-bottom:16px; }}
.modal-score-big {{
    font-family:'JetBrains Mono',monospace; font-size:1.8rem; font-weight:700;
    background:linear-gradient(135deg,{T['accent']},{T['accent2']});
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
.modal-bar-bg {{ flex:1; height:6px; background:var(--surface2); border-radius:99px; overflow:hidden; }}
.modal-bar-fill {{ height:6px; border-radius:99px; }}
.modal-section-hdr {{
    font-size:.7rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
    color:var(--muted); margin:16px 0 10px; padding-bottom:6px;
    border-bottom:1px solid var(--border); display:flex; align-items:center; gap:6px;
}}
.modal-close {{
    display:block; width:100%; background:var(--accent); color:#fff; border:none;
    border-radius:10px; padding:10px; font-size:.88rem; font-weight:700;
    cursor:pointer; font-family:'Outfit',sans-serif;
    transition:background .2s; margin-top:16px;
}}
.modal-close:hover {{ background:var(--accent2); }}
.modal-link {{
    display:block; text-align:center; margin-top:8px;
    font-size:.78rem; color:var(--muted); text-decoration:none;
}}
.modal-link:hover {{ color:var(--accent); }}

/* ── Empty state ──────────────────────────────────────────────────────────── */
.empty-state {{ text-align:center; padding:5rem 2rem; color:var(--muted); }}
.empty-state h3 {{ font-size:1.05rem; font-weight:600; color:var(--text); margin:14px 0 8px; }}
.empty-state p {{ font-size:.83rem; line-height:1.7; max-width:300px; margin:0 auto; }}

/* ── Upload preview ───────────────────────────────────────────────────────── */
.up-preview {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }}
.up-label {{ font-size:.65rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); padding:10px 14px 4px; }}

/* ── Streamlit overrides ──────────────────────────────────────────────────── */
.stButton > button {{
    background: var(--accent) !important; color:#fff !important;
    border:none !important; border-radius:var(--radius-sm) !important;
    font-family:'Outfit',sans-serif !important; font-weight:700 !important;
    font-size:.85rem !important; padding:.55rem 1.3rem !important;
    transition: all .2s !important; letter-spacing:.01em !important;
}}
.stButton > button:hover {{
    background: var(--accent2) !important;
    box-shadow: 0 4px 16px rgba(124,106,247,.4) !important;
    transform: translateY(-1px) !important;
}}
[data-testid="stFileUploader"] {{
    background:var(--surface) !important;
    border:1.5px dashed var(--border) !important;
    border-radius:var(--radius) !important;
}}
[data-testid="stSelectbox"] label,
[data-testid="stSlider"] label {{ color:var(--muted) !important; font-size:.8rem !important; }}
hr {{ border-color:var(--border) !important; margin:16px 0 !important; }}
[data-testid="stAlert"] {{
    background:var(--surface2) !important;
    border:1px solid var(--border) !important;
    border-radius:var(--radius-sm) !important;
}}
[data-testid="stDownloadButton"] > button {{
    background:var(--surface2) !important; color:var(--text) !important;
    border:1px solid var(--border) !important;
    font-size:.8rem !important; padding:.4rem 1rem !important;
}}
[data-testid="stDownloadButton"] > button:hover {{
    border-color:var(--accent) !important; color:var(--accent) !important;
    background:var(--surface) !important;
    box-shadow:none !important; transform:none !important;
}}
[data-testid="stExpander"] {{
    background:var(--surface) !important;
    border:1px solid var(--border) !important;
    border-radius:var(--radius-sm) !important;
}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="grad-bg"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
BACKEND_URL     = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 60
CATEGORIES      = ["All", "bags", "heels", "jeans", "skirts",
                   "sneakers", "tshirts", "wallets", "cafri"]
CAT_ICONS = {
    "bags":     "👜", "heels":    "👠", "jeans":    "👖",
    "skirts":   "🩱", "sneakers": "👟", "tshirts":  "👕",
    "wallets":  "👛", "cafri":    "🩳", "other":    "🏷️", "all": "✦",
}

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def match_info(pct):
    if pct >= 75: return "Excellent", "lbl-great", "#4ade80"
    if pct >= 55: return "Good",      "lbl-good",  "#fbbf24"
    return "Weak", "lbl-weak", "#f87171"

def cat_cls(cat):
    c = cat.lower()
    return f"cat-{c}" if c in ["bags","heels","jeans","skirts",
                                "sneakers","tshirts","wallets","cafri"] else "cat-other"

def format_price(amount, currency="INR"):
    symbol = "₹" if currency == "INR" else "$"
    return f"{symbol}{amount:,.0f}"

def discount_pct(price, mrp):
    if mrp and mrp > price:
        return round((mrp - price) / mrp * 100)
    return None

def run_search(image_bytes, filename, category, top_k, threshold):
    files = {"file": (filename, image_bytes, "image/jpeg")}
    data  = {"category": category, "top_k": top_k}
    r = requests.post(f"{BACKEND_URL}/search", files=files,
                      data=data, timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        return []
    return [x for x in r.json() if x["score"] * 100 >= threshold]

def fetch_prices(image_url: str, category: str = "") -> list[dict]:
    cache_key = image_url
    if cache_key in st.session_state.price_cache:
        return st.session_state.price_cache[cache_key]
    try:
        r = requests.post(
            f"{BACKEND_URL}/price_search",
            json={"image_url": image_url, "category": category},
            timeout=20,
        )
        data = r.json() if r.status_code == 200 else []
        st.session_state.price_cache[cache_key] = data
        return data
    except Exception:
        return []

def add_history(image_bytes, name, results):
    st.session_state.search_history = [
        h for h in st.session_state.search_history if h["name"] != name
    ][:4]
    st.session_state.search_history.insert(
        0, {"bytes": image_bytes, "name": name, "results": results}
    )

def record_analytics(results):
    st.session_state.total_searches += 1
    for r in results:
        st.session_state.all_scores.append(r["score"] * 100)

# ══════════════════════════════════════════════════════════════════════════════
# PRICE PANEL
# ══════════════════════════════════════════════════════════════════════════════
def render_price_panel(item, card_key):
    image_url = item["image"]
    cat       = item.get("category", "")

    if st.button("💰  Find prices across platforms",
                 key=f"load_{card_key}", use_container_width=True):
        st.session_state.expanded_card = card_key
        with st.spinner("Searching platforms…"):
            fetch_prices(image_url, cat)
        st.rerun()

    if st.session_state.expanded_card != card_key:
        return

    prices = st.session_state.price_cache.get(image_url)

    if not prices:
        st.markdown("""
        <div class="price-panel">
          <div class="price-panel-hdr">🔍 Price Comparison</div>
          <div class="price-unavailable">
            No listings found. Make sure <code>SERPAPI_KEY</code> is set in your
            <code>.env</code> file and the backend is running.
          </div>
        </div>""", unsafe_allow_html=True)
        if st.button("✕ Hide", key=f"hide_{card_key}"):
            st.session_state.expanded_card = None
            st.rerun()
        return

    prices_sorted = sorted(prices, key=lambda x: x.get("price", 9e9))
    min_price     = prices_sorted[0].get("price", 0)
    max_price     = prices_sorted[-1].get("price", 0)
    currency      = prices_sorted[0].get("currency", "INR")

    rows_html = ""
    for i, p in enumerate(prices_sorted):
        plat    = p.get("platform", "other").lower()
        pc      = PLATFORM_COLORS.get(plat, PLATFORM_COLORS["other"])
        price   = p.get("price", 0)
        mrp     = p.get("mrp")
        url     = p.get("url", "#")
        name    = p.get("name", "")
        name    = name[:40] + ("…" if len(name) > 40 else "")
        disc    = discount_pct(price, mrp)
        is_best = (i == 0)
        row_cls = "price-row best-deal" if is_best else "price-row"
        rating  = p.get("rating")

        badge_html  = '<span class="deal-badge">BEST</span>' if is_best else ""
        disc_html   = f'<span class="savings-badge">-{disc}%</span>' if disc else ""
        rating_html = f'<span style="font-size:.65rem;color:#fbbf24;">★ {rating}</span>' if rating else ""

        rows_html += f"""
        <div class="{row_cls}">
          <div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0;">
            <span class="plat-badge" style="background:{pc['bg']};color:{pc['text']}">
              {pc['icon']} {plat.title()}
            </span>
            <div style="min-width:0;">
              <div style="font-size:.7rem;color:var(--muted);white-space:nowrap;
                          overflow:hidden;text-overflow:ellipsis;max-width:160px;">{name}</div>
              <div style="display:flex;align-items:center;gap:4px;margin-top:2px;">
                {rating_html}
              </div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
            {badge_html}{disc_html}
            <span class="price-amount">{format_price(price, currency)}</span>
            <a class="price-link" href="{url}" target="_blank">Buy →</a>
          </div>
        </div>"""

    savings_html = ""
    if max_price > min_price:
        savings = max_price - min_price
        savings_html = f"""
        <div class="price-summary">
          <span class="best-text">Best price:</span>
          <span class="best-val">{format_price(min_price, currency)}</span>
          <span class="price-range-chip">Save up to {format_price(savings, currency)}</span>
        </div>"""

    st.markdown(f"""
    <div class="price-panel">
      <div class="price-panel-hdr">💰 Price Comparison
        <span style="margin-left:auto;font-size:.65rem;font-weight:400;">{len(prices)} platforms</span>
      </div>
      {rows_html}
      {savings_html}
    </div>""", unsafe_allow_html=True)

    if st.button("✕ Hide prices", key=f"hide_{card_key}"):
        st.session_state.expanded_card = None
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MODAL
# ══════════════════════════════════════════════════════════════════════════════
def render_modal(item):
    pct   = item["score"] * 100
    label, lcls, color = match_info(pct)
    cat   = item.get("category", "other").lower()
    icon  = CAT_ICONS.get(cat, "🏷️")
    cc    = cat_cls(cat)

    prices    = st.session_state.price_cache.get(item["image"], [])
    best_html = ""
    if prices:
        best = min(prices, key=lambda x: x.get("price", 9e9))
        plat = best.get("platform", "")
        pc   = PLATFORM_COLORS.get(plat.lower(), PLATFORM_COLORS["other"])
        best_html = f"""
        <div style="margin-bottom:14px;">
          <div class="modal-section-hdr">💰 Best Price Found</div>
          <div style="display:flex;align-items:center;gap:10px;
                      background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.2);
                      border-radius:10px;padding:12px 14px;">
            <span class="plat-badge" style="background:{pc['bg']};color:{pc['text']}">
              {pc['icon']} {plat.title()}
            </span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:1.3rem;
                         font-weight:700;color:#22c55e;">
              {format_price(best.get('price', 0), best.get('currency','INR'))}
            </span>
            <a href="{best.get('url','#')}" target="_blank" class="price-link" style="margin-left:auto;">
              Buy now →
            </a>
          </div>
        </div>"""

    st.markdown(f"""
    <div class="modal-backdrop">
      <div class="modal-box">
        <img class="modal-img" src="{item['image']}"
             onerror="this.style.display='none'"/>
        <div class="modal-body">
          <div><span class="cat-badge {cc}">{icon} {cat.upper()}</span></div>
          <div class="modal-score-row">
            <span class="modal-score-big">{pct:.0f}%</span>
            <div class="modal-bar-bg">
              <div class="modal-bar-fill" style="width:{pct:.0f}%;background:{color};"></div>
            </div>
            <span class="match-lbl {lcls}">{label}</span>
          </div>
          {best_html}
          <a class="modal-link" href="{item['image']}" target="_blank">🔗 Open full image</a>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("✕  Close", key="close_modal"):
        st.session_state.modal_open = False
        st.session_state.modal_item = None
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# COMPARE SLIDER
# ══════════════════════════════════════════════════════════════════════════════
def render_compare(query_bytes, result_url):
    import base64
    import streamlit.components.v1 as components
    q64  = base64.b64encode(query_bytes).decode()
    html = f"""
<style>
*{{box-sizing:border-box;margin:0;padding:0}}body{{background:transparent}}
.cw{{position:relative;width:100%;height:290px;border-radius:14px;overflow:hidden;
     border:1px solid #2a2a3a;background:#0d0d14;user-select:none;cursor:ew-resize;}}
.full{{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;}}
.clip{{position:absolute;top:0;left:0;height:100%;overflow:hidden;width:50%;z-index:2;}}
.clip img{{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;object-position:left;}}
.dl{{position:absolute;top:0;bottom:0;left:50%;width:2px;background:#fff;z-index:4;pointer-events:none;}}
.hd{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:38px;height:38px;
     background:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;
     font-size:14px;z-index:5;pointer-events:none;box-shadow:0 2px 16px rgba(0,0,0,.6);}}
.lb{{position:absolute;top:10px;z-index:6;font-size:10px;font-weight:700;letter-spacing:.06em;
     text-transform:uppercase;padding:3px 9px;border-radius:4px;font-family:sans-serif;}}
.lb.l{{left:10px;background:rgba(0,0,0,.7);color:#e8e8f0;}}
.lb.r{{right:10px;background:rgba(124,106,247,.7);color:#fff;}}
</style>
<div class="cw" id="cw">
  <img class="full" src="{result_url}"/>
  <div class="clip" id="clip"><img src="data:image/jpeg;base64,{q64}"/></div>
  <div class="dl" id="dl"></div>
  <div class="hd">⇔</div>
  <div class="lb l">Uploaded</div>
  <div class="lb r">Match</div>
</div>
<script>
(function(){{
  const cw=document.getElementById('cw'),clip=document.getElementById('clip'),dl=document.getElementById('dl');
  let drag=false;
  function set(x){{const r=cw.getBoundingClientRect(),p=Math.min(Math.max((x-r.left)/r.width*100,2),98);
    clip.style.width=p+'%';dl.style.left=p+'%';}}
  cw.addEventListener('mousedown',e=>{{drag=true;set(e.clientX);}});
  window.addEventListener('mousemove',e=>{{if(drag)set(e.clientX);}});
  window.addEventListener('mouseup',()=>drag=false);
  cw.addEventListener('touchstart',e=>{{drag=true;set(e.touches[0].clientX);}},{{passive:true}});
  window.addEventListener('touchmove',e=>{{if(drag)set(e.touches[0].clientX);}},{{passive:true}});
  window.addEventListener('touchend',()=>drag=false);
}})();
</script>"""
    components.html(html, height=310)

# ══════════════════════════════════════════════════════════════════════════════
# RENDER HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def render_skeleton():
    cols = st.columns(3)
    for i in range(6):
        with cols[i % 3]:
            st.markdown("""
            <div class="skeleton sk-card"></div>
            <div class="skeleton sk-bar m"></div>
            <div class="skeleton sk-bar s"></div>
            """, unsafe_allow_html=True)

def render_empty():
    st.markdown("""
    <div class="empty-state">
      <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
        <circle cx="36" cy="36" r="22" stroke="#7c6af7" stroke-width="2.5"/>
        <line x1="52" y1="52" x2="70" y2="70" stroke="#7c6af7" stroke-width="3" stroke-linecap="round"/>
      </svg>
      <h3>No matches found</h3>
      <p>Try lowering the minimum match %, switching category to "All",
         or uploading a cleaner product photo.</p>
    </div>""", unsafe_allow_html=True)

def render_results(results, sort_by, query_bytes=None):
    if not results:
        render_empty()
        return

    # ── Sort ──────────────────────────────────────────────────────────────────
    if sort_by == "Highest match first":
        results = sorted(results, key=lambda x: x["score"], reverse=True)
    elif sort_by == "Lowest match first":
        results = sorted(results, key=lambda x: x["score"])
    elif sort_by == "By category":
        results = sorted(results, key=lambda x: x.get("category", ""))
    elif sort_by == "Cheapest first":
        def best_price(r):
            p = st.session_state.price_cache.get(r["image"], [])
            return min((x.get("price", 9e9) for x in p), default=9e9)
        results = sorted(results, key=best_price)

    # ── Header + export ───────────────────────────────────────────────────────
    hc, ec = st.columns([4, 1])
    with hc:
        st.markdown(f"""
        <div class="sec-hdr">
          <h2>✦ Similar products
            <span class="pill">{len(results)} found</span>
          </h2>
        </div>""", unsafe_allow_html=True)
    with ec:
        csv = pd.DataFrame([{
            "url":           r["image"],
            "category":      r.get("category", ""),
            "score_pct":     round(r["score"] * 100, 1),
            "best_price":    min(
                (p.get("price", 0) for p in st.session_state.price_cache.get(r["image"], []) if p),
                default="",
            ),
            "best_platform": (
                min(
                    st.session_state.price_cache.get(r["image"], []),
                    key=lambda x: x.get("price", 9e9),
                    default={},
                ).get("platform", "")
            ),
        } for r in results]).to_csv(index=False).encode()
        st.download_button("⬇ Export", csv, "results.csv",
                           "text/csv", use_container_width=True)

    # ── Compare slider ────────────────────────────────────────────────────────
    if query_bytes and results:
        with st.expander("🔀 Compare uploaded vs top match"):
            render_compare(query_bytes, results[0]["image"])

    # ── Card grid ─────────────────────────────────────────────────────────────
    cols = st.columns(3)
    for i, item in enumerate(results):
        pct   = item["score"] * 100
        label, lcls, color = match_info(pct)
        cat   = item.get("category", "other").lower()
        icon  = CAT_ICONS.get(cat, "🏷️")
        cc    = cat_cls(cat)
        card_key = f"card_{i}_{item['image'][-20:]}"

        cached_prices = st.session_state.price_cache.get(item["image"])
        price_chip = ""
        if cached_prices:
            best = min(cached_prices, key=lambda x: x.get("price", 9e9))
            plat = best.get("platform", "")
            pc   = PLATFORM_COLORS.get(plat.lower(), PLATFORM_COLORS["other"])
            price_chip = f"""
            <div style="margin-top:6px;display:flex;align-items:center;gap:6px;">
              <span style="font-size:.65rem;color:var(--muted);">Best:</span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:.78rem;
                           font-weight:700;color:#22c55e;">
                {format_price(best.get('price', 0), best.get('currency','INR'))}
              </span>
              <span style="font-size:.6rem;padding:1px 6px;border-radius:4px;
                           background:{pc['bg']};color:{pc['text']}">{plat.title()}</span>
            </div>"""

        with cols[i % 3]:
            st.markdown(f"""
            <div class="card">
              <div class="card-img">
                <img src="{item['image']}" loading="lazy"
                     onerror="this.parentElement.style.background='#1a1a2a'"/>
                <div class="card-overlay"><span class="overlay-btn">View details</span></div>
              </div>
              <div class="card-body">
                <span class="cat-badge {cc}">{icon} {cat.upper()}</span>
                <div class="score-row">
                  <div class="score-bg">
                    <div class="score-fill" style="--w:{pct:.0f}%;background:{color};"></div>
                  </div>
                  <span class="score-pct">{pct:.0f}%</span>
                </div>
                <span class="match-lbl {lcls}">{label} match</span>
                {price_chip}
              </div>
            </div>
            <div style="height:6px"></div>
            """, unsafe_allow_html=True)

            render_price_panel(item, card_key)

            st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
            if st.button("🔍 Details", key=f"modal_{i}_{item['image'][-20:]}",
                         use_container_width=True):
                st.session_state.modal_item = item
                st.session_state.modal_open = True
                st.rerun()

            st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

# Modal overlay (renders above everything)
if st.session_state.modal_open and st.session_state.modal_item:
    render_modal(st.session_state.modal_item)

st.markdown('<div class="vs-hero">', unsafe_allow_html=True)
st.markdown('<h1 class="vs-title">Visual Search</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="vs-sub">Upload any product photo — find visually similar items '
    'and compare prices across platforms</p>',
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

mode = st.radio("", ["Single image", "Batch search"],
                horizontal=True, label_visibility="collapsed")
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="sb-brand">
      <div class="logo">✦ VisualSearch</div>
      <div class="tagline">AI-powered product discovery</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-section">Appearance</div>', unsafe_allow_html=True)
    col_d, col_l = st.columns(2)
    with col_d:
        if st.button("🌙  Dark", use_container_width=True,
                     type="primary" if DM else "secondary"):
            st.session_state.dark_mode = True
            st.rerun()
    with col_l:
        if st.button("☀️  Light", use_container_width=True,
                     type="primary" if not DM else "secondary"):
            st.session_state.dark_mode = False
            st.rerun()

    st.divider()

    st.markdown('<div class="sb-section">Search</div>', unsafe_allow_html=True)
    category  = st.selectbox(
        "Category", CATEGORIES,
        format_func=lambda c: f"{CAT_ICONS.get(c.lower(), '🏷️')}  {c}",
        label_visibility="collapsed",
    )
    top_k     = st.slider("Results to fetch", 3, 20, 10)
    threshold = st.slider("Min match %", 0, 100, 30)
    sort_by   = st.selectbox(
        "Sort",
        ["Highest match first", "Lowest match first", "By category", "Cheapest first"],
        label_visibility="collapsed",
    )

    st.divider()

    # ── Analytics ─────────────────────────────────────────────────────────────
    st.markdown('<div class="sb-section">Analytics</div>', unsafe_allow_html=True)
    ts      = st.session_state.total_searches
    scores  = st.session_state.all_scores
    avgs    = sum(scores) / len(scores) if scores else 0
    best_sc = max(scores) if scores else 0
    price_lookups = len(st.session_state.price_cache)

    st.markdown(f"""
    <div class="analytic-grid">
      <div class="analytic-card">
        <div class="analytic-val">{ts}</div>
        <div class="analytic-label">Searches</div>
      </div>
      <div class="analytic-card">
        <div class="analytic-val">{avgs:.0f}%</div>
        <div class="analytic-label">Avg score</div>
      </div>
      <div class="analytic-card">
        <div class="analytic-val">{best_sc:.0f}%</div>
        <div class="analytic-label">Best match</div>
      </div>
      <div class="analytic-card">
        <div class="analytic-val">{price_lookups}</div>
        <div class="analytic-label">Price lookups</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Dataset stats ─────────────────────────────────────────────────────────
    st.markdown('<div class="sb-section">Dataset</div>', unsafe_allow_html=True)
    try:
        sr = requests.get(f"{BACKEND_URL}/stats", timeout=3)
        if sr.status_code == 200:
            stats = sr.json()
            total = max(sum(stats.values()), 1)
            for cat, cnt in sorted(stats.items(), key=lambda x: -x[1]):
                pct2 = cnt / total * 100
                icon = CAT_ICONS.get(cat, "🏷️")
                st.markdown(f"""
                <div class="stat-row">
                  <span class="stat-cat">{icon} {cat}</span>
                  <div class="stat-bg">
                    <div class="stat-fill" style="width:{pct2:.0f}%"></div>
                  </div>
                  <span class="stat-num">{cnt}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.caption("Stats unavailable")
    except Exception:
        st.caption("Backend offline — run uvicorn main:app")

    # ── Search history ────────────────────────────────────────────────────────
    if st.session_state.search_history:
        st.divider()
        st.markdown('<div class="sb-section">Recent</div>', unsafe_allow_html=True)
        hcols = st.columns(5)
        for i, entry in enumerate(st.session_state.search_history[:5]):
            with hcols[i]:
                img = Image.open(io.BytesIO(entry["bytes"])).resize((60, 60))
                st.image(img, use_container_width=True)
                if st.button("↩", key=f"h{i}", help=entry["name"]):
                    st.session_state.last_results = entry["results"]
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SINGLE IMAGE
# ══════════════════════════════════════════════════════════════════════════════
if mode == "Single image":
    st.markdown("""
    <div class="drop-zone">
      <span class="dz-icon">📂</span>
      <div class="dz-title">Drag & drop a product image</div>
      <div class="dz-hint">JPG · PNG · JPEG</div>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload", type=["jpg", "jpeg", "png"],
                                label_visibility="collapsed")

    if uploaded:
        image_bytes = uploaded.read()
        pc, _ = st.columns([1, 2])
        with pc:
            st.markdown('<div class="up-preview"><div class="up-label">Your image</div>',
                        unsafe_allow_html=True)
            st.image(image_bytes, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        skel = st.empty()
        with skel.container():
            render_skeleton()

        try:
            results = run_search(image_bytes, uploaded.name,
                                 category, top_k, threshold)
            add_history(image_bytes, uploaded.name, results)
            record_analytics(results)
        except requests.exceptions.ConnectionError:
            skel.error("❌ Cannot connect to backend. Run: uvicorn main:app --reload")
            st.stop()
        except requests.exceptions.Timeout:
            skel.error(f"⏱ Request timed out after {REQUEST_TIMEOUT}s.")
            st.stop()
        except Exception as e:
            skel.error(f"Error: {e}")
            st.stop()

        skel.empty()
        render_results(results, sort_by, query_bytes=image_bytes)

# ══════════════════════════════════════════════════════════════════════════════
# BATCH
# ══════════════════════════════════════════════════════════════════════════════
else:
    st.markdown("""
    <div class="drop-zone">
      <span class="dz-icon">📂</span>
      <div class="dz-title">Drop multiple product images</div>
      <div class="dz-hint">JPG · PNG · JPEG · select several at once</div>
    </div>
    """, unsafe_allow_html=True)

    files = st.file_uploader("Upload images", type=["jpg", "jpeg", "png"],
                             accept_multiple_files=True,
                             label_visibility="collapsed")

    if files:
        n = len(files)
        if st.button(f"Search {n} image{'s' if n > 1 else ''}", type="primary"):
            batch = {}
            bar   = st.progress(0, text="Searching…")
            for i, f in enumerate(files):
                img_bytes = f.read()
                try:
                    res = run_search(img_bytes, f.name, category, top_k, threshold)
                    record_analytics(res)
                except Exception as e:
                    st.warning(f"{f.name}: {e}")
                    res = []
                batch[f.name] = {"bytes": img_bytes, "results": res}
                add_history(img_bytes, f.name, res)
                bar.progress((i + 1) / n, text=f"Done {i + 1}/{n}")
                time.sleep(0.04)
            bar.empty()

            tabs = st.tabs([nm[:22] for nm in batch])
            for tab, (fname, data) in zip(tabs, batch.items()):
                with tab:
                    pc2, rc = st.columns([1, 3])
                    with pc2:
                        st.image(data["bytes"], use_container_width=True, caption=fname)
                    with rc:
                        render_results(data["results"], sort_by,
                                       query_bytes=data["bytes"])
