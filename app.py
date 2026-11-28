# =====================================================================
# BookLens - Discover Books. Explore Data. Understand Insights.
# A worldwide book discovery and analytics platform built with Streamlit.
# Run with:  streamlit run app.py
# =====================================================================

# =====================================================================
# 1. IMPORTS AND CONFIGURATION
# =====================================================================
import hashlib
import html
import io
import json
import math
import os
import random
import re
import sqlite3
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from itertools import zip_longest

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
import streamlit as st
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings("ignore", module="bs4")
warnings.filterwarnings("ignore", category=FutureWarning)

SENTIMENT_ENGINE = None
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    SENTIMENT_ENGINE = "VADER"
except Exception:  # pragma: no cover
    try:
        from textblob import TextBlob

        SENTIMENT_ENGINE = "TextBlob"
    except Exception:
        SENTIMENT_ENGINE = None

APP_NAME = "BookLens"
TAGLINE = "Discover Books. Explore Data. Understand Insights."
DB_PATH = os.environ.get("BOOKLENS_DB", "booklens.db")
GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY", "").strip()
PER_SOURCE = 10          # records requested from each API per page (10 + 10 = up to 20 per page)
PAGE_SIZE = 20
CACHE_TTL = 3600         # seconds
HTTP_TIMEOUT = 10        # seconds
GB_URL = "https://www.googleapis.com/books/v1/volumes"
OL_SEARCH_URL = "https://openlibrary.org/search.json"
OL_FIELDS = ("key,title,author_name,first_publish_year,isbn,subject,publisher,language,"
             "number_of_pages_median,ratings_average,ratings_count,cover_i,publish_place")
HTTP_HEADERS = {"User-Agent": "BookLens/1.0 (Streamlit book discovery app)"}

SECTIONS = [
    ("Home", "Home", "🏠", "Welcome, quick search and shortcuts"),
    ("Explore Worldwide Books", "Explore", "🌍", "Search Google Books and Open Library worldwide"),
    ("Book Details", "Details", "📖", "Full information and links for one book"),
    ("Wishlist", "Wishlist", "♥", "Books you saved for later"),
    ("Recently Viewed", "Recent", "🕘", "Books you opened lately"),
    ("Book Comparison", "Compare", "⇄", "Two books side by side"),
    ("Book Recommendations", "Recommend", "✨", "Related and similar books"),
    ("Reading List", "Reading", "📚", "Track what to read, are reading and finished"),
    ("Top Rated Books", "Top Rated", "🏆", "Highest rated books in your dataset"),
    ("Trending Books", "Trending", "🔥", "Popularity ranking from ratings data"),
    ("Book Analytics", "Analytics", "📈", "Charts and statistics for your dataset"),
    ("Sentiment Analysis", "Sentiment", "💬", "Analyze descriptions and your own reviews"),
]
SECTION_NAMES = [s[0] for s in SECTIONS]
SECTION_INFO = {s[0]: s for s in SECTIONS}

SEARCH_TYPES = ["Keywords", "Title", "Author", "ISBN", "Subject / Category"]
STATUSES = ["To Read", "Currently Reading", "Completed"]

LANGUAGES = {  # name: (Google Books code, Open Library code)
    "Any": (None, None), "English": ("en", "eng"), "Tamil": ("ta", "tam"), "Hindi": ("hi", "hin"),
    "French": ("fr", "fre"), "German": ("de", "ger"), "Spanish": ("es", "spa"),
    "Japanese": ("ja", "jpn"), "Chinese": ("zh", "chi"), "Arabic": ("ar", "ara"),
    "Bengali": ("bn", "ben"), "Malayalam": ("ml", "mal"), "Telugu": ("te", "tel"),
    "Kannada": ("kn", "kan"), "Marathi": ("mr", "mar"), "Portuguese": ("pt", "por"),
    "Russian": ("ru", "rus"), "Italian": ("it", "ita"), "Korean": ("ko", "kor"),
    "Urdu": ("ur", "urd"), "Dutch": ("nl", "dut"), "Polish": ("pl", "pol"), "Turkish": ("tr", "tur"),
}
GB_LANG_NAMES = {v[0]: k for k, v in LANGUAGES.items() if v[0]}
OL_LANG_NAMES = {v[1]: k for k, v in LANGUAGES.items() if v[1]}

COUNTRIES = {
    "Any": None, "India": "IN", "United States": "US", "United Kingdom": "GB", "Canada": "CA",
    "Australia": "AU", "France": "FR", "Germany": "DE", "Spain": "ES", "Italy": "IT",
    "Japan": "JP", "China": "CN", "Brazil": "BR", "Singapore": "SG", "South Africa": "ZA",
}
CATEGORIES = ["Any", "Fiction", "Nonfiction", "Science", "Technology", "Computers", "Mathematics",
              "History", "Biography", "Fantasy", "Mystery", "Romance", "Thriller", "Self-Help",
              "Business", "Philosophy", "Poetry", "Drama", "Children", "Young Adult", "Health",
              "Cooking", "Art", "Religion", "Travel", "Psychology", "Education", "Comics", "Humor",
              "Sports"]
CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "GBP": "£", "EUR": "€", "JPY": "¥", "CAD": "CA$",
                    "AUD": "A$", "CNY": "CN¥"}
OL_BAD_SUBJECTS = {"accessible book", "protected daisy", "in library", "large type books",
                   "lending library", "internet archive wishlist", "open library staff picks",
                   "overdrive", "reading level-grade 11", "long now manual for civilization"}
RANDOM_TOPICS = ["fiction", "history", "science", "fantasy", "philosophy", "poetry", "biography",
                 "mystery", "travel", "psychology", "mathematics", "cooking"]
SUGGESTED_SEARCHES = [
    ("Science fiction", "Keywords", "Any", "Science"), ("Tamil literature", "Keywords", "Tamil", "Any"),
    ("Python programming", "Title", "Any", "Any"), ("Self improvement", "Subject / Category", "Any", "Any"),
    ("Murakami", "Author", "Any", "Any"), ("Les Misérables", "Title", "French", "Any"),
]

# Widget keys whose values must survive navigation (Streamlit drops state of unrendered widgets).
UI_DEFAULTS = {
    "f_type": "Keywords", "f_query": "", "f_author": "", "f_category": "Any", "f_lang": "Any",
    "f_country": "Any", "c_sort": "Relevance", "c_dir": "Ascending", "c_rating": 0.0,
    "c_pmin": 0, "c_pmax": 0, "c_ymin": 0, "c_ymax": 0, "tr_min": 0, "rl_filter": "All", "tw_q": "",
}

# =====================================================================
# 2. PAGE CONFIGURATION
# =====================================================================
st.set_page_config(page_title="BookLens | Discover Books", page_icon="📚", layout="wide",
                   initial_sidebar_state="expanded")

# =====================================================================
# 3. CUSTOM CSS
# =====================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap');
:root{--violet:#8b5cf6;--violet2:#6d28d9;--lav:#c4b5fd;--lav2:#e9ddff;--glass:rgba(255,255,255,.06);--glassb:rgba(196,181,253,.20);}
html,body,.stApp{font-family:'DM Sans',sans-serif;color:#e9ddff;}
.stApp{background:linear-gradient(135deg,#12082b 0%,#2a1055 48%,#160a35 100%);background-attachment:fixed;}
header[data-testid="stHeader"]{background:transparent;}
#MainMenu,footer{visibility:hidden;}
.block-container{padding-top:1.1rem;max-width:1300px;}
h1,h2,h3,h4{font-family:'Sora',sans-serif;color:#f3ecff;letter-spacing:-.01em;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#1b0c40,#0e0623);border-right:1px solid rgba(196,181,253,.16);}
[data-testid="stSidebar"] [role="radiogroup"] label{background:rgba(255,255,255,.05);border:1px solid rgba(196,181,253,.18);border-radius:12px;padding:.55rem .8rem;margin-bottom:.4rem;transition:all .15s ease;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:rgba(139,92,246,.28);border-color:#c4b5fd;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:linear-gradient(135deg,#8b5cf6,#6d28d9);border-color:#e9ddff;}
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child{display:none;}
[data-testid="stWidgetLabel"] p,label,.stCaption,[data-testid="stCaptionContainer"]{color:#d9c9ff !important;}
.stTextInput input,.stNumberInput input,textarea{background:rgba(255,255,255,.07) !important;color:#fff !important;border:1px solid rgba(196,181,253,.30) !important;border-radius:12px !important;}
div[data-baseweb="select"] > div{background:rgba(255,255,255,.07) !important;border:1px solid rgba(196,181,253,.30) !important;border-radius:12px !important;color:#fff !important;}
div[data-baseweb="select"] *{color:#f3ecff !important;}
div[data-baseweb="popover"] ul,div[data-baseweb="popover"] li{background:#22114a !important;color:#f3ecff !important;}
div[data-baseweb="popover"] li:hover{background:#3b1f7a !important;}
[data-testid="stForm"]{background:var(--glass);border:1px solid var(--glassb);border-radius:20px;padding:1rem 1.2rem;backdrop-filter:blur(14px);}
[data-testid="stExpander"]{background:var(--glass);border:1px solid var(--glassb) !important;border-radius:16px;}
[data-testid="stExpander"] summary p{color:#f3ecff !important;font-weight:600;}
.stTabs [data-baseweb="tab"]{color:#d9c9ff;border-radius:10px 10px 0 0;}
.stTabs [aria-selected="true"]{color:#fff !important;}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button,.stLinkButton>a{width:100%;border-radius:12px;border:1px solid rgba(196,181,253,.38);background:linear-gradient(135deg,rgba(139,92,246,.28),rgba(109,40,217,.16));color:#f3ecff !important;font-weight:600;text-decoration:none;transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease;display:flex;justify-content:center;}
.stButton>button p,.stDownloadButton>button p,.stFormSubmitButton>button p,.stLinkButton>a p{color:inherit !important;}
.stButton>button:hover,.stDownloadButton>button:hover,.stFormSubmitButton>button:hover,.stLinkButton>a:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(139,92,246,.45);border-color:#e9ddff;color:#fff !important;}
.stButton>button:disabled{opacity:.32;transform:none;box-shadow:none;}
button[kind="primary"],button[data-testid="stBaseButton-primary"],button[data-testid="stBaseButton-primaryFormSubmit"]{background:linear-gradient(135deg,#8b5cf6,#6d28d9) !important;border:1px solid #e9ddff !important;color:#fff !important;box-shadow:0 8px 22px rgba(139,92,246,.5);}
.glass{background:var(--glass);border:1px solid var(--glassb);border-radius:20px;padding:1.1rem 1.3rem;backdrop-filter:blur(14px);box-shadow:0 10px 40px rgba(10,0,40,.35);margin-bottom:.9rem;}
.hero{background:linear-gradient(135deg,rgba(139,92,246,.42),rgba(60,25,130,.30));border:1px solid rgba(233,221,255,.28);border-radius:26px;padding:2.2rem 2.4rem;box-shadow:0 18px 60px rgba(10,0,40,.55);margin-bottom:1rem;}
.hero h1{font-size:3rem;margin:0;font-weight:800;background:linear-gradient(90deg,#fff,#c4b5fd);-webkit-background-clip:text;background-clip:text;color:transparent;}
.hero p{font-size:1.15rem;color:#e9ddff;margin:.4rem 0 0 0;}
.bl-brand{font-family:'Sora',sans-serif;font-weight:800;font-size:1.7rem;background:linear-gradient(90deg,#fff,#c4b5fd);-webkit-background-clip:text;background-clip:text;color:transparent;}
.bl-brand-sub{color:#c4b5fd;font-size:.8rem;margin-bottom:1rem;}
.bl-h2{font-family:'Sora',sans-serif;font-size:1.55rem;font-weight:700;color:#f3ecff;margin:.2rem 0 .2rem 0;}
.bl-sub{color:#c4b5fd;font-size:.95rem;margin-bottom:.8rem;}
.bl-navmid{text-align:center;padding:.1rem 0;}
.bl-crumb{font-size:.82rem;color:#c4b5fd;}
.bl-crumb b{color:#fff;}
.bl-sectitle{font-family:'Sora',sans-serif;font-size:1.35rem;font-weight:700;color:#fff;}
.bl-pill{display:inline-block;background:rgba(139,92,246,.35);border:1px solid rgba(196,181,253,.4);border-radius:999px;padding:.1rem .7rem;font-size:.78rem;color:#f3ecff;margin-top:.15rem;}
.bl-trail{font-size:.75rem;color:#a78bfa;margin-top:.2rem;}
.bl-card{background:var(--glass);border:1px solid var(--glassb);border-radius:18px;padding:.8rem;backdrop-filter:blur(12px);box-shadow:0 8px 28px rgba(10,0,40,.4);transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease;margin-bottom:.5rem;}
.bl-card:hover{transform:translateY(-4px);box-shadow:0 16px 40px rgba(139,92,246,.35);border-color:#c4b5fd;}
.bl-cover{position:relative;width:100%;height:230px;border-radius:12px;overflow:hidden;background:linear-gradient(145deg,#2d1666,#170b36);display:flex;align-items:center;justify-content:center;}
.bl-cover img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#150a30;}
.bl-cover-sm{height:130px;width:90px;}
.bl-cover-lg{height:440px;}
.bl-cover-md{height:260px;}
.bl-nocover{color:#c4b5fd;font-size:.82rem;text-align:center;padding:.5rem;}
.bl-title{font-family:'Sora',sans-serif;font-weight:600;font-size:.98rem;color:#fff;margin-top:.6rem;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.6em;line-height:1.3;}
.bl-author{color:#c4b5fd;font-size:.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.bl-chip{display:inline-block;background:rgba(139,92,246,.25);border:1px solid rgba(196,181,253,.3);border-radius:999px;padding:.02rem .55rem;font-size:.72rem;margin:.18rem .2rem 0 0;color:#f3ecff;}
.bl-rating{color:#fcd34d;font-weight:600;font-size:.88rem;margin-top:.3rem;}
.bl-rating small{color:#c4b5fd;font-weight:400;}
.bl-price{font-weight:700;color:#fff;font-size:.95rem;}
.bl-tag{display:inline-block;border-radius:6px;padding:0 .4rem;font-size:.68rem;margin-left:.4rem;font-weight:600;}
.bl-tag-actual{background:rgba(52,211,153,.2);color:#6ee7b7;border:1px solid rgba(52,211,153,.5);}
.bl-tag-est{background:rgba(251,191,36,.16);color:#fcd34d;border:1px solid rgba(251,191,36,.45);}
.kpi{background:var(--glass);border:1px solid var(--glassb);border-radius:18px;padding:1rem 1.1rem;box-shadow:0 8px 28px rgba(10,0,40,.4);margin-bottom:.7rem;}
.kpi-v{font-family:'Sora',sans-serif;font-size:1.8rem;font-weight:700;color:#fff;}
.kpi-l{color:#c4b5fd;font-size:.85rem;}
.kpi-s{color:#a78bfa;font-size:.72rem;}
.bl-spec{width:100%;border-collapse:collapse;}
.bl-spec td{padding:.45rem .6rem;border-bottom:1px solid rgba(196,181,253,.15);font-size:.92rem;vertical-align:top;}
.bl-spec td:first-child{color:#c4b5fd;width:34%;font-weight:600;}
.bl-cmp td:first-child{width:20%;}
.bl-cmp td.win{color:#6ee7b7;font-weight:700;}
.bl-desc{line-height:1.65;color:#ece3ff;font-size:.97rem;}
.bl-unavail{border:1px dashed rgba(196,181,253,.4);border-radius:12px;padding:.55rem .8rem;text-align:center;color:#a78bfa;font-size:.88rem;}
.bl-rank{font-family:'Sora',sans-serif;font-size:1.6rem;font-weight:800;color:#c4b5fd;padding-top:1.6rem;}
.bl-note{background:rgba(251,191,36,.10);border:1px solid rgba(251,191,36,.35);border-radius:14px;padding:.7rem 1rem;color:#fde68a;font-size:.88rem;margin:.5rem 0;}
.bl-loader{display:flex;flex-direction:column;align-items:center;padding:1.4rem;}
.bl-loader span{display:inline-block;width:14px;height:14px;margin:0 5px;border-radius:50%;background:#a78bfa;animation:blbounce 1s infinite ease-in-out;}
.bl-loader span:nth-child(2){animation-delay:.15s;background:#8b5cf6;}
.bl-loader span:nth-child(3){animation-delay:.3s;background:#c4b5fd;}
.bl-loader p{color:#c4b5fd;margin-top:.6rem;font-size:.9rem;}
@keyframes blbounce{0%,80%,100%{transform:scale(.5);opacity:.5}40%{transform:scale(1.15);opacity:1}}
[data-testid="stSpinner"] *{color:#c4b5fd !important;}
@media (max-width:900px){.hero h1{font-size:2.1rem}.bl-cover-lg{height:320px}}
</style>
"""
LOADER_HTML = ('<div class="bl-loader"><div><span></span><span></span><span></span></div>'
               '<p>Searching worldwide catalogues…</p></div>')


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


# =====================================================================
# SMALL UTILITIES
# =====================================================================
def e(x):
    """HTML-escape text (also neutralises $ so Streamlit does not render LaTeX)."""
    return html.escape(str(x if x is not None else "")).replace("$", "&#36;")


def to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def to_float(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def year_from(v):
    m = re.search(r"(1[0-9]{3}|20[0-9]{2})", str(v or ""))
    return int(m.group(1)) if m else None


def clean_text(t):
    if not t:
        return ""
    try:
        txt = BeautifulSoup(str(t), "html.parser").get_text(" ")
    except Exception:
        txt = str(t)
    return re.sub(r"\s+", " ", txt).strip()


def safe_url(u):
    u = str(u or "").strip()
    return u if u.lower().startswith(("http://", "https://")) else None


def https(u):
    return re.sub(r"^http://", "https://", u) if u else u


def is_empty(v):
    return v is None or v == "" or v == [] or v in ("Uncategorized", "Unknown")


def fmt_int(n):
    return f"{int(n):,}" if n is not None else "-"


def now_iso():
    return datetime.now().isoformat(timespec="microseconds")


# =====================================================================
# 4. DATABASE INITIALIZATION (SQLite)
# =====================================================================
def db_exec(sql, params=(), many=False, fetch=False):
    """Run one SQL statement safely (parameterised). Returns rows when fetch=True."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.executemany(sql, params) if many else conn.execute(sql, params)
            rows = cur.fetchall() if fetch else None
            conn.commit()
            return rows
        finally:
            conn.close()
    except sqlite3.Error as exc:
        st.session_state.setdefault("db_errors", []).append(str(exc))
        return [] if fetch else None


def init_db():
    stmts = [
        "CREATE TABLE IF NOT EXISTS books (book_id TEXT PRIMARY KEY, data TEXT NOT NULL, saved_at TEXT)",
        "CREATE TABLE IF NOT EXISTS wishlist (book_id TEXT PRIMARY KEY, added_at TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS recently_viewed (book_id TEXT PRIMARY KEY, viewed_at TEXT NOT NULL, "
        "view_count INTEGER NOT NULL DEFAULT 1)",
        "CREATE TABLE IF NOT EXISTS reading_list (book_id TEXT PRIMARY KEY, "
        "status TEXT NOT NULL CHECK (status IN ('To Read','Currently Reading','Completed')), "
        "added_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    ]
    for s in stmts:
        db_exec(s)


def db_save_books(books):
    rows = [(b["id"], json.dumps(b, ensure_ascii=False), now_iso()) for b in books if b and b.get("id")]
    if rows:
        db_exec("INSERT INTO books (book_id, data, saved_at) VALUES (?,?,?) ON CONFLICT(book_id) "
                "DO UPDATE SET data=excluded.data, saved_at=excluded.saved_at", rows, many=True)


def db_load_books():
    out = []
    for r in db_exec("SELECT data FROM books ORDER BY saved_at ASC", fetch=True) or []:
        try:
            d = json.loads(r["data"])
            out.append({**blank_book(), **d})
        except (ValueError, TypeError):
            continue
    return out


def db_wishlist_ids():
    return [r["book_id"] for r in db_exec("SELECT book_id FROM wishlist ORDER BY added_at DESC", fetch=True) or []]


def db_recent_ids(limit=24):
    return [r["book_id"] for r in db_exec(
        "SELECT book_id FROM recently_viewed ORDER BY viewed_at DESC LIMIT ?", (limit,), fetch=True) or []]


def db_reading_map():
    return {r["book_id"]: r["status"] for r in db_exec(
        "SELECT book_id, status FROM reading_list ORDER BY updated_at DESC", fetch=True) or []}


def db_clear_unused_cache():
    db_exec("DELETE FROM books WHERE book_id NOT IN (SELECT book_id FROM wishlist) "
            "AND book_id NOT IN (SELECT book_id FROM reading_list) "
            "AND book_id NOT IN (SELECT book_id FROM recently_viewed)")


# =====================================================================
# 5. API FUNCTIONS (Google Books + Open Library) WITH CACHING / RETRIES
# =====================================================================
class ApiError(Exception):
    pass


@st.cache_resource
def _cache_store():
    return {"data": {}, "lock": threading.Lock()}


STORE = _cache_store()


def cache_get(key):
    with STORE["lock"]:
        item = STORE["data"].get(key)
        if item and item[0] > time.time():
            return item[1]
    return None


def cache_put(key, val, ttl=CACHE_TTL):
    with STORE["lock"]:
        d = STORE["data"]
        if len(d) > 3000:
            for k in list(d.keys())[:500]:
                d.pop(k, None)
        d[key] = (time.time() + ttl, val)


def http_json(url, params=None):
    """GET JSON with caching, timeout, retries and rate-limit handling. Failures are not cached."""
    key = url + "?" + json.dumps(params or {}, sort_keys=True, default=str)
    hit = cache_get(key)
    if hit is not None:
        return hit
    last = "unknown error"
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
        except requests.Timeout:
            last = "the request timed out"
            time.sleep(0.5 * (attempt + 1))
            continue
        except requests.RequestException:
            last = "a network error occurred"
            time.sleep(0.5 * (attempt + 1))
            continue
        if r.status_code == 200:
            try:
                data = r.json()
            except ValueError:
                last = "the service returned an invalid response"
                break
            cache_put(key, data)
            return data
        if r.status_code == 429:
            last = "the rate limit was reached"
            try:
                wait = float(r.headers.get("Retry-After", 1.5 * (attempt + 1)))
            except ValueError:
                wait = 1.5 * (attempt + 1)
            time.sleep(min(wait, 4))
            continue
        if r.status_code >= 500:
            last = f"the server returned an error ({r.status_code})"
            time.sleep(0.8 * (attempt + 1))
            continue
        last = f"the request was refused (HTTP {r.status_code})"
        break
    raise ApiError(last)


def sanitize_gb(q):
    return re.sub(r'["\\]', " ", q or "").strip()


def sanitize_ol(q):
    return re.sub(r'[\+\-!\(\)\{\}\[\]\^"~\*\?:\\/]', " ", q or "").strip()


def build_gb_query(p):
    q, t, parts = sanitize_gb(p["q"]), p["type"], []
    if q:
        if t == "Title":
            parts.append(f'intitle:"{q}"')
        elif t == "Author":
            parts.append(f'inauthor:"{q}"')
        elif t == "ISBN":
            parts.append("isbn:" + re.sub(r"[^0-9Xx]", "", q))
        elif t == "Subject / Category":
            parts.append(f'subject:"{q}"')
        else:
            parts.append(q)
    if p["author"] and t != "Author":
        parts.append(f'inauthor:"{sanitize_gb(p["author"])}"')
    if p["category"] != "Any" and t != "Subject / Category":
        parts.append(f'subject:"{p["category"]}"')
    return " ".join(parts)


def build_ol_query(p):
    q, t, parts = sanitize_ol(p["q"]), p["type"], []
    if q:
        if t == "Title":
            parts.append(f"title:({q})")
        elif t == "Author":
            parts.append(f"author:({q})")
        elif t == "ISBN":
            parts.append("isbn:" + re.sub(r"[^0-9Xx]", "", q))
        elif t == "Subject / Category":
            parts.append(f'subject:"{q}"')
        else:
            parts.append(f"({q})")
    if p["author"] and t != "Author":
        parts.append(f"author:({sanitize_ol(p['author'])})")
    if p["category"] != "Any" and t != "Subject / Category":
        parts.append(f'subject:"{p["category"]}"')
    ol_lang = LANGUAGES[p["lang"]][1]
    if ol_lang and parts:
        parts.append(f"language:{ol_lang}")
    if COUNTRIES.get(p["country"]) and parts:
        parts.append(f'publish_place:"{p["country"]}"')
    return " AND ".join(parts)


def gb_fetch(p, page):
    q = build_gb_query(p)
    if not q:
        return [], 0
    params = {"q": q, "startIndex": (page - 1) * PER_SOURCE, "maxResults": PER_SOURCE,
              "printType": "books", "country": COUNTRIES.get(p["country"]) or "IN"}
    lang = LANGUAGES[p["lang"]][0]
    if lang:
        params["langRestrict"] = lang
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY
    data = http_json(GB_URL, params)
    books = [b for b in (normalize_google(i) for i in (data.get("items") or [])) if b]
    return books, to_int(data.get("totalItems")) or 0


def ol_fetch(p, page):
    q = build_ol_query(p)
    if not q:
        return [], 0
    data = http_json(OL_SEARCH_URL, {"q": q, "page": page, "limit": PER_SOURCE, "fields": OL_FIELDS})
    books = [b for b in (normalize_open_library(d) for d in (data.get("docs") or [])) if b]
    return books, to_int(data.get("numFound")) or 0


def fetch_page(p, page):
    """Fetch one page from both APIs in parallel; a failing API never blocks the other."""
    out = {"books": [], "gb_total": None, "ol_total": None, "errors": {}}

    def run(name, fn):
        try:
            return name, fn(p, page), None
        except ApiError as exc:
            return name, None, str(exc)
        except Exception:
            return name, None, "an unexpected error occurred"

    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(run, "Google Books", gb_fetch), ex.submit(run, "Open Library", ol_fetch)]
        results = [f.result() for f in futs]
    lists = {}
    for name, val, err in results:
        if err:
            out["errors"][name] = err
        else:
            lists[name] = val[0]
            out["gb_total" if name == "Google Books" else "ol_total"] = val[1]
    merged = [b for pair in zip_longest(lists.get("Google Books", []), lists.get("Open Library", []))
              for b in pair if b]
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(resolve_cover, merged))
    out["books"] = merged
    return out


def extract_desc(x):
    if isinstance(x, dict):
        x = x.get("value")
    if isinstance(x, list) and x:
        x = x[0]
    return clean_text(x) if isinstance(x, str) else ""


def enrich_book(b):
    """Fetch a missing description from Open Library (on demand, cached)."""
    if b.get("_enriched") or b.get("description"):
        return
    desc = ""
    try:
        if b.get("ol_key"):
            desc = extract_desc(http_json(f"https://openlibrary.org{b['ol_key']}.json").get("description"))
        if not desc and b.get("isbn"):
            d = http_json(f"https://openlibrary.org/isbn/{b['isbn']}.json")
            desc = extract_desc(d.get("description")) or extract_desc(d.get("first_sentence"))
            if not desc and d.get("works"):
                wk = d["works"][0].get("key")
                if wk:
                    desc = extract_desc(http_json(f"https://openlibrary.org{wk}.json").get("description"))
                    if not b.get("ol_key"):
                        b["ol_key"] = wk
        b["_enriched"] = True
    except (ApiError, KeyError, IndexError, TypeError):
        return
    if desc:
        b["description"] = desc
    finalize(b)
    db_save_books([b])


# =====================================================================
# 6. BOOK NORMALIZATION AND DEDUPLICATION
# =====================================================================
BOOK_FIELDS = ["id", "title", "authors", "author", "isbn", "isbns", "category", "description", "year",
               "publisher", "language", "language_code", "pages", "rating", "ratings_count", "cover_url",
               "cover_i", "thumb_gb", "gb_id", "ol_key", "gb_url", "ol_url", "purchase_url", "details_url",
               "price", "currency", "price_type", "source"]


def blank_book():
    b = {k: None for k in BOOK_FIELDS}
    b["authors"], b["isbns"] = [], []
    return b


def clean_isbn(x):
    return re.sub(r"[^0-9Xx]", "", str(x or "")).upper()


def normalize_google(item):
    v, s = item.get("volumeInfo") or {}, item.get("saleInfo") or {}
    vid, title = item.get("id"), clean_text(v.get("title"))
    if not vid or not title:
        return None
    if v.get("subtitle"):
        title = f"{title}: {clean_text(v['subtitle'])}"
    isbns = []
    for ident in v.get("industryIdentifiers") or []:
        n = clean_isbn(ident.get("identifier"))
        if n and str(ident.get("type", "")).startswith("ISBN"):
            isbns.append(n)
    cats = v.get("categories") or []
    img = v.get("imageLinks") or {}
    thumb = img.get("thumbnail") or img.get("smallThumbnail")
    rp = s.get("retailPrice") or s.get("listPrice") or {}
    price, cur = to_float(rp.get("amount")), rp.get("currencyCode")
    b = blank_book()
    b.update({
        "id": f"gb:{vid}", "gb_id": vid, "title": title,
        "authors": [clean_text(a) for a in (v.get("authors") or []) if a],
        "isbns": isbns, "isbn": next((i for i in isbns if len(i) == 13), isbns[0] if isbns else ""),
        "category": clean_text(cats[0]).split("/")[0].strip() if cats else "Uncategorized",
        "description": clean_text(v.get("description")), "year": year_from(v.get("publishedDate")),
        "publisher": clean_text(v.get("publisher")), "language_code": v.get("language"),
        "language": GB_LANG_NAMES.get(v.get("language"), (v.get("language") or "").upper() or None),
        "pages": to_int(v.get("pageCount")) or None,
        "rating": to_float(v.get("averageRating")), "ratings_count": to_int(v.get("ratingsCount")),
        "thumb_gb": https(thumb).replace("&edge=curl", "") if thumb else None,
        "gb_url": safe_url(v.get("canonicalVolumeLink")) or f"https://books.google.com/books?id={vid}",
        "purchase_url": safe_url(s.get("buyLink")) if s.get("saleability") == "FOR_SALE" else None,
        "price": price if (price is not None and cur) else None,
        "currency": cur if (price is not None and cur) else None,
        "price_type": "Actual" if (price is not None and cur) else None,
        "source": "Google Books",
    })
    return b


def normalize_open_library(doc):
    key, title = doc.get("key"), clean_text(doc.get("title"))
    if not key or not title:
        return None
    isbns = [clean_isbn(i) for i in (doc.get("isbn") or [])[:25]]
    isbns = [i for i in isbns if len(i) in (10, 13)]
    subjects = [s for s in (doc.get("subject") or []) if str(s).strip().lower() not in OL_BAD_SUBJECTS]
    langs = doc.get("language") or []
    rating = to_float(doc.get("ratings_average"))
    b = blank_book()
    b.update({
        "id": f"ol:{key}", "ol_key": key, "title": title,
        "authors": [clean_text(a) for a in (doc.get("author_name") or [])[:6] if a],
        "isbns": isbns, "isbn": next((i for i in isbns if len(i) == 13), isbns[0] if isbns else ""),
        "category": clean_text(subjects[0]) if subjects else "Uncategorized",
        "year": to_int(doc.get("first_publish_year")),
        "publisher": clean_text((doc.get("publisher") or [""])[0]),
        "language_code": langs[0] if langs else None,
        "language": OL_LANG_NAMES.get(langs[0], langs[0].upper()) if langs else None,
        "pages": to_int(doc.get("number_of_pages_median")) or None,
        "rating": round(rating, 2) if rating and rating > 0 else None,
        "ratings_count": to_int(doc.get("ratings_count")), "cover_i": doc.get("cover_i"),
        "ol_url": f"https://openlibrary.org{key}", "source": "Open Library",
    })
    return b


def title_key(b):
    t = re.split(r"[:\-–(]", (b.get("title") or "").lower())[0]
    t = re.sub(r"[^a-z0-9\u0080-\uffff]+", "", t)
    a = (b.get("authors") or [""])[0].lower().split()
    a = re.sub(r"[^a-z0-9\u0080-\uffff]+", "", a[-1]) if a else "unknown"
    return f"{t}|{a}" if t else ""


FILL_FIELDS = ["title", "isbn", "category", "description", "year", "publisher", "language", "language_code",
               "pages", "rating", "ratings_count", "cover_url", "cover_i", "thumb_gb", "gb_id", "ol_key",
               "gb_url", "ol_url", "purchase_url", "details_url"]


def merge_book(dst, src):
    """Merge duplicate records: keep dst, fill its gaps from src."""
    for f in FILL_FIELDS:
        if is_empty(dst.get(f)) and not is_empty(src.get(f)):
            dst[f] = src[f]
    if "covers.openlibrary.org" in str(src.get("cover_url") or "") and \
            "covers.openlibrary.org" not in str(dst.get("cover_url") or ""):
        dst["cover_url"] = src["cover_url"]
    if not dst.get("authors") and src.get("authors"):
        dst["authors"] = src["authors"]
    dst["isbns"] = sorted(set(dst.get("isbns") or []) | set(src.get("isbns") or []))
    if src.get("price_type") == "Actual" and dst.get("price_type") != "Actual":
        dst["price"], dst["currency"], dst["price_type"] = src["price"], src["currency"], "Actual"
    srcs = set((dst.get("source") or "").split(" + ")) | set((src.get("source") or "").split(" + "))
    dst["source"] = " + ".join(sorted(x for x in srcs if x))


def get_book(bid):
    return st.session_state.pool.get(bid)


def register_book(b):
    """Add a book to the session dataset, merging it with an existing duplicate (ISBN / title+author)."""
    ss = st.session_state
    existing = b["id"] if b["id"] in ss.pool else None
    if not existing:
        for i in b.get("isbns") or []:
            if i in ss.isbn_idx and ss.isbn_idx[i] in ss.pool:
                existing = ss.isbn_idx[i]
                break
    tk = title_key(b)
    if not existing and tk and tk in ss.tkey_idx and ss.tkey_idx[tk] in ss.pool:
        existing = ss.tkey_idx[tk]
    if existing:
        target = ss.pool[existing]
        if target is not b:
            merge_book(target, b)
    else:
        target = b
        ss.pool[b["id"]] = b
    finalize(target)
    for i in target.get("isbns") or []:
        ss.isbn_idx[i] = target["id"]
    tk = title_key(target)
    if tk:
        ss.tkey_idx[tk] = target["id"]
    return target


# =====================================================================
# 7. BOOK COVER HANDLING
# =====================================================================
def cover_ok(url):
    key = "cover:" + url
    hit = cache_get(key)
    if hit is not None:
        return hit
    ok = False
    try:
        r = requests.get(url, headers=HTTP_HEADERS, timeout=6, stream=True)
        ok = r.status_code == 200 and "image" in r.headers.get("Content-Type", "image")
        r.close()
    except requests.RequestException:
        ok = False
    cache_put(key, ok, ttl=6 * 3600)
    return ok


def resolve_cover(b):
    """Priority: Open Library cover (id, then verified ISBN cover) -> Google Books thumbnail."""
    if b.get("cover_url"):
        return
    if b.get("cover_i"):
        b["cover_url"] = f"https://covers.openlibrary.org/b/id/{b['cover_i']}-L.jpg"
        return
    if b.get("isbn"):
        url = f"https://covers.openlibrary.org/b/isbn/{b['isbn']}-L.jpg?default=false"
        if cover_ok(url):
            b["cover_url"] = url
            return
    if b.get("thumb_gb"):
        b["cover_url"] = https(b["thumb_gb"])


def cover_html(b, size="card"):
    url = safe_url(b.get("cover_url"))
    img = (f'<img src="{e(url)}" alt="" loading="lazy" referrerpolicy="no-referrer" '
           f'onerror="this.style.display=\'none\'">') if url else ""
    return (f'<div class="bl-cover bl-cover-{size}"><div class="bl-nocover">Cover<br>Not Available</div>'
            f'{img}</div>')


# =====================================================================
# 8. PRICE MANAGEMENT
# =====================================================================
def estimate_price_inr(b):
    """Reasonable INR estimate from page count (clearly labelled 'Estimated' everywhere)."""
    pages = b.get("pages") or 300
    base = 120 + pages * 0.75
    if (b.get("year") or 0) >= 2015:
        base *= 1.1
    base = max(149, min(base, 1999))
    return float(int(round(base / 10.0) * 10 - 1))


def finalize(b):
    """Derive display author, links and (if needed) an estimated price."""
    b["author"] = ", ".join(b["authors"]) if b.get("authors") else "Unknown"
    if b.get("price") is None or b.get("price_type") != "Actual":
        b["price"], b["currency"], b["price_type"] = estimate_price_inr(b), "INR", "Estimated"
    if b.get("isbn") and b["isbn"] not in (b.get("isbns") or []):
        b["isbns"] = (b.get("isbns") or []) + [b["isbn"]]
    if not b.get("gb_url"):
        if b.get("gb_id"):
            b["gb_url"] = f"https://books.google.com/books?id={b['gb_id']}"
        elif b.get("isbn"):
            b["gb_url"] = f"https://books.google.com/books?vid=ISBN{b['isbn']}"
    if not b.get("ol_url"):
        if b.get("ol_key"):
            b["ol_url"] = f"https://openlibrary.org{b['ol_key']}"
        elif b.get("isbn"):
            b["ol_url"] = f"https://openlibrary.org/search?q=isbn%3A{b['isbn']}"
    b["details_url"] = b.get("details_url") or b.get("ol_url") or b.get("gb_url")


def fmt_price(b):
    p, c = b.get("price"), b.get("currency") or "INR"
    if p is None:
        return "Price unavailable"
    amt = f"{p:,.0f}" if float(p).is_integer() else f"{p:,.2f}"
    sym = CURRENCY_SYMBOLS.get(c)
    return f"{sym}{amt}" if sym else f"{c} {amt}"


def price_html(b):
    actual = b.get("price_type") == "Actual"
    cls, label = ("bl-tag-actual", "Actual price") if actual else ("bl-tag-est", "Estimated")
    return f'<span class="bl-price">{e(fmt_price(b))}</span><span class="bl-tag {cls}">{label}</span>'


def rating_html(b):
    if not b.get("rating"):
        return '<div class="bl-rating"><small>Not rated</small></div>'
    cnt = f' <small>({fmt_int(b["ratings_count"])})</small>' if b.get("ratings_count") else ""
    return f'<div class="bl-rating">★ {b["rating"]:.1f}{cnt}</div>'


# =====================================================================
# 9. SEARCH AND PAGINATION
# =====================================================================
def do_search():
    ss = st.session_state
    p = {"type": ss.f_type, "q": (ss.f_query or "").strip(), "author": (ss.f_author or "").strip(),
         "category": ss.f_category, "lang": ss.f_lang, "country": ss.f_country}
    if not (p["q"] or p["author"] or p["category"] != "Any"):
        ss.search_error = "Enter a title, author, ISBN or keyword (or choose a category) to search."
        go("Explore Worldwide Books")
        return
    ss.search_error = None
    ss.search, ss.results, ss.loaded_pages, ss.meta, ss.page_no = p, [], [], {}, 1
    ss.pending_fetch = {"page": 1, "append": False}
    go("Explore Worldwide Books")


def home_search():
    st.session_state.f_query = st.session_state.get("home_q", "")
    st.session_state.f_type = "Keywords"
    do_search()


def quick_search(q, stype, lang, cat):
    ss = st.session_state
    ss.f_query, ss.f_type, ss.f_lang, ss.f_category, ss.f_author = q, stype, lang, cat, ""
    do_search()


def goto_page(n, append=False):
    st.session_state.pending_fetch = {"page": max(1, n), "append": append}


def process_pending():
    ss = st.session_state
    pend = ss.pending_fetch
    if not pend or not ss.search:
        ss.pending_fetch = None
        return
    ss.pending_fetch = None
    ph = st.empty()
    ph.markdown(LOADER_HTML, unsafe_allow_html=True)
    data = fetch_page(ss.search, pend["page"])
    ph.empty()
    if len(data["errors"]) == 2:  # both failed: keep what is on screen
        ss.meta = {**ss.meta, "errors": data["errors"], "failed": True}
        return
    ids = []
    existing = set(ss.results) if pend["append"] else set()
    targets = []
    for b in data["books"]:
        t = register_book(b)
        targets.append(t)
        if t["id"] not in existing and t["id"] not in ids:
            ids.append(t["id"])
    db_save_books(targets)
    ss.results = (ss.results + ids) if pend["append"] else ids
    ss.page_no = pend["page"]
    ss.loaded_pages = (ss.loaded_pages + [pend["page"]]) if pend["append"] else [pend["page"]]
    gb, ol = data["gb_total"], data["ol_total"]
    pages = max(math.ceil(gb / PER_SOURCE) if gb else 0, math.ceil(ol / PER_SOURCE) if ol else 0)
    ss.meta = {"gb_total": gb, "ol_total": ol, "errors": data["errors"], "total_pages": pages,
               "last_count": len(data["books"])}


def apply_client_filters(books):
    ss = st.session_state
    rmin, pmin, pmax = float(ss.c_rating), float(ss.c_pmin), float(ss.c_pmax)
    ymin, ymax = int(ss.c_ymin), int(ss.c_ymax)
    out = []
    for b in books:
        if rmin > 0 and (b.get("rating") or 0) < rmin:
            continue
        y = b.get("year")
        if (ymin and (not y or y < ymin)) or (ymax and (not y or y > ymax)):
            continue
        if pmin > 0 or pmax > 0:
            if b.get("currency") != "INR" or b.get("price") is None:
                continue
            if (pmin > 0 and b["price"] < pmin) or (pmax > 0 and b["price"] > pmax):
                continue
        out.append(b)
    if ss.c_sort != "Relevance":
        keyf = {"Title": lambda b: (b.get("title") or "").lower(), "Rating": lambda b: b.get("rating"),
                "Price": lambda b: b.get("price") if b.get("currency") == "INR" else None,
                "Publication year": lambda b: b.get("year")}[ss.c_sort]
        present = [b for b in out if keyf(b) is not None]
        missing = [b for b in out if keyf(b) is None]
        present.sort(key=keyf, reverse=(ss.c_dir == "Descending"))
        out = present + missing
    return out


# =====================================================================
# 10. SESSION STATE AND NAVIGATION
# =====================================================================
def init_state():
    ss = st.session_state
    if ss.get("_init"):
        return
    init_db()
    ss.section, ss.nav_history, ss.selected_id = SECTION_NAMES[0], [SECTION_NAMES[0]], None
    ss.pool, ss.isbn_idx, ss.tkey_idx = {}, {}, {}
    ss.results, ss.page_no, ss.loaded_pages, ss.meta = [], 1, [], {}
    ss.search, ss.search_error, ss.pending_fetch = None, None, None
    ss.compare_ids, ss.random_id, ss.random_request = [], None, False
    ss.wish_ids, ss.reading = set(db_wishlist_ids()), db_reading_map()
    ss.user_reviews, ss.ui_store, ss.imported_files = [], {}, set()
    for b in db_load_books():
        register_book(b)
    ss._init = True


def restore_ui():
    for k, v in UI_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = st.session_state.ui_store.get(k, v)


def persist_ui():
    for k in UI_DEFAULTS:
        if k in st.session_state:
            st.session_state.ui_store[k] = st.session_state[k]


def go(section):
    ss = st.session_state
    ss.section = section
    h = ss.nav_history
    if not h or h[-1] != section:  # no duplicate consecutive entries
        h.append(section)
        del h[:-12]


def open_book(bid):
    b = get_book(bid)
    if not b:
        return
    st.session_state.selected_id = bid
    db_save_books([b])
    db_exec("INSERT INTO recently_viewed (book_id, viewed_at, view_count) VALUES (?,?,1) "
            "ON CONFLICT(book_id) DO UPDATE SET viewed_at=excluded.viewed_at, view_count=view_count+1",
            (bid, now_iso()))
    go("Book Details")


def toggle_wishlist(bid):
    ss, b = st.session_state, get_book(bid)
    if bid in ss.wish_ids:
        db_exec("DELETE FROM wishlist WHERE book_id=?", (bid,))
        ss.wish_ids.discard(bid)
        st.toast("Removed from wishlist")
    elif b:
        db_save_books([b])
        db_exec("INSERT OR IGNORE INTO wishlist (book_id, added_at) VALUES (?,?)", (bid, now_iso()))
        ss.wish_ids.add(bid)
        st.toast("Added to wishlist")


def toggle_compare(bid):
    ss = st.session_state
    if bid in ss.compare_ids:
        ss.compare_ids.remove(bid)
        st.toast("Removed from comparison")
    else:
        ss.compare_ids = (ss.compare_ids + [bid])[-2:]
        st.toast(f"Added to comparison ({len(ss.compare_ids)}/2)")


def set_reading(bid, status):
    ss, b = st.session_state, get_book(bid)
    if not b or status not in STATUSES:
        return
    db_save_books([b])
    ts = now_iso()
    db_exec("INSERT INTO reading_list (book_id, status, added_at, updated_at) VALUES (?,?,?,?) "
            "ON CONFLICT(book_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at",
            (bid, status, ts, ts))
    ss.reading[bid] = status


def remove_reading(bid):
    db_exec("DELETE FROM reading_list WHERE book_id=?", (bid,))
    st.session_state.reading.pop(bid, None)
    st.toast("Removed from reading list")


def render_nav_bar():
    ss = st.session_state
    i = SECTION_NAMES.index(ss.section)
    prev_name = SECTION_NAMES[i - 1] if i > 0 else None
    next_name = SECTION_NAMES[i + 1] if i < len(SECTION_NAMES) - 1 else None
    c1, c2, c3 = st.columns([1.3, 4, 1.3])
    c1.button(f"← {SECTION_INFO[prev_name][1]}" if prev_name else "← Back", key="nav_back",
              disabled=prev_name is None, on_click=go, args=(prev_name or SECTION_NAMES[0],))
    crumb = "BookLens › Home" if ss.section == "Home" else f"BookLens › Home › <b>{e(ss.section)}</b>"
    sel = get_book(ss.selected_id) if ss.selected_id else None
    if ss.section == "Book Details" and sel:
        crumb += f" › {e(sel['title'][:50])}"
    trail = " → ".join(SECTION_INFO[s][1] for s in ss.nav_history[-5:])
    c2.markdown(
        f'<div class="bl-navmid"><div class="bl-crumb">{crumb}</div>'
        f'<div class="bl-sectitle">{SECTION_INFO[ss.section][2]} {e(ss.section)}</div>'
        f'<span class="bl-pill">Section {i + 1} of {len(SECTION_NAMES)}</span>'
        f'<div class="bl-trail">Visited: {e(trail)}</div></div>', unsafe_allow_html=True)
    c3.button(f"{SECTION_INFO[next_name][1]} →" if next_name else "Next →", key="nav_next",
              disabled=next_name is None, on_click=go, args=(next_name or SECTION_NAMES[-1],))
    for row in (0, 1):
        cols = st.columns(6)
        for j, col in enumerate(cols):
            idx = row * 6 + j
            name = SECTION_NAMES[idx]
            col.button(f"{SECTION_INFO[name][2]} {SECTION_INFO[name][1]}", key=f"menu_{idx}",
                       type="primary" if name == ss.section else "secondary", on_click=go, args=(name,))
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)


# =====================================================================
# 11. BOOK CARDS
# =====================================================================
def card_html(b):
    chips = []
    if b.get("year"):
        chips.append(str(b["year"]))
    if b.get("category") and b["category"] != "Uncategorized":
        chips.append(e(b["category"][:22]))
    if b.get("language"):
        chips.append(e(b["language"]))
    chip_html = "".join(f'<span class="bl-chip">{c}</span>' for c in chips)
    return (f'<div class="bl-card">{cover_html(b)}<div class="bl-title">{e(b["title"])}</div>'
            f'<div class="bl-author">by {e(b["author"])}</div><div>{chip_html}</div>'
            f'{rating_html(b)}<div>{price_html(b)}</div></div>')


def book_card(b, ctx):
    ss, bid = st.session_state, b["id"]
    st.markdown(card_html(b), unsafe_allow_html=True)
    st.button("View Details", key=f"{ctx}_view_{bid}", on_click=open_book, args=(bid,))
    a, c = st.columns(2)
    saved = bid in ss.wish_ids
    if ctx == "wish":
        wl = "✕ Remove"
    else:
        wl = "♥ Saved" if saved else "♡ Wishlist"
    a.button(wl, key=f"{ctx}_wish_{bid}", on_click=toggle_wishlist, args=(bid,))
    c.button("✓ Comparing" if bid in ss.compare_ids else "⇄ Compare", key=f"{ctx}_cmp_{bid}",
             on_click=toggle_compare, args=(bid,))


def render_grid(ids, ctx, cols=4):
    books = [get_book(i) for i in ids if get_book(i)]
    for start in range(0, len(books), cols):
        columns = st.columns(cols)
        for col, b in zip(columns, books[start:start + cols]):
            with col:
                book_card(b, ctx)


def ranked_row(b, rank, ctx, extra=""):
    c0, c1, c2, c3 = st.columns([0.6, 1.2, 5, 1.6])
    c0.markdown(f'<div class="bl-rank">#{rank}</div>', unsafe_allow_html=True)
    c1.markdown(cover_html(b, "sm"), unsafe_allow_html=True)
    c2.markdown(f'<div class="bl-title" style="min-height:0">{e(b["title"])}</div>'
                f'<div class="bl-author">by {e(b["author"])}</div>{rating_html(b)}{extra}',
                unsafe_allow_html=True)
    c3.button("View Details", key=f"{ctx}_view_{b['id']}", on_click=open_book, args=(b["id"],))
    st.markdown("<hr style='border-color:rgba(196,181,253,.12);margin:.3rem 0'>", unsafe_allow_html=True)


def section_header(title, sub=""):
    st.markdown(f'<div class="bl-h2">{e(title)}</div><div class="bl-sub">{e(sub)}</div>', unsafe_allow_html=True)


def empty_state(msg, button_label="Explore Worldwide Books", target="Explore Worldwide Books", key="empty"):
    st.markdown(f'<div class="glass">{e(msg)}</div>', unsafe_allow_html=True)
    st.button(f"Go to {button_label}", key=f"{key}_go", on_click=go, args=(target,))


def pick_label(bid):
    b = get_book(bid)
    return f"{b['title'][:60]} — {b['author'][:30]}" if b else str(bid)


def book_options(extra=()):
    ids = list(st.session_state.pool.keys())[-1000:]
    for x in extra:
        if x and x in st.session_state.pool and x not in ids:
            ids.append(x)
    return ids


# =====================================================================
# 12. BOOK DETAILS
# =====================================================================
def link_buttons(b):
    items = [("Open Library page", safe_url(b.get("ol_url")), "Link Not Available"),
             ("Google Books page", safe_url(b.get("gb_url")), "Link Not Available"),
             ("Purchase website", safe_url(b.get("purchase_url")), "Purchase Link Not Available")]
    dl = safe_url(b.get("details_url"))
    if dl and dl not in (b.get("ol_url"), b.get("gb_url")):
        items.append(("Book page", dl, "Link Not Available"))
    cols = st.columns(len(items))
    for col, (label, url, missing) in zip(cols, items):
        with col:
            if url:
                st.link_button(label, url)  # opens in a new browser tab
            else:
                st.markdown(f'<div class="bl-unavail">{missing}</div>', unsafe_allow_html=True)


def add_reading_from_details():
    ss = st.session_state
    set_reading(ss.selected_id, ss.get("det_status", STATUSES[0]))
    st.toast("Reading list updated")


def render_details():
    ss = st.session_state
    b = get_book(ss.selected_id) if ss.selected_id else None
    if not b:
        empty_state("No book selected yet. Search for a book and press “View Details”.", key="det_empty")
        return
    if not b.get("description") and not b.get("_enriched"):
        with st.spinner("Loading more details from Open Library…"):
            enrich_book(b)
    left, right = st.columns([1, 2])
    with left:
        st.markdown(cover_html(b, "lg"), unsafe_allow_html=True)
        st.button("♥ Saved — remove" if b["id"] in ss.wish_ids else "♡ Add to wishlist", key="det_wish",
                  on_click=toggle_wishlist, args=(b["id"],))
        st.button("✓ In comparison" if b["id"] in ss.compare_ids else "⇄ Add to comparison", key="det_cmp",
                  on_click=toggle_compare, args=(b["id"],))
        cur = ss.reading.get(b["id"])
        st.selectbox("Reading list status", STATUSES, key="det_status",
                     index=STATUSES.index(cur) if cur in STATUSES else 0)
        st.button("📚 Update reading list" if cur else "📚 Add to reading list", key="det_read",
                  on_click=add_reading_from_details)
    with right:
        st.markdown(f'<div class="bl-h2" style="font-size:2rem">{e(b["title"])}</div>'
                    f'<div class="bl-sub" style="font-size:1.1rem">by {e(b["author"])}</div>'
                    f'{rating_html(b)}<div style="margin:.3rem 0">{price_html(b)}</div>',
                    unsafe_allow_html=True)
        if b.get("price_type") != "Actual":
            st.markdown('<div class="bl-note">This price is an <b>estimate</b> in INR based on page count. '
                        'It is not a store price.</div>', unsafe_allow_html=True)
        desc = e(b["description"]) if b.get("description") else "No description is available for this book."
        st.markdown(f'<div class="glass"><div class="bl-desc">{desc}</div></div>', unsafe_allow_html=True)
        rows = [("ISBN", b.get("isbn") or "Not available"), ("Publisher", b.get("publisher") or "Not available"),
                ("Publication year", b.get("year") or "Not available"),
                ("Category", b.get("category") or "Not available"),
                ("Language", b.get("language") or "Not available"),
                ("Page count", b.get("pages") or "Not available"),
                ("Rating", f"{b['rating']:.1f} / 5" if b.get("rating") else "Not rated"),
                ("Number of ratings", fmt_int(b.get("ratings_count")) if b.get("ratings_count") else "Not available"),
                ("Price", fmt_price(b)), ("Price type", b.get("price_type") or "Not available"),
                ("Data source", b.get("source") or "Not available")]
        table = "".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>" for k, v in rows)
        st.markdown(f'<div class="glass"><table class="bl-spec">{table}</table></div>', unsafe_allow_html=True)
        link_buttons(b)
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    c1, c2, _ = st.columns([1.3, 1.3, 3])
    c1.button("← Back to Search Results", key="det_back", on_click=go, args=("Explore Worldwide Books",))
    c2.button("✨ See recommendations", key="det_rec", on_click=go, args=("Book Recommendations",))


# =====================================================================
# 13. EXPLORE (SEARCH PAGE)
# =====================================================================
def pagination_bar(pos):
    ss = st.session_state
    page, total = ss.page_no, ss.meta.get("total_pages", 0)
    has_next = bool(total) and page < total and ss.meta.get("last_count", 0) > 0
    c = st.columns([1, 1.5, 1, 1.2])
    c[0].button("◀ Previous", key=f"pg_prev_{pos}", disabled=page <= 1, on_click=goto_page, args=(page - 1, False))
    pages_txt = f"of {total:,}" if total else ""
    loaded = f" · pages {min(ss.loaded_pages)}–{max(ss.loaded_pages)} loaded" if len(ss.loaded_pages) > 1 else ""
    c[1].markdown(f'<div class="bl-navmid"><span class="bl-pill">Page {page} {pages_txt}</span>'
                  f'<div class="bl-trail">{e(loaded)}</div></div>', unsafe_allow_html=True)
    c[2].button("Next ▶", key=f"pg_next_{pos}", disabled=not has_next, on_click=goto_page, args=(page + 1, False))
    c[3].button("＋ Load more", key=f"pg_more_{pos}", disabled=not has_next, on_click=goto_page, args=(page + 1, True))


def render_explore():
    ss = st.session_state
    section_header("Explore Worldwide Books",
                   "Searches Google Books and Open Library live — results are not limited to a fixed catalogue.")
    with st.form("search_form"):
        a, b_ = st.columns([1, 3])
        a.selectbox("Search by", SEARCH_TYPES, key="f_type")
        b_.text_input("Search", key="f_query", placeholder="e.g. Dune, Chimamanda Adichie, 9780143127741, machine learning")
        c1, c2, c3, c4 = st.columns(4)
        c1.text_input("Author (optional)", key="f_author")
        c2.selectbox("Category", CATEGORIES, key="f_category")
        c3.selectbox("Language", list(LANGUAGES), key="f_lang")
        c4.selectbox("Country / region", list(COUNTRIES), key="f_country")
        st.form_submit_button("🔍 Search worldwide catalogues", type="primary", on_click=do_search)
    st.caption("Country / region: Open Library results are filtered by publication place; Google Books uses it as the "
               "store region for availability and prices (default: India). Country is never guessed from language.")
    with st.expander("Refine and sort the loaded results", expanded=False):
        r1, r2, r3, r4 = st.columns(4)
        r1.selectbox("Sort by", ["Relevance", "Title", "Rating", "Price", "Publication year"], key="c_sort")
        r2.selectbox("Order", ["Ascending", "Descending"], key="c_dir")
        r3.selectbox("Minimum rating", [0.0, 3.0, 3.5, 4.0, 4.5], key="c_rating",
                     format_func=lambda x: "Any" if x == 0 else f"{x}+ stars")
        r4.number_input("Publication year from (0 = any)", min_value=0, max_value=2100, step=1, key="c_ymin")
        r5, r6, r7, _ = st.columns(4)
        r5.number_input("Minimum price ₹ (0 = any)", min_value=0, step=50, key="c_pmin")
        r6.number_input("Maximum price ₹ (0 = any)", min_value=0, step=50, key="c_pmax")
        r7.number_input("Publication year to (0 = any)", min_value=0, max_value=2100, step=1, key="c_ymax")
        st.caption("These refinements apply to the books loaded so far and combine with the search filters. "
                   "Price filters compare INR prices (actual or estimated). Sorting applies to loaded results only.")
    if ss.search_error:
        st.warning(ss.search_error)
    if not ss.search:
        st.markdown('<div class="glass">Start with a search above, or try one of these:</div>', unsafe_allow_html=True)
        cols = st.columns(len(SUGGESTED_SEARCHES))
        for i, (col, s) in enumerate(zip(cols, SUGGESTED_SEARCHES)):
            col.button(s[0], key=f"sugg_{i}", on_click=quick_search, args=s)
        return
    process_pending()
    meta = ss.meta
    for name, err in (meta.get("errors") or {}).items():
        other = "Open Library" if name == "Google Books" else "Google Books"
        if meta.get("failed"):
            st.error(f"{name} failed: {err}. The previous results are still shown — please try again shortly.")
        else:
            st.warning(f"{name} is unavailable right now ({err}); showing results from {other} only.")
    bits = []
    if meta.get("gb_total") is not None:
        bits.append(f"Google Books reports about {meta['gb_total']:,} matches")
    if meta.get("ol_total") is not None:
        bits.append(f"Open Library reports {meta['ol_total']:,} matches")
    p = ss.search
    desc = f"“{p['q']}”" if p["q"] else "your filters"
    st.markdown(f'<div class="glass"><b>Results for {e(desc)}</b> · {e(p["type"])} · {e(p["lang"])} · '
                f'{e(p["category"])}<br><span class="bl-sub">{e(" · ".join(bits)) if bits else "No totals reported."}'
                f'</span></div>', unsafe_allow_html=True)
    books = [get_book(i) for i in ss.results if get_book(i)]
    if not books:
        st.info("No books found for this search. Try different keywords, or remove some filters.")
        pagination_bar("top")
        return
    filtered = apply_client_filters(books)
    st.markdown(f"**{len(filtered)}** of **{len(books)}** loaded unique books shown "
                f"(up to {PAGE_SIZE} per page: {PER_SOURCE} per source, duplicates merged).")
    pagination_bar("top")
    if filtered:
        render_grid([b["id"] for b in filtered], "ex")
    else:
        st.info("No loaded books match the refine filters. Loosen them or load more results.")
    pagination_bar("bot")


# =====================================================================
# 14. WISHLIST  /  15. RECENTLY VIEWED
# =====================================================================
def render_wishlist():
    ss = st.session_state
    section_header("Wishlist", "Saved in SQLite — still here after restarting the app.")
    st.text_input("Search your wishlist", key="tw_q", placeholder="Filter by title or author")
    ids = [i for i in db_wishlist_ids() if get_book(i)]
    q = (ss.tw_q or "").strip().lower()
    if q:
        ids = [i for i in ids if q in get_book(i)["title"].lower() or q in get_book(i)["author"].lower()]
    if not ids:
        empty_state("Your wishlist is empty." if not q else "No saved books match your search.", key="wl")
        return
    st.markdown(f"**{len(ids)}** saved book(s)")
    render_grid(ids, "wish")


def clear_recent():
    db_exec("DELETE FROM recently_viewed")


def render_recent():
    section_header("Recently Viewed", "Books you opened, latest first. Stored in SQLite.")
    ids = [i for i in db_recent_ids(24) if get_book(i)]
    if not ids:
        empty_state("You haven’t opened any book details yet.", key="rv")
        return
    st.button("Clear viewing history", key="rv_clear", on_click=clear_recent)
    render_grid(ids, "rv")


# =====================================================================
# 16. COMPARISON
# =====================================================================
def set_cmp():
    ss = st.session_state
    new = []
    for k in ("cmp_pick_0", "cmp_pick_1"):
        if ss.get(k) and ss[k] not in new:
            new.append(ss[k])
    ss.compare_ids = new[-2:]


def render_comparison():
    ss = st.session_state
    section_header("Book Comparison", "Pick two books here, or use the Compare button on any book card.")
    if not ss.pool:
        empty_state("There are no books to compare yet.", key="cmp")
        return
    ids = ss.compare_ids
    ss.cmp_pick_0 = ids[0] if len(ids) > 0 else None
    ss.cmp_pick_1 = ids[1] if len(ids) > 1 else None
    opts = [None] + book_options(ids)
    fmt = lambda x: "— choose a book —" if x is None else pick_label(x)
    c1, c2 = st.columns(2)
    c1.selectbox("First book", opts, key="cmp_pick_0", format_func=fmt, on_change=set_cmp)
    c2.selectbox("Second book", opts, key="cmp_pick_1", format_func=fmt, on_change=set_cmp)
    if len(ss.compare_ids) < 2:
        st.info("Select two books to see the side-by-side comparison.")
        return
    a, b = get_book(ss.compare_ids[0]), get_book(ss.compare_ids[1])
    if not a or not b:
        return
    win_r = "A" if (a.get("rating") or 0) > (b.get("rating") or 0) else "B" if (b.get("rating") or 0) > (a.get("rating") or 0) else ""
    win_p = ""
    if a.get("currency") == b.get("currency") and a.get("price") != b.get("price"):
        win_p = "A" if a["price"] < b["price"] else "B"

    def row(label, va, vb, win=""):
        ca = ' class="win"' if win == "A" else ""
        cb = ' class="win"' if win == "B" else ""
        return f"<tr><td>{e(label)}</td><td{ca}>{e(va)}</td><td{cb}>{e(vb)}</td></tr>"

    def rt(x):
        return f"{x['rating']:.1f} ({fmt_int(x.get('ratings_count'))} ratings)" if x.get("rating") else "Not rated"

    def nz(v):
        return v if v else "Not available"

    head = (f'<tr><td></td><td>{cover_html(a, "md")}</td><td>{cover_html(b, "md")}</td></tr>')
    body = "".join([
        row("Title", a["title"], b["title"]), row("Author", a["author"], b["author"]),
        row("Category", nz(a.get("category")), nz(b.get("category"))),
        row("Price", fmt_price(a), fmt_price(b), win_p),
        row("Price type", a.get("price_type"), b.get("price_type")),
        row("Rating", rt(a), rt(b), win_r),
        row("Publication year", nz(a.get("year")), nz(b.get("year"))),
        row("Publisher", nz(a.get("publisher")), nz(b.get("publisher"))),
        row("Page count", nz(a.get("pages")), nz(b.get("pages"))),
        row("Language", nz(a.get("language")), nz(b.get("language")))])
    st.markdown(f'<div class="glass"><table class="bl-spec bl-cmp">{head}{body}</table></div>', unsafe_allow_html=True)
    st.caption("Green marks the higher rating and the lower price (only when both prices use the same currency).")
    d1, d2, d3 = st.columns(3)
    d1.button("View first book", key="cmp_v1", on_click=open_book, args=(a["id"],))
    d2.button("View second book", key="cmp_v2", on_click=open_book, args=(b["id"],))
    d3.button("Clear comparison", key="cmp_clear", on_click=lambda: st.session_state.update(compare_ids=[]))


# =====================================================================
# 17. RECOMMENDATIONS (related books + TF-IDF)
# =====================================================================
def kw_set(text):
    return {w for w in re.findall(r"[^\W\d_]{3,}", (text or "").lower()) if w not in ENGLISH_STOP_WORDS}


def related_books(b, n=8):
    ss = st.session_state
    auth = {a.lower() for a in b.get("authors") or []}
    kws = kw_set(b["title"])
    scored = []
    for o in ss.pool.values():
        if o["id"] == b["id"] or title_key(o) == title_key(b):
            continue
        score = 0.0
        if auth & {a.lower() for a in o.get("authors") or []}:
            score += 3
        if b.get("category") and b["category"] != "Uncategorized" and o.get("category") == b["category"]:
            score += 2
        score += min(len(kws & kw_set(o["title"])), 3)
        if score > 0:
            scored.append((score, o.get("ratings_count") or 0, o["id"]))
    scored.sort(reverse=True)
    return [x[2] for x in scored[:n]]


def book_text(b):
    return " ".join([(b.get("title") or "")] * 2 + [b.get("author") or ""] + [(b.get("category") or "")] * 2 +
                    [b.get("description") or ""])


@st.cache_data(show_spinner=False, max_entries=4)
def tfidf_scores(ids, texts, target_id):
    if len(ids) < 2 or target_id not in ids:
        return []
    try:
        X = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=30000).fit_transform(texts)
    except ValueError:
        return []
    idx = ids.index(target_id)
    sims = cosine_similarity(X[idx], X).ravel()
    order = np.argsort(-sims)
    return [(ids[i], float(sims[i])) for i in order if ids[i] != target_id and sims[i] > 0.01][:20]


def fetch_more_candidates(b):
    """Pull extra candidate books (same author / subject) from the APIs into the dataset."""
    base = {"q": "", "author": "", "category": "Any", "lang": "Any", "country": "Any"}
    queries = []
    if b.get("authors"):
        queries.append({**base, "type": "Author", "q": b["authors"][0]})
    if b.get("category") and b["category"] != "Uncategorized":
        queries.append({**base, "type": "Subject / Category", "q": b["category"]})
    added = []
    for q in queries:
        data = fetch_page(q, 1)
        for x in data["books"]:
            added.append(register_book(x))
    db_save_books(added)
    return len(added)


def set_selected_from_pick():
    st.session_state.selected_id = st.session_state.rec_pick


def render_recommendations():
    ss = st.session_state
    section_header("Book Recommendations", "Related books and content-based suggestions (TF-IDF + cosine similarity).")
    opts = book_options([ss.selected_id])
    if not opts:
        empty_state("Search for some books first — recommendations are built from your collected dataset.", key="rec")
        return
    ss.rec_pick = ss.selected_id if ss.selected_id in ss.pool else opts[-1]
    st.selectbox("Recommend books similar to", opts, key="rec_pick", format_func=pick_label,
                 on_change=set_selected_from_pick)
    base = get_book(ss.rec_pick)
    if not base:
        return
    st.markdown(f'<div class="glass"><b>{e(base["title"])}</b> — {e(base["author"])}</div>', unsafe_allow_html=True)
    if st.button("🌐 Fetch more candidates from the APIs", key="rec_fetch"):
        with st.spinner("Collecting more books by this author and subject…"):
            n = fetch_more_candidates(base)
        st.success(f"{n} more records added to your dataset.") if n else st.info("No additional records were found.")
    t1, t2 = st.tabs(["✨ Smart recommendations (TF-IDF)", "🔗 Related books"])
    with t1:
        pool = list(ss.pool.values())[-3000:]
        if base["id"] not in {p["id"] for p in pool}:
            pool.append(base)
        scores = tfidf_scores(tuple(p["id"] for p in pool), tuple(book_text(p) for p in pool), base["id"])
        scores = [(i, s) for i, s in scores if get_book(i) and title_key(get_book(i)) != title_key(base)][:8]
        if not scores:
            st.info("Not enough similar books yet. Use the fetch button above or search more books.")
        else:
            st.caption("Similarity uses title, author, category and description. Missing text is handled safely.")
            for k, (i, s) in enumerate(scores, 1):
                ranked_row(get_book(i), k, "rec_s", f'<span class="bl-chip">similarity {s * 100:.0f}%</span>')
    with t2:
        rel = related_books(base)
        if not rel:
            st.info("No related books in your dataset yet. Use the fetch button above.")
        else:
            st.caption("Ranked by same author (+3), same category (+2) and shared title keywords (up to +3).")
            render_grid(rel, "rec_r")


# =====================================================================
# 18. READING LIST
# =====================================================================
def add_reading_from_list():
    ss = st.session_state
    if ss.get("rl_add_pick"):
        set_reading(ss.rl_add_pick, ss.rl_add_status)
        st.toast("Added to reading list")


def change_status(bid):
    set_reading(bid, st.session_state[f"rl_status_{bid}"])


def render_reading_list():
    ss = st.session_state
    section_header("Reading List", "Track your books. Stored in SQLite.")
    opts = [None] + book_options()
    with st.expander("➕ Add a book to your reading list", expanded=not ss.reading):
        c1, c2, c3 = st.columns([3, 1.5, 1])
        c1.selectbox("Book", opts, key="rl_add_pick", format_func=lambda x: "— choose —" if x is None else pick_label(x))
        c2.selectbox("Status", STATUSES, key="rl_add_status")
        c3.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
        c3.button("Add", key="rl_add_btn", on_click=add_reading_from_list)
    ids = [i for i in ss.reading if get_book(i)]
    counts = {s: sum(1 for i in ids if ss.reading[i] == s) for s in STATUSES}
    m = st.columns(3)
    for col, s in zip(m, STATUSES):
        col.markdown(f'<div class="kpi"><div class="kpi-v">{counts[s]}</div><div class="kpi-l">{s}</div></div>',
                     unsafe_allow_html=True)
    st.radio("Show", ["All"] + STATUSES, key="rl_filter", horizontal=True)
    if ss.rl_filter != "All":
        ids = [i for i in ids if ss.reading[i] == ss.rl_filter]
    if not ids:
        st.info("Nothing here yet. Add books above or from any Book Details page.")
        return
    for i in ids:
        b = get_book(i)
        c0, c1, c2, c3 = st.columns([1, 4, 2, 1.6])
        c0.markdown(cover_html(b, "sm"), unsafe_allow_html=True)
        c1.markdown(f'<div class="bl-title" style="min-height:0">{e(b["title"])}</div>'
                    f'<div class="bl-author">by {e(b["author"])}</div>{rating_html(b)}', unsafe_allow_html=True)
        ss[f"rl_status_{i}"] = ss.reading[i]
        c2.selectbox("Status", STATUSES, key=f"rl_status_{i}", on_change=change_status, args=(i,))
        c3.button("Details", key=f"rl_view_{i}", on_click=open_book, args=(i,))
        c3.button("Remove", key=f"rl_rm_{i}", on_click=remove_reading, args=(i,))
        st.markdown("<hr style='border-color:rgba(196,181,253,.12);margin:.3rem 0'>", unsafe_allow_html=True)


# =====================================================================
# 19. TOP RATED AND TRENDING
# =====================================================================
def render_top_rated():
    ss = st.session_state
    section_header("Top Rated Books", "The 10 highest-rated books in your collected dataset (books without ratings are ignored).")
    st.number_input("Minimum number of ratings", min_value=0, step=1, key="tr_min")
    rated = [b for b in ss.pool.values() if b.get("rating") and (b.get("ratings_count") or 0) >= int(ss.tr_min)]
    if not rated:
        empty_state("No rated books in your dataset yet. Search for books to collect ratings.", key="tr")
        return
    rated.sort(key=lambda b: (b["rating"], b.get("ratings_count") or 0), reverse=True)
    for k, b in enumerate(rated[:10], 1):
        ranked_row(b, k, "tr", f'<span class="bl-chip">{fmt_int(b.get("ratings_count"))} ratings</span>')
    st.caption("Ties are broken by the number of ratings. Raise the minimum to avoid books with only a few votes.")


def trend_score(b):
    return (b["rating"] or 0) * math.log10(1 + (b.get("ratings_count") or 0))


def render_trending():
    ss = st.session_state
    section_header("Trending Books", "Popularity ranking from rating data in your dataset.")
    st.markdown('<div class="bl-note"><b>How this ranking works:</b> score = average rating × log10(1 + number of ratings). '
                'It rewards books that are both well rated and widely rated. This is <b>not</b> live trending data — '
                'neither API provides real-time trends — it reflects the rating information returned for the books '
                'you have collected.</div>', unsafe_allow_html=True)
    cand = [b for b in ss.pool.values() if b.get("rating") and (b.get("ratings_count") or 0) > 0]
    if not cand:
        empty_state("No books with rating counts yet. Search for books to build the ranking.", key="tn")
        return
    cand.sort(key=trend_score, reverse=True)
    for k, b in enumerate(cand[:10], 1):
        ranked_row(b, k, "tn", f'<span class="bl-chip">score {trend_score(b):.2f}</span>'
                               f'<span class="bl-chip">{fmt_int(b["ratings_count"])} ratings</span>')


# =====================================================================
# 20. SENTIMENT ANALYSIS
# =====================================================================
@st.cache_resource
def get_vader():
    return SentimentIntensityAnalyzer()


def sentiment_score(text):
    if SENTIMENT_ENGINE == "VADER":
        return float(get_vader().polarity_scores(text)["compound"])
    if SENTIMENT_ENGINE == "TextBlob":
        return float(TextBlob(text).sentiment.polarity)
    return None


def sentiment_label(s):
    return "Positive" if s >= 0.05 else "Negative" if s <= -0.05 else "Neutral"


SENT_COLORS = {"Positive": "#34d399", "Neutral": "#a78bfa", "Negative": "#f87171"}


def sentiment_chart(labels, title, xlabel="Sentiment", ylabel="Count"):
    counts = [labels.count(k) for k in SENT_COLORS]
    fig, ax = new_fig(6, 3.2)
    ax.bar(list(SENT_COLORS), counts, color=list(SENT_COLORS.values()))
    for i, c in enumerate(counts):
        ax.text(i, c, f"{c}", ha="center", va="bottom", color=FG)
    finish(fig, ax, title, xlabel, ylabel)
    show_fig(fig)


def submit_review():
    ss = st.session_state
    text = (ss.get("rev_text") or "").strip()
    if not text:
        st.toast("Write a review first")
        return
    s = sentiment_score(text)
    if s is None:
        return
    pick = ss.get("rev_book")
    ss.user_reviews.append({"Book": get_book(pick)["title"] if pick and get_book(pick) else "(no book selected)",
                            "Review": text, "Score": round(s, 3), "Sentiment": sentiment_label(s),
                            "Submitted": datetime.now().strftime("%Y-%m-%d %H:%M")})
    ss.rev_text = ""


def render_sentiment():
    ss = st.session_state
    section_header("Sentiment Analysis", f"Powered by {SENTIMENT_ENGINE or 'no engine installed'}. "
                   "Scores range from −1 (very negative) to +1 (very positive).")
    if SENTIMENT_ENGINE is None:
        st.error("Install vaderSentiment (or textblob) to use sentiment analysis: pip install vaderSentiment")
        return
    t1, t2, t3 = st.tabs(["📖 Book descriptions", "✍️ Your own reviews", "📊 Dataset overview"])
    with t1:
        st.markdown('<div class="bl-note">Descriptions are written by publishers or catalogues. Their sentiment '
                    'describes the <b>wording of the blurb</b>, not what readers think.</div>', unsafe_allow_html=True)
        opts = [i for i in book_options([ss.selected_id]) if get_book(i).get("description")]
        if not opts:
            st.info("No book descriptions are available yet. Search for books or open a Book Details page.")
        else:
            ss.sent_pick = ss.selected_id if ss.selected_id in opts else opts[-1]
            pid = st.selectbox("Book", opts, key="sent_pick", format_func=pick_label)
            b = get_book(pid)
            s = sentiment_score(b["description"])
            lab = sentiment_label(s)
            st.markdown(f'<div class="glass"><div class="bl-desc">{e(b["description"])}</div></div>', unsafe_allow_html=True)
            k = st.columns(2)
            k[0].markdown(f'<div class="kpi"><div class="kpi-v">{s:+.3f}</div><div class="kpi-l">Description sentiment score</div></div>', unsafe_allow_html=True)
            k[1].markdown(f'<div class="kpi"><div class="kpi-v" style="color:{SENT_COLORS[lab]}">{lab}</div><div class="kpi-l">Description sentiment category</div></div>', unsafe_allow_html=True)
            sents = [x for x in re.split(r"(?<=[.!?])\s+", b["description"]) if len(x.split()) >= 3]
            if sents:
                sentiment_chart([sentiment_label(sentiment_score(x)) for x in sents],
                                "Sentence-level sentiment of this description", "Sentiment", "Number of sentences")
    with t2:
        st.markdown('<div class="bl-note">Reviews you type here are <b>user-submitted</b> and are kept separate from '
                    'book descriptions. They live in this session only.</div>', unsafe_allow_html=True)
        st.selectbox("Book this review is about (optional)", [None] + book_options(), key="rev_book",
                     format_func=lambda x: "— none —" if x is None else pick_label(x))
        st.text_area("Your review", key="rev_text", height=120, placeholder="Write what you thought about the book…")
        st.button("Analyze review", key="rev_btn", type="primary", on_click=submit_review)
        if ss.user_reviews:
            df = pd.DataFrame(ss.user_reviews)
            st.dataframe(df, hide_index=True)
            sentiment_chart(list(df["Sentiment"]), "Sentiment of your submitted reviews", "Sentiment", "Number of reviews")
            st.button("Clear my reviews", key="rev_clear", on_click=lambda: st.session_state.update(user_reviews=[]))
        else:
            st.info("No reviews analyzed yet.")
    with t3:
        st.markdown('<div class="bl-note">Distribution of <b>description</b> sentiment across your collected books. '
                    'This does not represent reader opinion.</div>', unsafe_allow_html=True)
        descs = [b["description"] for b in ss.pool.values() if b.get("description")][:600]
        if not descs:
            st.info("No descriptions collected yet.")
        else:
            labels = [sentiment_label(sentiment_score(d)) for d in descs]
            sentiment_chart(labels, f"Description sentiment across {len(descs)} books", "Sentiment", "Number of books")


# =====================================================================
# 21. ANALYTICS
# =====================================================================
BG, FG, ACC = "#1b1038", "#e9ddff", "#8b5cf6"
PALETTE = ["#8b5cf6", "#a78bfa", "#c4b5fd", "#7c3aed", "#d8b4fe", "#e879f9", "#6366f1", "#818cf8", "#f0abfc", "#6d28d9"]


def new_fig(w=7, h=3.8):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    return fig, ax


def finish(fig, ax, title, xlabel="", ylabel=""):
    ax.set_title(title, color="#fff", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel, color=FG)
    ax.set_ylabel(ylabel, color=FG)
    ax.tick_params(colors=FG, labelsize=8)
    for sp in ax.spines.values():
        sp.set_color("#4c3a8a")
    ax.grid(alpha=.15, color="#c4b5fd")
    ax.set_axisbelow(True)
    leg = ax.get_legend()
    if leg:
        leg.get_frame().set_facecolor(BG)
        leg.get_frame().set_edgecolor("#4c3a8a")
        for t in leg.get_texts():
            t.set_color(FG)
        if leg.get_title():
            leg.get_title().set_color(FG)
    fig.tight_layout()


def show_fig(fig):
    st.pyplot(fig)
    plt.close(fig)


def short(t, n=32):
    t = str(t)
    return t if len(t) <= n else t[:n - 1] + "…"


def pool_df():
    cols = ["id", "title", "author", "authors", "category", "year", "rating", "ratings_count", "price",
            "currency", "price_type", "language", "publisher", "pages", "source"]
    rows = [{c: b.get(c) for c in cols} for b in st.session_state.pool.values()]
    df = pd.DataFrame(rows, columns=cols)
    for c in ("year", "rating", "ratings_count", "price", "pages"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def barh(labels, values, title, xlabel, ylabel):
    fig, ax = new_fig(7, max(3.0, 0.42 * len(labels) + 1.3))
    labels, values = list(labels)[::-1], list(values)[::-1]
    bars = ax.barh([short(l) for l in labels], values, color=ACC)
    for r, v in zip(bars, values):
        ax.text(r.get_width(), r.get_y() + r.get_height() / 2, f" {v:g}", va="center", color=FG, fontsize=8)
    finish(fig, ax, title, xlabel, ylabel)
    show_fig(fig)


def chart_category(df, n=10):
    c = df[~df["category"].isin(["Uncategorized", None])]["category"].value_counts().head(n)
    if c.empty:
        st.info("No category data yet.")
        return
    barh(c.index, c.values, f"Top {len(c)} categories", "Number of books", "Category")


def chart_rating_hist(df):
    r = df["rating"].dropna()
    if r.empty:
        st.info("No ratings yet.")
        return
    fig, ax = new_fig(6.5, 3.6)
    sns.histplot(x=r, bins=np.linspace(0, 5, 11), color=ACC, edgecolor="#1b1038", ax=ax)
    finish(fig, ax, "Rating distribution", "Average rating (stars)", "Number of books")
    show_fig(fig)


def chart_price_hist(df):
    inr = df[(df["currency"] == "INR") & df["price"].notna()]
    if inr.empty:
        st.info("No INR prices yet.")
        return
    fig, ax = new_fig(6.5, 3.6)
    pal = {"Actual": "#34d399", "Estimated": "#a78bfa"}
    present = {k: v for k, v in pal.items() if k in set(inr["price_type"])}
    sns.histplot(data=inr, x="price", hue="price_type", palette=present, bins=20, multiple="layer", alpha=.65, ax=ax)
    finish(fig, ax, "Price distribution (INR only)", "Price (₹)", "Number of books")
    show_fig(fig)


def chart_actual_vs_est(df):
    if df.empty:
        st.info("No data yet.")
        return
    counts = df["price_type"].value_counts()
    inr = df[(df["currency"] == "INR") & df["price"].notna()].groupby("price_type")["price"].mean()
    f, (a1, a2) = plt.subplots(1, 2, figsize=(8, 3.4))
    f.patch.set_facecolor(BG)
    for a in (a1, a2):
        a.set_facecolor(BG)
    cols = {"Actual": "#34d399", "Estimated": "#a78bfa"}
    a1.bar(counts.index, counts.values, color=[cols.get(k, ACC) for k in counts.index])
    for i, v in enumerate(counts.values):
        a1.text(i, v, f"{v}", ha="center", va="bottom", color=FG, fontsize=8)
    a1.tick_params(colors=FG, labelsize=8)
    a1.set_title("Books by price type", color="#fff", fontsize=10)
    a1.set_ylabel("Number of books", color=FG)
    if not inr.empty:
        a2.bar(inr.index, inr.values, color=[cols.get(k, ACC) for k in inr.index])
        for i, v in enumerate(inr.values):
            a2.text(i, v, f"₹{v:,.0f}", ha="center", va="bottom", color=FG, fontsize=8)
    a2.tick_params(colors=FG, labelsize=8)
    a2.set_title("Average price in INR", color="#fff", fontsize=10)
    a2.set_ylabel("Average price (₹)", color=FG)
    for a in (a1, a2):
        a.grid(alpha=.15, color="#c4b5fd")
        for sp in a.spines.values():
            sp.set_color("#4c3a8a")
    f.tight_layout()
    show_fig(f)


def chart_authors(df, n=10):
    ex = df.explode("authors")
    ex = ex[ex["authors"].notna() & (ex["authors"] != "")]
    c = ex["authors"].value_counts().head(n)
    if c.empty:
        st.info("No author data yet.")
        return
    barh(c.index, c.values, f"Most frequent authors (top {len(c)})", "Number of books", "Author")


def chart_years(df):
    y = df["year"].dropna()
    y = y[(y >= 1800) & (y <= datetime.now().year + 1)].astype(int)
    if y.empty:
        st.info("No publication year data yet.")
        return
    counts = y.value_counts().sort_index()
    fig, ax = new_fig(7, 3.6)
    ax.plot(counts.index, counts.values, color="#c4b5fd", marker="o", ms=3, lw=1.5)
    ax.fill_between(counts.index, counts.values, color=ACC, alpha=.35)
    finish(fig, ax, "Books published per year (trend)", "Publication year", "Number of books")
    show_fig(fig)


def chart_decades(df):
    y = df["year"].dropna()
    y = y[(y >= 1800) & (y <= datetime.now().year + 1)].astype(int)
    if y.empty:
        return
    dec = (y // 10 * 10).value_counts().sort_index()
    fig, ax = new_fig(7, 3.4)
    ax.bar([f"{d}s" for d in dec.index], dec.values, color=ACC)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    finish(fig, ax, "Books published per decade", "Decade", "Number of books")
    show_fig(fig)


def chart_top_books(df, by="rating", n=10):
    d = df.dropna(subset=["rating"]) if by == "rating" else df.dropna(subset=["ratings_count"])
    if by == "rating":
        d = d.sort_values(["rating", "ratings_count"], ascending=False).head(n)
        vals, title, xl = d["rating"].round(2), f"Top {len(d)} rated books", "Average rating"
    else:
        d = d[d["ratings_count"] > 0].sort_values("ratings_count", ascending=False).head(n)
        vals, title, xl = d["ratings_count"].astype(int), f"Top {len(d)} most popular books (by rating count)", "Number of ratings"
    if d.empty:
        st.info("No rating data yet.")
        return
    barh(d["title"], vals, title, xl, "Book")


def kpi(label, value, sub=""):
    return (f'<div class="kpi"><div class="kpi-v">{e(value)}</div><div class="kpi-l">{e(label)}</div>'
            f'<div class="kpi-s">{e(sub)}</div></div>')


def render_analytics():
    section_header("Book Analytics", "Statistics and charts for every book collected so far.")
    df = pool_df()
    if df.empty:
        empty_state("No books collected yet. Run a search to start collecting data.", key="an")
        return
    st.caption(f"Dataset: {len(df):,} unique books (from searches, saved records and CSV uploads).")
    tabs = st.tabs(["Category", "Price", "Rating", "Author", "Publication year", "Top 10"])
    with tabs[0]:
        counts = df[df["category"] != "Uncategorized"]["category"].value_counts()
        c1, c2 = st.columns([2, 3])
        c1.dataframe(counts.rename_axis("Category").reset_index(name="Books").head(25), hide_index=True)
        with c2:
            chart_category(df, 12)
    with tabs[1]:
        inr = df[(df["currency"] == "INR") & df["price"].notna()]
        k = st.columns(3)
        k[0].markdown(kpi("Minimum price (INR)", f"₹{inr['price'].min():,.0f}" if len(inr) else "-"), unsafe_allow_html=True)
        k[1].markdown(kpi("Maximum price (INR)", f"₹{inr['price'].max():,.0f}" if len(inr) else "-"), unsafe_allow_html=True)
        k[2].markdown(kpi("Average price (INR)", f"₹{inr['price'].mean():,.0f}" if len(inr) else "-"), unsafe_allow_html=True)
        act = df[(df["price_type"] == "Actual") & df["price"].notna()]
        if len(act):
            g = act.groupby("currency")["price"].agg(["count", "min", "max", "mean"]).round(2).reset_index()
            g.columns = ["Currency", "Books", "Min", "Max", "Average"]
            st.markdown("**Actual prices by currency** (currencies are never mixed in one average)")
            st.dataframe(g, hide_index=True)
        c1, c2 = st.columns(2)
        with c1:
            chart_price_hist(df)
        with c2:
            chart_actual_vs_est(df)
        st.caption("Estimated prices are INR guesses based on page count; they are shown separately from actual store prices.")
    with tabs[2]:
        r = df["rating"].dropna()
        k = st.columns(3)
        k[0].markdown(kpi("Average rating", f"{r.mean():.2f}" if len(r) else "-"), unsafe_allow_html=True)
        k[1].markdown(kpi("Rated books", f"{len(r):,}"), unsafe_allow_html=True)
        k[2].markdown(kpi("Highest rating", f"{r.max():.1f}" if len(r) else "-"), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            chart_rating_hist(df)
        with c2:
            chart_top_books(df, "rating")
    with tabs[3]:
        ex = df.explode("authors")
        ex = ex[ex["authors"].notna() & (ex["authors"] != "")]
        c1, c2 = st.columns([2, 3])
        c1.dataframe(ex["authors"].value_counts().rename_axis("Author").reset_index(name="Books").head(25), hide_index=True)
        with c2:
            chart_authors(df, 12)
    with tabs[4]:
        c1, c2 = st.columns(2)
        with c1:
            chart_years(df)
        with c2:
            chart_decades(df)
    with tabs[5]:
        c1, c2 = st.columns(2)
        with c1:
            chart_top_books(df, "rating")
        with c2:
            chart_top_books(df, "popular")
    st.markdown("---")
    with st.expander("📁 Import / export data"):
        data_tools("analytics")


# =====================================================================
# 22. CSV / EXCEL SUPPORT
# =====================================================================
CSV_ALIASES = {
    "title": ["title", "book title", "name"], "authors": ["author", "authors", "author name"],
    "isbn": ["isbn", "isbn13", "isbn 13", "isbn10"], "category": ["category", "categories", "genre", "subject"],
    "description": ["description", "summary", "blurb"],
    "year": ["year", "publication year", "published", "published year", "first publish year"],
    "publisher": ["publisher"], "language": ["language"],
    "pages": ["pages", "page count", "pagecount", "num pages"],
    "rating": ["rating", "average rating", "avg rating"],
    "ratings_count": ["ratings count", "number of ratings", "num ratings", "rating count", "ratingscount"],
    "cover_url": ["cover", "cover url", "image", "image url", "thumbnail"], "price": ["price"],
    "currency": ["currency", "price currency", "currency code"],
    "details_url": ["details url", "url", "link"], "purchase_url": ["purchase url", "buy url", "buy link"],
}


def norm_col(c):
    return re.sub(r"[\s_\-]+", " ", str(c).strip().lower())


def parse_csv(file):
    """Return (books, report dict). Never raises on bad input."""
    rep = {"errors": [], "rows": 0, "imported": 0, "skipped": 0, "unknown": [], "missing": []}
    try:
        df = pd.read_csv(file)
    except UnicodeDecodeError:
        file.seek(0)
        try:
            df = pd.read_csv(file, encoding="latin-1")
        except Exception as exc:
            rep["errors"].append(f"Could not read the file: {exc}")
            return [], rep
    except Exception as exc:
        rep["errors"].append(f"Could not read the file: {exc}")
        return [], rep
    rep["rows"] = len(df)
    cmap = {norm_col(c): c for c in df.columns}
    col = {}
    for field, aliases in CSV_ALIASES.items():
        for a in aliases:
            if a in cmap:
                col[field] = cmap[a]
                break
    known = set(col.values())
    rep["unknown"] = [str(c) for c in df.columns if c not in known]
    rep["missing"] = [f for f in CSV_ALIASES if f not in col]
    if "title" not in col:
        rep["errors"].append("The CSV must contain a 'title' column (accepted names: title, book title, name).")
        return [], rep

    def val(row, f):
        if f not in col:
            return None
        v = row.get(col[f])
        return None if (v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() == "") else v

    books = []
    for row in df.to_dict("records"):
        title = clean_text(val(row, "title"))
        if not title:
            rep["skipped"] += 1
            continue
        a = val(row, "authors")
        authors = [clean_text(x) for x in re.split(r"\s*[;|]\s*", str(a)) if x.strip()] if a else []
        isbn = clean_isbn(val(row, "isbn"))
        price, cur = to_float(val(row, "price")), val(row, "currency")
        b = blank_book()
        b.update({
            "id": "csv:" + hashlib.md5(f"{title}|{authors}|{isbn}".encode("utf-8")).hexdigest()[:12],
            "title": title, "authors": authors, "isbn": isbn if len(isbn) in (10, 13) else "",
            "isbns": [isbn] if len(isbn) in (10, 13) else [],
            "category": clean_text(val(row, "category")) or "Uncategorized",
            "description": clean_text(val(row, "description")), "year": year_from(val(row, "year")),
            "publisher": clean_text(val(row, "publisher")), "language": clean_text(val(row, "language")) or None,
            "pages": to_int(val(row, "pages")) or None,
            "rating": (lambda r: r if r and 0 < r <= 5 else None)(to_float(val(row, "rating"))),
            "ratings_count": to_int(val(row, "ratings_count")), "cover_url": safe_url(val(row, "cover_url")),
            "details_url": safe_url(val(row, "details_url")), "purchase_url": safe_url(val(row, "purchase_url")),
            "price": price if price is not None and price >= 0 else None,
            "currency": (str(cur).strip().upper() if cur else "INR") if price is not None else None,
            "price_type": "Actual" if price is not None and price >= 0 else None, "source": "CSV Upload",
        })
        books.append(b)
    rep["imported"] = len(books)
    return books, rep


def export_df():
    rows = []
    for b in st.session_state.pool.values():
        rows.append({
            "Book ID": b["id"], "Title": b["title"], "Author": b["author"], "ISBN": b.get("isbn"),
            "Category": b.get("category"), "Description": b.get("description"),
            "Publication Year": b.get("year"), "Publisher": b.get("publisher"), "Language": b.get("language"),
            "Page Count": b.get("pages"), "Rating": b.get("rating"), "Number of Ratings": b.get("ratings_count"),
            "Cover Image": b.get("cover_url"), "Book Details URL": b.get("details_url"),
            "Purchase URL": b.get("purchase_url"), "Price": b.get("price"), "Currency": b.get("currency"),
            "Price Type": b.get("price_type"), "API Source": b.get("source")})
    df = pd.DataFrame(rows)
    ctrl = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].map(lambda x: ctrl.sub("", x) if isinstance(x, str) else x)
    return df


def data_tools(ctx):
    ss = st.session_state
    up = st.file_uploader("Upload a CSV of books", type=["csv"], key=f"upl_{ctx}")
    st.caption("Required column: title. Optional: author, isbn, category, description, year, publisher, language, "
               "pages, rating, ratings_count, cover_url, price, currency, details_url, purchase_url.")
    if up is not None:
        books, rep = parse_csv(up)
        for err in rep["errors"]:
            st.error(err)
        if books:
            sig = f"{up.name}:{up.size}"
            if sig not in ss.imported_files:
                targets = [register_book(b) for b in books]
                db_save_books(targets)
                ss.imported_files.add(sig)
                st.success(f"Imported {rep['imported']} of {rep['rows']} rows into your dataset.")
            else:
                st.info(f"{rep['imported']} rows from this file are already in your dataset.")
            if rep["skipped"]:
                st.warning(f"{rep['skipped']} row(s) were skipped because the title was missing.")
            if rep["unknown"]:
                st.caption("Ignored unrecognised columns: " + ", ".join(rep["unknown"]))
            prev = pd.DataFrame([{"Title": b["title"], "Author": ", ".join(b["authors"]) or "Unknown",
                                  "Category": b["category"], "Year": b["year"], "Rating": b["rating"],
                                  "Price": b["price"]} for b in books[:300]])
            st.markdown("**Uploaded records (first 300)**")
            st.dataframe(prev, hide_index=True)
    if not ss.pool:
        st.info("Nothing to download yet — collect some books first.")
        return
    df = export_df()
    d1, d2 = st.columns(2)
    d1.download_button("⬇ Download CSV", df.to_csv(index=False).encode("utf-8-sig"), "booklens_books.csv",
                       "text/csv", key=f"dlcsv_{ctx}")
    try:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            df.to_excel(xw, index=False, sheet_name="Books")
        d2.download_button("⬇ Download Excel", buf.getvalue(), "booklens_books.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dlxlsx_{ctx}")
    except Exception as exc:
        d2.error(f"Excel export unavailable: {exc}. Install openpyxl.")


# =====================================================================
# 23. DASHBOARD
# =====================================================================
def clear_cache_records():
    db_clear_unused_cache()
    st.toast("Cached records cleared (wishlist, reading list and viewed books kept)")


def render_dashboard():
    ss = st.session_state
    st.markdown('<div class="hero" style="padding:1.4rem 1.8rem"><h1 style="font-size:2.2rem">📊 Dashboard</h1>'
                '<p>Live overview of every book collected by BookLens.</p></div>', unsafe_allow_html=True)
    df = pool_df()
    if df.empty:
        st.markdown('<div class="glass">Your dataset is empty. Search for books on the Home page to fill this dashboard.</div>',
                    unsafe_allow_html=True)
        st.button("Go to Home", key="dash_home", on_click=lambda: st.session_state.update(page_nav="🏠 Home"))
        with st.expander("📁 Import a CSV"):
            data_tools("dash_empty")
        return
    ex = df.explode("authors")
    n_auth = ex["authors"].replace("", np.nan).dropna().nunique()
    n_cat = df[df["category"] != "Uncategorized"]["category"].nunique()
    inr = df[(df["currency"] == "INR") & df["price"].notna()]
    row1 = st.columns(4)
    row1[0].markdown(kpi("Total Books", f"{len(df):,}", "unique records"), unsafe_allow_html=True)
    row1[1].markdown(kpi("Total Authors", f"{n_auth:,}"), unsafe_allow_html=True)
    row1[2].markdown(kpi("Total Categories", f"{n_cat:,}"), unsafe_allow_html=True)
    row1[3].markdown(kpi("Average Rating", f"{df['rating'].mean():.2f}" if df["rating"].notna().any() else "-",
                         f"{int(df['rating'].notna().sum())} rated books"), unsafe_allow_html=True)
    row2 = st.columns(3)
    row2[0].markdown(kpi("Average Price", f"₹{inr['price'].mean():,.0f}" if len(inr) else "-",
                         "INR prices only (actual + estimated)"), unsafe_allow_html=True)
    row2[1].markdown(kpi("Actual Price Count", f"{int((df['price_type'] == 'Actual').sum()):,}"), unsafe_allow_html=True)
    row2[2].markdown(kpi("Estimated Price Count", f"{int((df['price_type'] == 'Estimated').sum()):,}"), unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        chart_category(df)
    with b:
        chart_rating_hist(df)
    a, b = st.columns(2)
    with a:
        chart_price_hist(df)
    with b:
        chart_years(df)
    a, b = st.columns(2)
    with a:
        chart_authors(df)
    with b:
        chart_top_books(df, "rating")
    chart_actual_vs_est(df)
    with st.expander("📁 Import / export data"):
        data_tools("dash")
        st.button("Clear cached book records", key="dash_clear", on_click=clear_cache_records)


# =====================================================================
# HOME (WELCOME) PAGE
# =====================================================================
def request_random():
    st.session_state.random_request = True


def render_welcome():
    ss = st.session_state
    st.markdown(f'<div class="hero"><h1>{APP_NAME}</h1><p>{TAGLINE}</p>'
                '<p style="font-size:.95rem;color:#c4b5fd">Search Google Books and Open Library worldwide, '
                'compare books, track your reading and explore the data behind them.</p></div>', unsafe_allow_html=True)
    c1, c2 = st.columns([5, 1.2])
    c1.text_input("Quick search", key="home_q", placeholder="Search any title, author, ISBN or topic…", label_visibility="collapsed")
    c2.button("🔍 Search", key="home_search", type="primary", on_click=home_search)
    cols = st.columns(len(SUGGESTED_SEARCHES))
    for i, (col, s) in enumerate(zip(cols, SUGGESTED_SEARCHES)):
        col.button(s[0], key=f"hs_{i}", on_click=quick_search, args=s)
    k = st.columns(4)
    k[0].markdown(kpi("Books in dataset", f"{len(ss.pool):,}"), unsafe_allow_html=True)
    k[1].markdown(kpi("Wishlist", f"{len(ss.wish_ids)}"), unsafe_allow_html=True)
    k[2].markdown(kpi("Reading list", f"{len(ss.reading)}"), unsafe_allow_html=True)
    k[3].markdown(kpi("Recently viewed", f"{len(db_recent_ids(200))}"), unsafe_allow_html=True)
    st.markdown('<div class="bl-h2" style="margin-top:.6rem">Everything in BookLens</div>', unsafe_allow_html=True)
    names = SECTION_NAMES[1:]
    for start in range(0, len(names), 3):
        cols = st.columns(3)
        for col, name in zip(cols, names[start:start + 3]):
            s = SECTION_INFO[name]
            with col:
                st.markdown(f'<div class="glass" style="min-height:105px;margin-bottom:.4rem"><div class="bl-title" '
                            f'style="margin-top:0;min-height:0">{s[2]} {e(s[0])}</div>'
                            f'<div class="bl-author" style="white-space:normal">{e(s[3])}</div></div>',
                            unsafe_allow_html=True)
                st.button("Open", key=f"homecard_{name}", on_click=go, args=(name,))
    st.markdown('<div class="bl-h2" style="margin-top:1rem">🎲 Random book suggestion</div>', unsafe_allow_html=True)
    st.button("Surprise me with a book", key="rand_btn", on_click=request_random)
    if ss.random_request:
        ss.random_request = False
        if not ss.pool:
            with st.spinner("Finding a book for you…"):
                data = fetch_page({"type": "Subject / Category", "q": random.choice(RANDOM_TOPICS), "author": "",
                                   "category": "Any", "lang": "Any", "country": "Any"}, 1)
                targets = [register_book(b) for b in data["books"]]
                db_save_books(targets)
            if not targets:
                st.warning("Could not reach the book services right now. Please try again in a moment.")
        if ss.pool:
            ss.random_id = random.choice(list(ss.pool.keys()))
    if ss.random_id and get_book(ss.random_id):
        _, mid, _ = st.columns([1, 1.2, 1])
        with mid:
            book_card(get_book(ss.random_id), "rand")
    with st.expander("📁 Import a CSV or download your collected data"):
        data_tools("home")
    st.caption("Data sources: Google Books API and Open Library API. Covers: Open Library Covers API with Google Books "
               "thumbnails as fallback. Estimated prices are always labelled and are never store prices.")


# =====================================================================
# 24. MAIN APPLICATION ROUTING
# =====================================================================
RENDERERS = {
    "Home": render_welcome, "Explore Worldwide Books": render_explore, "Book Details": render_details,
    "Wishlist": render_wishlist, "Recently Viewed": render_recent, "Book Comparison": render_comparison,
    "Book Recommendations": render_recommendations, "Reading List": render_reading_list,
    "Top Rated Books": render_top_rated, "Trending Books": render_trending,
    "Book Analytics": render_analytics, "Sentiment Analysis": render_sentiment,
}


def main():
    init_state()
    restore_ui()
    inject_css()
    with st.sidebar:
        st.markdown(f'<div class="bl-brand">📚 {APP_NAME}</div><div class="bl-brand-sub">{TAGLINE}</div>',
                    unsafe_allow_html=True)
        st.radio("Navigation", ["🏠 Home", "📊 Dashboard"], key="page_nav", label_visibility="collapsed")
    if st.session_state.page_nav == "📊 Dashboard":
        render_dashboard()
    else:
        render_nav_bar()
        RENDERERS[st.session_state.section]()
    for msg in st.session_state.pop("db_errors", [])[:1]:
        st.warning(f"Database notice: {msg}")
    persist_ui()
main()
