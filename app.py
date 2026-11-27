```python
import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import seaborn as sns
from bs4 import BeautifulSoup
from textblob import TextBlob
from urllib.parse import urljoin

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="BookLens | Book Analytics",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #080d20, #11152e, #21133d);
    color: white;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #10162f, #21143b);
    border-right: 1px solid #493477;
}

[data-testid="stSidebar"] * {
    color: white !important;
}

h1, h2, h3 {
    color: #ffffff !important;
}

p, label {
    color: #cbd5e1;
}

.hero {
    background: linear-gradient(120deg, #30205f, #171d42, #44216b);
    padding: 55px 35px;
    border-radius: 22px;
    border: 1px solid #6846a5;
    margin-bottom: 30px;
}

.hero h1 {
    font-size: 48px;
    color: white;
}

.hero p {
    font-size: 18px;
    color: #ddd6fe;
}

.card {
    background: linear-gradient(135deg, #1c2345, #302052);
    border: 1px solid #59418b;
    padding: 25px;
    border-radius: 18px;
    text-align: center;
    margin-bottom: 15px;
}

.card h3 {
    color: #c4b5fd !important;
    font-size: 17px;
}

.card h1 {
    font-size: 35px;
    color: white !important;
}

.section {
    background: #171d38;
    padding: 22px;
    border-radius: 15px;
    border: 1px solid #38345f;
    margin-bottom: 12px;
    min-height: 115px;
}

.book-title {
    color: white;
    font-size: 14px;
    font-weight: bold;
    min-height: 55px;
    margin-top: 10px;
}

.book-price {
    color: #c4b5fd;
    font-size: 19px;
    font-weight: bold;
}

.book-rating {
    color: #facc15;
    font-size: 14px;
}

.stButton > button {
    background: linear-gradient(90deg, #7c3aed, #a855f7);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 15px;
    font-weight: bold;
    width: 100%;
}

.stButton > button:hover {
    background: linear-gradient(90deg, #9333ea, #c084fc);
    color: white;
}

.footer {
    text-align: center;
    padding: 25px;
    color: #a5a5c7;
    border-top: 1px solid #38345f;
    margin-top: 50px;
}
</style>
""", unsafe_allow_html=True)


# ---------------- SESSION STATE ----------------

if "books" not in st.session_state:
    st.session_state.books = pd.DataFrame()

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "🏠 Home"


# ---------------- SIDEBAR NAVIGATION ----------------

page_options = [
    "🏠 Home",
    "🌐 Web Scraping",
    "🔍 Exploratory Data Analysis",
    "📊 Data Visualization",
    "💬 Sentiment Analysis"
]

st.sidebar.markdown("# 📚 BookLens")
st.sidebar.caption("Book Data Analytics Platform")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "NAVIGATION",
    page_options,
    key="selected_page"
)

st.sidebar.markdown("---")
st.sidebar.info("Discover Books • Explore Data • Analyze Insights")


# ---------------- HELPER FUNCTIONS ----------------

def get_numeric_data(df):
    return df.select_dtypes(include="number")


def metric_card(title, value):
    st.markdown(
        f"""
        <div class="card">
            <h3>{title}</h3>
            <h1>{value}</h1>
        </div>
        """,
        unsafe_allow_html=True
    )


def footer():
    st.markdown("""
    <div class="footer">
        <h3>📚 BookLens</h3>
        Book Data Analytics Platform<br>
        Explore • Analyze • Visualize
    </div>
    """, unsafe_allow_html=True)


def display_book_cards(df):

    if df.empty:
        st.info("No books available.")
        return

    st.subheader(f"📚 Book Collection ({len(df)} Books)")

    for start in range(0, len(df), 4):

        cols = st.columns(4)

        for index, col in enumerate(cols):

            row_index = start + index

            if row_index >= len(df):
                break

            book = df.iloc[row_index]

            with col:

                with st.container(border=True):

                    image_url = book.get("Image", "")

                    if pd.notna(image_url) and str(image_url).startswith("http"):
                        st.image(
                            image_url,
                            use_container_width=True
                        )
                    else:
                        st.markdown(
                            "<div style='height:220px;text-align:center;"
                            "font-size:70px;padding-top:50px;'>📕</div>",
                            unsafe_allow_html=True
                        )

                    title = str(book.get("Title", "Unknown Book"))

                    st.markdown(
                        f"<div class='book-title'>{title}</div>",
                        unsafe_allow_html=True
                    )

                    price = book.get("Price", 0)

                    if pd.notna(price):
                        st.markdown(
                            f"<div class='book-price'>£{float(price):.2f}</div>",
                            unsafe_allow_html=True
                        )

                    rating = book.get("Rating", 0)

                    st.markdown(
                        f"<div class='book-rating'>⭐ {rating}/5</div>",
                        unsafe_allow_html=True
                    )

                    availability = book.get(
                        "Availability",
                        "Not Available"
                    )

                    st.caption(f"🟢 {availability}")


# ---------------- HOME ----------------

if page == "🏠 Home":

    st.markdown("""
    <div class="hero">
        <h1>📚 Welcome to BookLens</h1>
        <p>Discover Books. Explore Data. Understand Insights.</p>
        <p>A smart platform for collecting, analyzing and visualizing book data.</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("✨ Explore Our Features")

    c1, c2 = st.columns(2)

    with c1:

        st.markdown("""
        <div class="section">
        <h3>🌐 Web Scraping</h3>
        Collect book information from online sources.
        </div>
        """, unsafe_allow_html=True)

        if st.button("Explore Web Scraping →"):
            st.session_state.selected_page = "🌐 Web Scraping"
            st.rerun()

        st.markdown("""
        <div class="section">
        <h3>🔍 Exploratory Data Analysis</h3>
        Understand book data through statistical analysis.
        </div>
        """, unsafe_allow_html=True)

        if st.button("Explore EDA →"):
            st.session_state.selected_page = "🔍 Exploratory Data Analysis"
            st.rerun()

    with c2:

        st.markdown("""
        <div class="section">
        <h3>📊 Data Visualization</h3>
        Explore patterns through charts and graphs.
        </div>
        """, unsafe_allow_html=True)

        if st.button("Explore Visualization →"):
            st.session_state.selected_page = "📊 Data Visualization"
            st.rerun()

        st.markdown("""
        <div class="section">
        <h3>💬 Sentiment Analysis</h3>
        Analyze positive, negative and neutral opinions.
        </div>
        """, unsafe_allow_html=True)

        if st.button("Explore Sentiment Analysis →"):
            st.session_state.selected_page = "💬 Sentiment Analysis"
            st.rerun()

    st.markdown("---")
    st.subheader("📈 Book Collection Overview")

    if not st.session_state.books.empty:

        df = st.session_state.books
        numeric = get_numeric_data(df)

        m1, m2, m3 = st.columns(3)

        with m1:
            metric_card("Total Books", f"{len(df):,}")

        with m2:
            price = numeric["Price"].mean() if "Price" in numeric else 0
            metric_card("Average Price", f"£{price:.2f}")

        with m3:
            rating = numeric["Rating"].mean() if "Rating" in numeric else 0
            metric_card("Average Rating", f"{rating:.2f}/5")

    else:
        st.info("Visit Web Scraping or upload a CSV file to explore book data.")

    footer()


# ---------------- WEB SCRAPING ----------------

elif page == "🌐 Web Scraping":

    st.title("🌐 Web Scraping")
    st.write("Collect books with their cover images and details.")

    url = st.text_input(
        "Website URL",
        "https://books.toscrape.com/"
    )

    limit = st.number_input(
        "Number of books to collect",
        min_value=1,
        max_value=1000,
        value=100
    )

    if st.button("🚀 Start Scraping"):

        books = []

        try:

            with st.spinner("Collecting books and cover images..."):

                next_url = url

                while next_url and len(books) < limit:

                    response = requests.get(
                        next_url,
                        timeout=20,
                        headers={"User-Agent": "Mozilla/5.0"}
                    )

                    response.raise_for_status()

                    soup = BeautifulSoup(
                        response.text,
                        "html.parser"
                    )

                    for item in soup.select("article.product_pod"):

                        title = item.h3.a["title"]

                        price = item.select_one(
                            ".price_color"
                        ).get_text(strip=True)

                        availability = item.select_one(
                            ".availability"
                        ).get_text(strip=True)

                        rating_element = item.select_one(
                            "p.star-rating"
                        )

                        rating_map = {
                            "One": 1,
                            "Two": 2,
                            "Three": 3,
                            "Four": 4,
                            "Five": 5
                        }

                        rating = rating_map.get(
                            rating_element["class"][1],
                            0
                        )

                        image_element = item.select_one(
                            "div.image_container img"
                        )

                        image_url = ""

                        if image_element and image_element.get("src"):
                            image_url = urljoin(
                                next_url,
                                image_element["src"]
                            )

                        books.append({
                            "Title": title,
                            "Price": float(
                                price.replace("£", "").replace("Â", "")
                            ),
                            "Rating": rating,
                            "Availability": availability,
                            "Image": image_url
                        })

                        if len(books) >= limit:
                            break

                    next_button = soup.select_one("li.next a")

                    if next_button and len(books) < limit:
                        next_url = urljoin(
                            next_url,
                            next_button["href"]
                        )
                    else:
                        next_url = None

                df = pd.DataFrame(books)
                st.session_state.books = df

            st.success(f"Successfully collected {len(df)} books!")

        except Exception as e:
            st.error(f"Scraping error: {e}")

    if not st.session_state.books.empty:

        df = st.session_state.books

        display_book_cards(df)

        st.markdown("---")

        st.download_button(
            "⬇️ Download Book Dataset CSV",
            df.to_csv(index=False).encode("utf-8"),
            "books_data.csv",
            "text/csv"
        )

    footer()


# ---------------- EDA ----------------

elif page == "🔍 Exploratory Data Analysis":

    st.title("🔍 Exploratory Data Analysis")
    st.write("Understand and explore your book dataset.")

    uploaded = st.file_uploader(
        "Upload your book CSV file",
        type=["csv"],
        key="eda_upload"
    )

    if uploaded:

        try:
            st.session_state.books = pd.read_csv(uploaded)
            st.success("Dataset uploaded successfully!")

        except Exception as e:
            st.error(f"Unable to read CSV: {e}")

    if not st.session_state.books.empty:

        df = st.session_state.books

        a, b, c = st.columns(3)

        with a:
            metric_card("Total Records", len(df))

        with b:
            metric_card("Total Columns", len(df.columns))

        with c:
            metric_card(
                "Missing Values",
                int(df.isnull().sum().sum())
            )

        st.subheader("📋 Dataset Preview")
        st.dataframe(df.head(20), use_container_width=True)

        st.subheader("📊 Statistical Summary")

        numeric = get_numeric_data(df)

        if not numeric.empty:
            st.dataframe(
                numeric.describe(),
                use_container_width=True
            )
        else:
            st.info("No numeric columns available.")

        st.subheader("🔎 Missing Values")
        st.bar_chart(df.isnull().sum())

        st.subheader("Duplicate Records")
        st.write(f"Total duplicates: {df.duplicated().sum()}")

    else:
        st.info("Scrape books or upload a CSV file to begin analysis.")

    footer()


# ---------------- DATA VISUALIZATION ----------------

elif page == "📊 Data Visualization":

    st.title("📊 Data Visualization")
    st.write("Discover patterns and insights through visual analytics.")

    if not st.session_state.books.empty:

        df = st.session_state.books.copy()
        numeric = get_numeric_data(df)

        st.subheader("📈 Book Analytics")

        if "Price" in numeric.columns:

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.hist(df["Price"].dropna(), bins=15)
            ax.set_title("Book Price Distribution")
            ax.set_xlabel("Price")
            ax.set_ylabel("Number of Books")

            st.pyplot(fig)
            plt.close(fig)

        if "Rating" in numeric.columns:

            fig, ax = plt.subplots(figsize=(10, 4))
            df["Rating"].value_counts().sort_index().plot(
                kind="bar",
                ax=ax
            )
            ax.set_title("Book Rating Distribution")
            ax.set_xlabel("Rating")
            ax.set_ylabel("Number of Books")

            st.pyplot(fig)
            plt.close(fig)

        if "Price" in numeric.columns and "Rating" in numeric.columns:

            fig, ax = plt.subplots(figsize=(10, 4))
            sns.scatterplot(
                data=df,
                x="Price",
                y="Rating",
                ax=ax
            )
            ax.set_title("Price vs Rating")

            st.pyplot(fig)
            plt.close(fig)

        st.subheader("📋 Data Table")
        st.dataframe(df, use_container_width=True)

    else:
        st.warning("Please scrape books or upload a CSV file in EDA first.")

    footer()


# ---------------- SENTIMENT ANALYSIS ----------------

elif page == "💬 Sentiment Analysis":

    st.title("💬 Sentiment Analysis")
    st.write("Analyze text and understand its emotional polarity.")

    text_input = st.text_area(
        "Enter a sentence or review",
        placeholder="Type your book review here..."
    )

    if st.button("🔍 Analyze Sentiment"):

        if text_input.strip():

            polarity = TextBlob(text_input).sentiment.polarity

            if polarity > 0:
                result = "Positive"
                icon = "😊"

            elif polarity < 0:
                result = "Negative"
                icon = "😞"

            else:
                result = "Neutral"
                icon = "😐"

            st.markdown(f"""
            <div class="hero">
                <h1>{icon} {result}</h1>
                <p>Sentiment Polarity: {polarity:.3f}</p>
            </div>
            """, unsafe_allow_html=True)

            st.subheader("📊 Sentiment Result")

            x, y, z = st.columns(3)

            with x:
                metric_card("Positive", "😊")

            with y:
                metric_card("Negative", "😞")

            with z:
                metric_card("Neutral", "😐")

        else:
            st.warning("Please enter some text.")

    footer()
```
