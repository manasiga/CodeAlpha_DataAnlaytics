import html, io, json, random, re, sqlite3, time
from contextlib import closing
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

st.set_page_config(page_title="BookLens", page_icon="📚", layout="wide")
DB, PER_PAGE = "booklens.db", 20
NUM = ["year", "pages", "rating", "rating_count", "price_value"]
TXT = ["book_id", "title", "author", "isbn", "category", "description", "publisher", "language",
       "cover", "details_url", "buy_url", "currency", "price_type"]
RATE = {"INR": 1, "USD": 83, "EUR": 90, "GBP": 105, "CAD": 61, "AUD": 55}
TOPICS = ["fiction", "fantasy", "science", "history", "biography", "romance", "mystery", "thriller",
          "technology", "programming", "business", "self-help", "psychology", "philosophy", "art",
          "cooking", "travel", "poetry", "health", "education", "economics", "mathematics", "religion",
          "children", "horror", "adventure", "comics", "music", "sports", "nature"]

st.markdown("""<style>
.stApp{background:linear-gradient(135deg,#120a24 0%,#2a1055 55%,#3b1a78 100%);}
section[data-testid=stSidebar]{background:rgba(18,10,36,.92);}
h1,h2,h3,h4{color:#e9deff!important;font-family:'Segoe UI',sans-serif}
.hero{font-size:2.4rem;font-weight:800;background:linear-gradient(90deg,#c4b5fd,#8b5cf6,#f0abfc);
-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sub{color:#cdbdf5;margin-bottom:12px}
.card{background:rgba(255,255,255,.07);backdrop-filter:blur(12px);border:1px solid rgba(190,160,255,.25);
border-radius:18px;padding:12px;margin-bottom:6px;transition:.25s;min-height:395px}
.card:hover{transform:translateY(-6px);box-shadow:0 12px 30px rgba(140,90,255,.45)}
.cover{width:100%;height:210px;object-fit:contain;border-radius:12px;background:rgba(0,0,0,.25)}
.nocover{height:210px;display:flex;align-items:center;justify-content:center;border-radius:12px;
background:rgba(0,0,0,.3);color:#b9a6e8;border:1px dashed #8b7bb8}
.t{font-weight:700;color:#fff;margin-top:8px;line-height:1.25}.m{color:#cdbdf5;font-size:.85rem}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;background:rgba(139,92,246,.35);font-size:.75rem;color:#fff}
.kpi{background:rgba(255,255,255,.08);border:1px solid rgba(190,160,255,.3);border-radius:16px;padding:14px;text-align:center}
.kpi b{font-size:1.5rem;color:#d8c8ff;display:block}.kpi span{color:#b9a6e8;font-size:.8rem}
.stButton>button{background:linear-gradient(90deg,#7c3aed,#a78bfa);color:#fff;border:0;border-radius:12px;transition:.2s}
.stButton>button:hover{transform:scale(1.03);box-shadow:0 6px 18px rgba(139,92,246,.5);color:#fff}
</style>""", unsafe_allow_html=True)

# ---------------- Database ----------------
def db(q, a=(), fetch=False):
    with closing(sqlite3.connect(DB)) as c:
        cur = c.execute(q, a); c.commit()
        return cur.fetchall() if fetch else None

def init_db():
    for t in ("wishlist", "recent", "reading"):
        db(f"CREATE TABLE IF NOT EXISTS {t}(book_id TEXT PRIMARY KEY, data TEXT, status TEXT DEFAULT 'To Read')")

def saved(t):
    return [dict(json.loads(d), status=s) for d, s in db(f"SELECT data,status FROM {t} ORDER BY rowid DESC", fetch=True)]

def in_tbl(t, bid):
    return bool(db(f"SELECT 1 FROM {t} WHERE book_id=?", (bid,), fetch=True))

def save_row(t, b, status="To Read", replace=False):
    op = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
    db(f"{op} INTO {t}(book_id,data,status) VALUES(?,?,?)", (b["book_id"], json.dumps(b, default=str), status))

def del_row(t, bid): db(f"DELETE FROM {t} WHERE book_id=?", (bid,))
def set_status(bid, key): db("UPDATE reading SET status=? WHERE book_id=?", (st.session_state[key], bid))

# ---------------- API collection ----------------
def get_json(url, params):
    for i in range(3):
        try:
            r = requests.get(url, params=params, timeout=12)
            if r.status_code == 200: return r.json()
            if r.status_code in (429, 500, 503): time.sleep(1.5 * (i + 1))
            else: return {}
        except (requests.RequestException, ValueError): time.sleep(1)
    return {}

def yr(s):
    m = re.search(r"\d{4}", str(s or "")); return int(m.group()) if m else np.nan

@st.cache_data(ttl=86400, show_spinner=False)
def google_page(topic, start):
    d = get_json("https://www.googleapis.com/books/v1/volumes",
                 {"q": f"subject:{topic}", "maxResults": 40, "startIndex": start, "printType": "books", "langRestrict": "en"})
    out = []
    for it in d.get("items", []):
        v, s = it.get("volumeInfo", {}), it.get("saleInfo", {})
        ids = {i.get("type"): i.get("identifier") for i in v.get("industryIdentifiers", [])}
        img = v.get("imageLinks") or {}
        cover = (img.get("thumbnail") or img.get("smallThumbnail") or "").replace("http://", "https://").replace("&edge=curl", "")
        rp = s.get("retailPrice") or {}
        sale = s.get("saleability") == "FOR_SALE"
        out.append(dict(book_id="g_" + it["id"], title=v.get("title", ""), author=", ".join(v.get("authors", [])),
            isbn=ids.get("ISBN_13") or ids.get("ISBN_10") or "", category=(v.get("categories") or [topic.title()])[0],
            description=v.get("description", ""), year=yr(v.get("publishedDate")), publisher=v.get("publisher", ""),
            language=v.get("language", ""), pages=v.get("pageCount"), rating=v.get("averageRating"),
            rating_count=v.get("ratingsCount"), cover=cover,
            details_url=v.get("infoLink") or v.get("canonicalVolumeLink", ""),
            buy_url=s.get("buyLink", "") if sale else "", price_value=rp.get("amount") if sale else None,
            currency=rp.get("currencyCode", "") if sale else ""))
    return out

@st.cache_data(ttl=86400, show_spinner=False)
def ol_page(topic, page):
    d = get_json("https://openlibrary.org/search.json",
                 {"q": f"subject:{topic}", "limit": 50, "page": page, "language": "eng",
                  "fields": "key,title,author_name,isbn,cover_i,first_publish_year,publisher,language,number_of_pages_median,ratings_average,ratings_count"})
    out = []
    for w in d.get("docs", []):
        ci = w.get("cover_i")
        out.append(dict(book_id="ol_" + w["key"].split("/")[-1], title=w.get("title", ""),
            author=", ".join(w.get("author_name", [])[:3]), isbn=(w.get("isbn") or [""])[0], category=topic.title(),
            description="", year=w.get("first_publish_year"), publisher=(w.get("publisher") or [""])[0],
            language=(w.get("language") or [""])[0], pages=w.get("number_of_pages_median"),
            rating=w.get("ratings_average"), rating_count=w.get("ratings_count"),
            cover=f"https://covers.openlibrary.org/b/id/{ci}-L.jpg" if ci else "",
            details_url="https://openlibrary.org" + w["key"], buy_url="", price_value=None, currency=""))
    return out

def normalize(df):
    df = df.copy()
    for c in TXT + NUM:
        if c not in df: df[c] = np.nan if c in NUM else ""
    for c in NUM: df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in TXT: df[c] = df[c].fillna("").astype(str).str.strip()
    df["category"] = df["category"].replace("", "Uncategorized")
    df["author"] = df["author"].replace("", "Unknown")
    df = df[df.title != ""].copy()
    miss = df.book_id == ""
    df.loc[miss, "book_id"] = ["u_" + str(i) for i in df.index[miss]]
    df = df.drop_duplicates("book_id").reset_index(drop=True)
    df["year"] = df["year"].where(df.year.between(1000, 2030))
    df["rating"] = df["rating"].where(df.rating.between(0, 5))
    act = df.price_value.notna() & (df.price_value > 0)
    pg = df.pages.fillna(0)
    est = np.round(np.where(pg > 0, 149 + pg.clip(upper=1000) * 1.2, 399) / 10) * 10
    df["price_type"] = np.where(act, "Actual", "Estimated")
    df["price_value"] = np.where(act, df.price_value, est)
    df["currency"] = np.where(act & (df.currency != ""), df.currency, np.where(act, "N/A", "INR"))
    df["price_inr"] = df.price_value * df.currency.map(RATE).fillna(1)
    return df

def collect(target):
    rows, seen = [], set()
    bar = st.progress(0.0, text="Collecting books from Google Books and Open Library...")
    def add(b):
        k = (re.sub(r"\W+", "", b["title"].lower()), re.sub(r"\W+", "", b["author"].lower().split(",")[0]))
        if b["title"] and k not in seen:
            seen.add(k); rows.append(b)
    for i, t in enumerate(TOPICS):
        for fn, arg in ((google_page, 0), (google_page, 40), (ol_page, 1)):
            if len(rows) >= target: break
            for b in fn(t, arg): add(b)
        bar.progress(min(1.0, max((i + 1) / len(TOPICS), len(rows) / target)), text=f"Collected {len(rows)} unique books...")
        if len(rows) >= target: break
    bar.empty()
    return normalize(pd.DataFrame(rows[:target])) if rows else normalize(pd.DataFrame())

# ---------------- Helpers ----------------
def esc(x): return html.escape(str(x))
def rtxt(r): return "N/A" if pd.isna(r) else f"{r:.1f} ⭐"
def ptxt(b): return f"{b['currency']} {b['price_value']:,.2f} ({b['price_type']} Price)"

def card_html(b):
    img = (f'<img class="cover" src="{esc(b["cover"])}" loading="lazy">' if b["cover"]
           else '<div class="nocover">Cover Not Available</div>')
    return (f'<div class="card">{img}<div class="t">{esc(b["title"][:70])}</div>'
            f'<div class="m">by {esc(b["author"][:45])}</div><div style="margin:6px 0"><span class="badge">{esc(b["category"][:28])}</span></div>'
            f'<div class="m">{rtxt(b["rating"])}</div><div class="m">{esc(ptxt(b))}</div></div>')

def open_book(b):
    st.session_state.sel = b; save_row("recent", b, "", replace=True)
def close_book(): st.session_state.sel = None

def cards(df, pre, extra=None):
    recs = df.to_dict("records")
    for i in range(0, len(recs), 4):
        for c, b in zip(st.columns(4), recs[i:i + 4]):
            with c:
                st.markdown(card_html(b), unsafe_allow_html=True)
                st.button("View Details", key=f"{pre}_{b['book_id']}", on_click=open_book, args=(b,), use_container_width=True)
                if extra: extra(b, pre)

def kpi(col, label, val): col.markdown(f'<div class="kpi"><b>{val}</b><span>{label}</span></div>', unsafe_allow_html=True)

def fig_ax(w=6, h=3.4):
    fig, ax = plt.subplots(figsize=(w, h)); fig.patch.set_alpha(0); ax.set_facecolor((1, 1, 1, .05))
    for s in ax.spines.values(): s.set_color("#8b7bb8")
    ax.tick_params(colors="#e6dcff")
    return fig, ax

def done(fig, ax, title, xl="", yl=""):
    ax.set_title(title, color="white", fontweight="bold"); ax.set_xlabel(xl, color="#e6dcff"); ax.set_ylabel(yl, color="#e6dcff")
    fig.tight_layout(); st.pyplot(fig, clear_figure=True, transparent=True)

def c_bar(s, title, xl="Count"):
    if len(s) == 0: return st.info("No data for " + title)
    fig, ax = fig_ax(); s = s.head(12)
    sns.barplot(x=s.values, y=[str(i)[:28] for i in s.index], ax=ax, color="#a78bfa"); done(fig, ax, title, xl)

def c_hist(s, title, xl, bins=20):
    s = s.dropna()
    if len(s) == 0: return st.info("No data for " + title)
    fig, ax = fig_ax(); sns.histplot(s, bins=bins, color="#a78bfa", ax=ax); done(fig, ax, title, xl, "Books")

def c_line(s, title, xl, yl):
    if len(s) == 0: return st.info("No data for " + title)
    fig, ax = fig_ax(); ax.plot(s.index, s.values, marker="o", color="#c4b5fd"); done(fig, ax, title, xl, yl)

# ---------------- Recommendation ----------------
@st.cache_resource(show_spinner=False)
def tfidf_model(texts):
    v = TfidfVectorizer(stop_words="english", max_features=20000)
    return v, v.fit_transform(texts)

def texts_of(df):
    return tuple((df.title + " " + df.title + " " + df.author + " " + df.category + " " + df.description).str.lower())

def recommend(df, idx=None, query=None, n=8):
    v, m = tfidf_model(texts_of(df))
    q = m[idx] if idx is not None else v.transform([query.lower()])
    sims = linear_kernel(q, m).ravel()
    if idx is not None: sims[idx] = -1
    top = [i for i in sims.argsort()[::-1][:n] if sims[i] > 0]
    return df.iloc[top]

def related(df, b, n=6):
    kw = {w for w in re.findall(r"[a-z]{4,}", b["title"].lower())}
    sc = (df.category == b["category"]) * 2 + (df.author == b["author"]) * 3 + \
         df.title.apply(lambda t: len(kw & set(re.findall(r"[a-z]{4,}", t.lower()))))
    sc = sc.where(df.book_id != b["book_id"], -1)
    return df.loc[sc[sc > 0].sort_values(ascending=False).head(n).index]

# ---------------- Details ----------------
def details(df, b):
    st.button("⬅ Back to books", on_click=close_book)
    c1, c2 = st.columns([1, 2])
    with c1:
        if b["cover"]: st.image(b["cover"], use_container_width=True)
        else: st.markdown('<div class="nocover">Cover Not Available</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f"## {b['title']}")
        st.markdown(f"**Author:** {b['author']}  \n**Category:** {b['category']}  \n**Publisher:** {b['publisher'] or 'N/A'}  \n"
                    f"**Publication Year:** {'N/A' if pd.isna(b['year']) else int(b['year'])}  \n**ISBN:** {b['isbn'] or 'N/A'}  \n"
                    f"**Pages:** {'N/A' if pd.isna(b['pages']) else int(b['pages'])}  \n**Language:** {b['language'] or 'N/A'}  \n"
                    f"**Rating:** {rtxt(b['rating'])} ({'N/A' if pd.isna(b['rating_count']) else int(b['rating_count'])} ratings)  \n**Price:** {ptxt(b)}")
        st.write(b["description"] or "_No description available._")
        k1, k2 = st.columns(2)
        if b["details_url"]: k1.link_button("🌐 Open Book Website", b["details_url"], use_container_width=True)
        if b["buy_url"]: k2.link_button("🛒 Buy Book", b["buy_url"], use_container_width=True)
        else: k2.caption("Purchase Link Not Available")
        w1, w2 = st.columns(2)
        if in_tbl("wishlist", b["book_id"]):
            w1.button("💔 Remove from Wishlist", on_click=del_row, args=("wishlist", b["book_id"]), use_container_width=True)
        else:
            w1.button("❤ Add to Wishlist", on_click=save_row, args=("wishlist", b), use_container_width=True)
        stt = w2.selectbox("Reading status", ["To Read", "Currently Reading", "Completed"], key="det_status")
        w2.button("📖 Save to Reading List", on_click=save_row, args=("reading", b, stt, True), use_container_width=True)
    st.markdown("### Related Books"); r = related(df, b)
    cards(r, "rel") if len(r) else st.info("No related books found.")
    st.markdown("### Similar Books (TF-IDF)")
    idx = df.index[df.book_id == b["book_id"]]
    if len(idx):
        r = recommend(df, idx=idx[0], n=4)
        cards(r, "sim") if len(r) else st.info("No similar books found.")

# ---------------- Filters ----------------
def filter_df(df):
    a, b_, c = st.columns([3, 1, 1.5])
    q = a.text_input("🔎 Search", placeholder="Title, author or ISBN").strip().lower()
    mode = b_.selectbox("Search in", ["All", "Title", "Author", "ISBN"])
    cat = c.selectbox("Category", ["All"] + sorted(df.category.unique()))
    d, e, f, g = st.columns(4)
    y0, y1 = int(df.year.min()) if df.year.notna().any() else 1900, int(df.year.max()) if df.year.notna().any() else 2025
    yrs = d.slider("Publication year", y0, y1, (y0, y1)) if y0 < y1 else (y0, y1)
    p0, p1 = float(df.price_inr.min()), float(df.price_inr.max())
    prs = e.slider("Price (INR)", p0, p1, (p0, p1)) if p0 < p1 else (p0, p1)
    mr = f.slider("Minimum rating", 0.0, 5.0, 0.0, 0.5)
    sk = g.selectbox("Sort by", ["Title", "Price", "Rating", "Publication Year"])
    asc = g.checkbox("Ascending", True)
    out = df
    if q:
        cols = {"All": ["title", "author", "isbn"], "Title": ["title"], "Author": ["author"], "ISBN": ["isbn"]}[mode]
        mask = np.zeros(len(out), bool)
        for col in cols: mask |= out[col].str.lower().str.replace("-", "", regex=False).str.contains(q.replace("-", ""), regex=False).values
        out = out[mask]
    if cat != "All": out = out[out.category == cat]
    if (y0, y1) != tuple(yrs): out = out[out.year.between(*yrs)]
    if (p0, p1) != tuple(prs): out = out[out.price_inr.between(*prs)]
    if mr > 0: out = out[out.rating >= mr]
    col = {"Title": "title", "Price": "price_inr", "Rating": "rating", "Publication Year": "year"}[sk]
    key = out[col].str.lower() if col == "title" else out[col]
    out = out.assign(_k=key).sort_values("_k", ascending=asc, na_position="last").drop(columns="_k")
    return out, (q, mode, cat, tuple(yrs), tuple(prs), mr, sk, asc)

# ---------------- Data section ----------------
def data_section(df):
    st.markdown("#### Download collected data")
    d1, d2 = st.columns(2)
    d1.download_button("⬇ Download CSV", df.to_csv(index=False).encode("utf-8"), "booklens_books.csv", "text/csv", use_container_width=True)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w: df.to_excel(w, index=False, sheet_name="Books")
    d2.download_button("⬇ Download Excel", buf.getvalue(), "booklens_books.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    st.markdown("#### Upload CSV")
    up = st.file_uploader("Upload a CSV (needs at least a 'title' column)", type="csv")
    if up:
        try:
            u = pd.read_csv(up); u.columns = [c.strip().lower() for c in u.columns]
            u = u.rename(columns={"authors": "author", "name": "title", "image": "cover", "url": "details_url"})
            if "title" not in u.columns: return st.error("Invalid file: a 'title' column is required.")
            u = normalize(u); st.success(f"Validated {len(u)} valid rows."); st.dataframe(u.head(50), use_container_width=True)
            if st.button("➕ Add uploaded books to library"):
                st.session_state.df = normalize(pd.concat([df, u], ignore_index=True)); st.rerun()
        except Exception as ex:
            st.error(f"Could not read the file: {ex}")

# ---------------- Pages ----------------
def home(df):
    st.markdown('<div class="hero">📚 BookLens</div><div class="sub">Discover Books. Explore Data. Understand Insights.</div>', unsafe_allow_html=True)
    with st.expander("⚙ Data source"):
        n = st.slider("Books to collect (max 2,000)", 100, 2000, 300, 100)
        if st.button("🔄 Collect books from APIs"):
            with st.spinner("Contacting APIs..."): st.session_state.df = collect(n)
            st.rerun()
    st.caption(f"Library contains **{len(df)}** unique books (actual number collected; APIs may return fewer than requested).")
    if df.empty:
        st.warning("No books available. The APIs may be unreachable — try again or upload a CSV below.")
        return data_section(df)
    if st.session_state.get("sel"): return details(df, st.session_state.sel)
    tabs = st.tabs(["Discover", "Top Rated", "Trending", "Random", "Recommend", "Compare", "Wishlist", "Reading List", "Recently Viewed", "Data"])
    with tabs[0]:
        out, sig = filter_df(df)
        if st.session_state.get("sig") != sig: st.session_state.page, st.session_state.sig = 1, sig
        pages = max(1, -(-len(out) // PER_PAGE)); pg = min(st.session_state.get("page", 1), pages)
        st.write(f"**{len(out)}** books match.")
        if len(out): cards(out.iloc[(pg - 1) * PER_PAGE: pg * PER_PAGE], "disc")
        else: st.info("No books match your filters.")
        p1, p2, p3 = st.columns([1, 2, 1])
        if p1.button("⬅ Previous", disabled=pg <= 1): st.session_state.page = pg - 1; st.rerun()
        p2.markdown(f"<div style='text-align:center'>Page <b>{pg}</b> of <b>{pages}</b></div>", unsafe_allow_html=True)
        if p3.button("Next ➡", disabled=pg >= pages): st.session_state.page = pg + 1; st.rerun()
    with tabs[1]:
        st.subheader("Top 10 Rated Books")
        t = df[df.rating.notna()].sort_values(["rating", "rating_count"], ascending=False).head(10)
        cards(t, "top") if len(t) else st.info("No rated books available.")
    with tabs[2]:
        st.subheader("Trending Books")
        st.info("Ranking criteria: rating × log(1 + number of ratings). This uses a static snapshot of API data — it is NOT a live trend.")
        t = df[df.rating.notna()].assign(score=lambda x: x.rating * np.log1p(x.rating_count.fillna(0))).sort_values("score", ascending=False).head(12)
        cards(t, "trend") if len(t) else st.info("No rating data available.")
    with tabs[3]:
        if st.button("🎲 Suggest a random book"): st.session_state.rnd = df.sample(1).iloc[0].to_dict()
        if st.session_state.get("rnd"):
            c, _ = st.columns([1, 3]); 
            with c: cards(pd.DataFrame([st.session_state.rnd]), "rnd")
    with tabs[4]:
        st.subheader("Smart Recommendations")
        q = st.text_input("Describe what you like (title, author, topic)", key="rq")
        lab = (df.title + " — " + df.author).tolist()
        pick = st.selectbox("...or pick a book you enjoyed", ["(none)"] + lab)
        r = None
        if q.strip(): r = recommend(df, query=q)
        elif pick != "(none)": r = recommend(df, idx=lab.index(pick))
        if r is not None: cards(r, "rec") if len(r) else st.info("No similar books found.")
    with tabs[5]:
        lab = (df.title + " — " + df.author).tolist()
        a, b = st.columns(2)
        s1, s2 = a.selectbox("Book 1", lab, key="c1"), b.selectbox("Book 2", lab, index=min(1, len(lab) - 1), key="c2")
        if s1 == s2: st.info("Select two different books.")
        else:
            x, y = df.iloc[lab.index(s1)], df.iloc[lab.index(s2)]
            fields = [("Title", "title"), ("Author", "author"), ("Category", "category"), ("Publisher", "publisher")]
            rows = {l: [x[k] or "N/A", y[k] or "N/A"] for l, k in fields}
            rows["Price"] = [ptxt(x), ptxt(y)]; rows["Rating"] = [rtxt(x.rating), rtxt(y.rating)]
            rows["Publication Year"] = [("N/A" if pd.isna(i.year) else int(i.year)) for i in (x, y)]
            rows["Page Count"] = [("N/A" if pd.isna(i.pages) else int(i.pages)) for i in (x, y)]
            st.table(pd.DataFrame(rows, index=["Book 1", "Book 2"]).T.astype(str))
    with tabs[6]:
        w = saved("wishlist")
        if not w: st.info("Your wishlist is empty.")
        else: cards(pd.DataFrame(w), "wl", lambda b, p: st.button("💔 Remove", key=f"{p}x{b['book_id']}", on_click=del_row, args=("wishlist", b["book_id"]), use_container_width=True))
    with tabs[7]:
        r = saved("reading")
        if not r: st.info("Your reading list is empty. Add books from the details page.")
        else:
            opts = ["To Read", "Currently Reading", "Completed"]
            def extra(b, p):
                k = f"{p}s{b['book_id']}"
                st.selectbox("Status", opts, index=opts.index(b["status"]) if b["status"] in opts else 0, key=k, on_change=set_status, args=(b["book_id"], k))
                st.button("🗑 Remove", key=f"{p}x{b['book_id']}", on_click=del_row, args=("reading", b["book_id"]), use_container_width=True)
            cards(pd.DataFrame(r), "rl", extra)
    with tabs[8]:
        r = saved("recent")[:20]
        cards(pd.DataFrame(r), "rv") if r else st.info("No recently viewed books yet.")
    with tabs[9]: data_section(df)

def dashboard(df):
    st.markdown('<div class="hero">📊 Dashboard</div><div class="sub">Live analytics for the current dataset</div>', unsafe_allow_html=True)
    if df.empty: return st.warning("No data to analyse yet. Collect books on the Home page.")
    cols = st.columns(7)
    for c, (l, v) in zip(cols, [("Total Books", len(df)), ("Authors", df.author.nunique()), ("Categories", df.category.nunique()),
        ("Avg Rating", "N/A" if df.rating.isna().all() else f"{df.rating.mean():.2f}"), ("Avg Price (₹)", f"{df.price_inr.mean():,.0f}"),
        ("Actual Prices", int((df.price_type == 'Actual').sum())), ("Estimated Prices", int((df.price_type == 'Estimated').sum()))]): kpi(c, l, v)
    st.write("")
    tabs = st.tabs(["Overview", "Categories", "Prices", "Ratings", "Authors", "Years", "Top 10", "Sentiment"])
    cat, auth = df.category.value_counts(), df[df.author != "Unknown"].author.value_counts()
    top = df[df.rating.notna()].sort_values(["rating", "rating_count"], ascending=False).head(10)
    with tabs[0]:
        a, b = st.columns(2)
        with a: c_bar(cat, "Books per Category"); c_hist(df.price_inr, "Price Distribution (₹)", "Price in INR")
        with b: c_hist(df.rating, "Rating Distribution", "Rating", 10); c_line(df.year.dropna().astype(int).value_counts().sort_index(), "Publication Year Trend", "Year", "Books")
        a, b = st.columns(2)
        with a: c_bar(auth, "Top Authors")
        with b: c_bar(df.price_type.value_counts(), "Actual vs Estimated Prices")
        if len(top): c_bar(pd.Series(top.rating.values, index=top.title), "Top 10 Books by Rating", "Rating")
    with tabs[1]:
        c_bar(cat, "Most Popular Categories"); st.dataframe(cat.rename("Books"), use_container_width=True)
    with tabs[2]:
        k = st.columns(3); kpi(k[0], "Min (₹)", f"{df.price_inr.min():,.0f}"); kpi(k[1], "Max (₹)", f"{df.price_inr.max():,.0f}"); kpi(k[2], "Average (₹)", f"{df.price_inr.mean():,.0f}")
        a, b = st.columns(2)
        with a: c_hist(df.price_inr, "Price Distribution", "INR")
        with b: c_bar(df.groupby("price_type").price_inr.mean().round(0), "Average Price: Actual vs Estimated (₹)", "INR")
        st.caption("Non-INR actual prices are converted with fixed approximate rates for charts only.")
    with tabs[3]:
        st.metric("Average rating", "N/A" if df.rating.isna().all() else f"{df.rating.mean():.2f}")
        c_hist(df.rating, "Rating Histogram", "Rating", 10)
        st.dataframe(top[["title", "author", "rating", "rating_count"]], use_container_width=True)
    with tabs[4]:
        c_bar(auth, "Books per Author"); st.dataframe(auth.head(20).rename("Books"), use_container_width=True)
    with tabs[5]:
        y = df.year.dropna().astype(int).value_counts().sort_index()
        c_line(y, "Books Published by Year", "Year", "Books"); st.dataframe(y.rename("Books").tail(30), use_container_width=True)
    with tabs[6]:
        st.markdown("**Top rated**"); st.dataframe(top[["title", "author", "rating"]], use_container_width=True)
        pop = df[df.rating_count.notna()].sort_values("rating_count", ascending=False).head(10)
        st.markdown("**Most popular by number of ratings**"); st.dataframe(pop[["title", "author", "rating_count"]], use_container_width=True)
    with tabs[7]:
        st.info("Sentiment is computed on book DESCRIPTIONS (VADER). It does not represent actual reader reviews.")
        sia = SentimentIntensityAnalyzer()
        def lab(s): return "Positive" if s >= .05 else "Negative" if s <= -.05 else "Neutral"
        d = df[df.description != ""].copy()
        if d.empty: st.warning("No descriptions available.")
        else:
            d["score"] = d.description.apply(lambda t: sia.polarity_scores(t)["compound"]); d["sentiment"] = d.score.apply(lab)
            a, b = st.columns(2)
            with a: c_bar(d.sentiment.value_counts(), "Sentiment Distribution")
            with b: c_hist(d.score, "Sentiment Score Distribution", "Compound score")
            st.dataframe(d[["title", "score", "sentiment"]].head(100), use_container_width=True)
        txt = st.text_area("Analyse your own review text")
        if txt.strip():
            s = sia.polarity_scores(txt)["compound"]; st.success(f"Score: {s:.3f} — {lab(s)}")

# ---------------- Main ----------------
init_db()
st.session_state.setdefault("sel", None)
if "df" not in st.session_state:
    with st.spinner("Collecting initial books from Google Books & Open Library..."):
        st.session_state.df = collect(300)
st.sidebar.markdown("## 📚 BookLens")
page = st.sidebar.radio("Navigate", ["Home", "Dashboard"], label_visibility="collapsed")
home(st.session_state.df) if page == "Home" else dashboard(st.session_state.df)
