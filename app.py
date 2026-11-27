import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import seaborn as sns

from bs4 import BeautifulSoup
from urllib.parse import urljoin

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="BookLens | Book Analytics",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =====================================================
# CUSTOM CSS
# =====================================================

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
    color: white !important;
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
    font-size: 46px;
}

.hero p {
    font-size: 18px;
    color: #ddd6fe;
}

.card {
    background: linear-gradient(135deg, #1c2345, #302052);
    border: 1px solid #59418b;
    padding: 23px;
    border-radius: 18px;
    text-align: center;
    margin-bottom: 15px;
}

.card h3 {
    color: #c4b5fd !important;
    font-size: 16px;
}

.card h1 {
    font-size: 32px;
}

.section {
    background: #171d38;
    padding: 25px;
    border-radius: 15px;
    border: 1px solid #38345f;
    margin-bottom: 15px;
    min-height: 125px;
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

div[data-testid="stDataFrame"] {
    border: 1px solid #493477;
    border-radius: 12px;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# SESSION STATE
# =====================================================

if "books" not in st.session_state:
    st.session_state.books = pd.DataFrame()

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "🏠 Home"

if "sentiment_results" not in st.session_state:
    st.session_state.sentiment_results = None


def navigate_to(page_name):
    st.session_state.selected_page = page_name


# =====================================================
# NAVIGATION
# =====================================================

page_options = [
    "🏠 Home",
    "📊 Dashboard",
    "🌐 Web Scraping",
    "🔍 Exploratory Data Analysis",
    "📈 Data Visualization",
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

st.sidebar.info(
    "Discover Books • Explore Data • Analyze Insights"
)

if not st.session_state.books.empty:
    st.sidebar.success(
        f"📚 {len(st.session_state.books)} Books Loaded"
    )


# =====================================================
# HELPER FUNCTIONS
# =====================================================

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
        Discover • Explore • Analyze
    </div>
    """, unsafe_allow_html=True)


def safe_numeric(df, column):

    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce")

    return pd.Series(dtype="float64")


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
                            "<div style='height:180px;text-align:center;"
                            "font-size:65px;padding-top:45px;'>📕</div>",
                            unsafe_allow_html=True
                        )

                    title = str(book.get("Title", "Unknown Book"))

                    st.markdown(
                        f"<div class='book-title'>{title}</div>",
                        unsafe_allow_html=True
                    )

                    price = pd.to_numeric(
                        book.get("Price", 0),
                        errors="coerce"
                    )

                    if pd.notna(price):

                        st.markdown(
                            f"<div class='book-price'>£{price:.2f}</div>",
                            unsafe_allow_html=True
                        )

                    rating = book.get("Rating", 0)

                    st.markdown(
                        f"<div class='book-rating'>⭐ {rating}/5</div>",
                        unsafe_allow_html=True
                    )

                    st.caption(
                        f"🟢 {book.get('Availability', 'Unknown')}"
                    )


# =====================================================
# HOME PAGE
# =====================================================

if page == "🏠 Home":

    st.markdown("""
    <div class="hero">

        st.markdown(
    """
    <div class="hero">
        <h1>📚 Welcome to BookLens</h1>
        <p>Discover Books. Explore Data. Understand Insights.</p>
        <p>
            A smart platform for collecting, analyzing
            and visualizing book data.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
    </div>
    """, unsafe_allow_html=True)

    st.subheader("✨ Explore BookLens")

    st.markdown("""
    <div class="section">

    <h2>📊 Your Book Analytics Dashboard</h2>

    <p>
    Get a complete overview of your book collection
    with interactive charts, statistics and insights.
    </p>

    </div>
    """, unsafe_allow_html=True)

    st.button(
        "🚀 Explore Dashboard",
        key="home_dashboard",
        on_click=navigate_to,
        args=("📊 Dashboard",)
    )

    st.markdown("---")

    st.subheader("✨ Explore Our Features")

    c1, c2 = st.columns(2)

    with c1:

        st.markdown("""
        <div class="section">
        <h3>🌐 Web Scraping</h3>
        Collect book information and cover images
        from online sources.
        </div>
        """, unsafe_allow_html=True)

        st.button(
            "Explore Web Scraping →",
            key="web_btn",
            on_click=navigate_to,
            args=("🌐 Web Scraping",)
        )

        st.markdown("""
        <div class="section">
        <h3>🔍 Exploratory Data Analysis</h3>
        Understand your dataset through
        statistical analysis.
        </div>
        """, unsafe_allow_html=True)

        st.button(
            "Explore EDA →",
            key="eda_btn",
            on_click=navigate_to,
            args=("🔍 Exploratory Data Analysis",)
        )

    with c2:

        st.markdown("""
        <div class="section">
        <h3>📈 Data Visualization</h3>
        Discover patterns through interactive
        charts and graphs.
        </div>
        """, unsafe_allow_html=True)

        st.button(
            "Explore Visualization →",
            key="visual_btn",
            on_click=navigate_to,
            args=("📈 Data Visualization",)
        )

        st.markdown("""
        <div class="section">
        <h3>💬 Sentiment Analysis</h3>
        Analyze positive, negative and neutral
        opinions using NLP.
        </div>
        """, unsafe_allow_html=True)

        st.button(
            "Explore Sentiment Analysis →",
            key="sentiment_btn",
            on_click=navigate_to,
            args=("💬 Sentiment Analysis",)
        )

    footer()


# =====================================================
# DASHBOARD
# =====================================================

elif page == "📊 Dashboard":

    st.title("📊 BookLens Dashboard")

    st.write(
        "Complete overview of your book collection and analytics."
    )

    if not st.session_state.books.empty:

        df = st.session_state.books.copy()

        price = safe_numeric(df, "Price")
        rating = safe_numeric(df, "Rating")

        total_books = len(df)

        avg_price = price.mean() if not price.empty else 0

        avg_rating = rating.mean() if not rating.empty else 0

        available = 0

        if "Availability" in df.columns:

            available = df["Availability"].astype(
                str
            ).str.contains(
                "In stock",
                case=False,
                na=False
            ).sum()

        categories = (
            df["Category"].nunique()
            if "Category" in df.columns
            else 0
        )

        st.markdown("---")

        # METRIC CARDS

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            metric_card("📚 Total Books", f"{total_books:,}")

        with c2:
            metric_card("💰 Average Price", f"£{avg_price:.2f}")

        with c3:
            metric_card("⭐ Average Rating", f"{avg_rating:.2f}/5")

        with c4:
            metric_card("🟢 Available Books", f"{available:,}")

        st.markdown("---")

        # CHARTS

        st.subheader("📈 Book Analytics")

        left, right = st.columns(2)

        with left:

            st.markdown("### 💰 Price Distribution")

            if price.notna().any():

                fig, ax = plt.subplots(figsize=(8, 4))

                ax.hist(
                    price.dropna(),
                    bins=15,
                    edgecolor="white"
                )

                ax.set_xlabel("Book Price (£)")
                ax.set_ylabel("Number of Books")
                ax.set_title("Price Distribution")

                fig.tight_layout()

                st.pyplot(fig)

                plt.close(fig)

            else:

                st.info("Price data not available.")

        with right:

            st.markdown("### ⭐ Rating Distribution")

            if rating.notna().any():

                fig, ax = plt.subplots(figsize=(8, 4))

                rating.value_counts().sort_index().plot(
                    kind="bar",
                    ax=ax
                )

                ax.set_xlabel("Rating")
                ax.set_ylabel("Number of Books")
                ax.set_title("Rating Distribution")

                fig.tight_layout()

                st.pyplot(fig)

                plt.close(fig)

            else:

                st.info("Rating data not available.")

        st.markdown("---")

        # CATEGORY ANALYSIS

        st.subheader("📚 Category Analysis")

        if "Category" in df.columns:

            category_counts = df["Category"].value_counts()

            if not category_counts.empty:

                st.bar_chart(category_counts)

                st.write(
                    f"Total Categories: {categories}"
                )

        else:

            st.info(
                "Category information is not present in this dataset. "
                "Category analysis will appear when Category data is available."
            )

        st.markdown("---")

        # PRICE VS RATING

        st.subheader("🔍 Price vs Rating Analysis")

        chart_data = pd.DataFrame({
            "Price": price,
            "Rating": rating
        }).dropna()

        if not chart_data.empty:

            fig, ax = plt.subplots(figsize=(10, 4))

            sns.scatterplot(
                data=chart_data,
                x="Price",
                y="Rating",
                ax=ax
            )

            ax.set_title("Book Price vs Rating")

            fig.tight_layout()

            st.pyplot(fig)

            plt.close(fig)

        else:

            st.info("Price and rating data required.")

        st.markdown("---")

        # RECENT BOOKS

        st.subheader("🆕 Recent Book Collection")

        if "Title" in df.columns:

            st.dataframe(
                df.head(10),
                use_container_width=True
            )

        # DOWNLOAD

        st.download_button(
            "⬇️ Download Dashboard Dataset",
            df.to_csv(index=False).encode("utf-8-sig"),
            "booklens_dashboard_data.csv",
            "text/csv"
        )

    else:

        st.markdown("""
        <div class="hero">
            <h2>📚 Your Dashboard is Waiting!</h2>
            <p>
            Start collecting books through Web Scraping
            or upload your book dataset through EDA.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.button(
            "🌐 Start Collecting Books",
            on_click=navigate_to,
            args=("🌐 Web Scraping",)
        )

    footer()


# =====================================================
# WEB SCRAPING
# =====================================================

elif page == "🌐 Web Scraping":

    st.title("🌐 Web Scraping")

    st.write(
        "Collect book information, prices, ratings and cover images."
    )

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

            with st.spinner("Collecting books..."):

                next_url = url

                while next_url and len(books) < limit:

                    response = requests.get(
                        next_url,
                        timeout=20,
                        headers={
                            "User-Agent": "Mozilla/5.0"
                        }
                    )

                    response.raise_for_status()

                    soup = BeautifulSoup(
                        response.text,
                        "html.parser"
                    )

                    for item in soup.select("article.product_pod"):

                        title_element = item.select_one("h3 a")

                        price_element = item.select_one(".price_color")

                        availability_element = item.select_one(
                            ".availability"
                        )

                        rating_element = item.select_one(
                            "p.star-rating"
                        )

                        image_element = item.select_one(
                            "div.image_container img"
                        )

                        title = (
                            title_element.get("title", "Unknown")
                            if title_element else "Unknown"
                        )

                        price_text = (
                            price_element.get_text(strip=True)
                            if price_element else "0"
                        )

                        price = float(
                            price_text.replace("£", "").replace("Â", "")
                        )

                        availability = (
                            availability_element.get_text(
                                " ",
                                strip=True
                            )
                            if availability_element
                            else "Unknown"
                        )

                        rating_map = {
                            "One": 1,
                            "Two": 2,
                            "Three": 3,
                            "Four": 4,
                            "Five": 5
                        }

                        rating = 0

                        if rating_element:

                            classes = rating_element.get("class", [])

                            if len(classes) > 1:

                                rating = rating_map.get(
                                    classes[1],
                                    0
                                )

                        image_url = ""

                        if image_element and image_element.get("src"):

                            image_url = urljoin(
                                next_url,
                                image_element["src"]
                            )

                        books.append({

                            "Title": title,
                            "Price": price,
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

            st.success(
                f"Successfully collected {len(df)} books!"
            )

        except Exception as e:

            st.error(f"Scraping error: {e}")

    if not st.session_state.books.empty:

        df = st.session_state.books

        display_book_cards(df)

        st.markdown("---")

        st.download_button(
            "⬇️ Download Book Dataset CSV",
            df.to_csv(index=False).encode("utf-8-sig"),
            "books_data.csv",
            "text/csv"
        )

    footer()


# =====================================================
# EXPLORATORY DATA ANALYSIS
# =====================================================

elif page == "🔍 Exploratory Data Analysis":

    st.title("🔍 Exploratory Data Analysis")

    st.write(
        "Understand and explore your book dataset."
    )

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

        a, b, c, d = st.columns(4)

        with a:
            metric_card("Total Records", len(df))

        with b:
            metric_card("Total Columns", len(df.columns))

        with c:
            metric_card(
                "Missing Values",
                int(df.isnull().sum().sum())
            )

        with d:
            metric_card(
                "Duplicate Records",
                int(df.duplicated().sum())
            )

        st.markdown("---")

        st.subheader("📋 Dataset Preview")

        st.dataframe(
            df.head(20),
            use_container_width=True
        )

        st.markdown("---")

        st.subheader("📊 Statistical Summary")

        numeric = get_numeric_data(df)

        if not numeric.empty:

            st.dataframe(
                numeric.describe(),
                use_container_width=True
            )

        else:

            st.info("No numeric columns available.")

        st.markdown("---")

        st.subheader("🔎 Missing Values Analysis")

        missing = df.isnull().sum()

        if missing.sum() > 0:

            st.bar_chart(missing)

        else:

            st.success("No missing values found!")

        st.markdown("---")

        st.subheader("📌 Dataset Information")

        st.write("Column Names:")

        st.write(df.columns.tolist())

        st.write("Data Types:")

        st.dataframe(
            df.dtypes.astype(str).rename("Data Type"),
            use_container_width=True
        )

    else:

        st.info(
            "Scrape books or upload a CSV file to begin analysis."
        )

    footer()


# =====================================================
# DATA VISUALIZATION
# =====================================================

elif page == "📈 Data Visualization":

    st.title("📈 Data Visualization")

    st.write(
        "Discover patterns and insights through visual analytics."
    )

    if not st.session_state.books.empty:

        df = st.session_state.books.copy()

        price = safe_numeric(df, "Price")
        rating = safe_numeric(df, "Rating")

        st.subheader("💰 Book Price Distribution")

        if price.notna().any():

            fig, ax = plt.subplots(figsize=(10, 4))

            ax.hist(
                price.dropna(),
                bins=15,
                edgecolor="white"
            )

            ax.set_title("Book Price Distribution")
            ax.set_xlabel("Price (£)")
            ax.set_ylabel("Number of Books")

            st.pyplot(fig)

            plt.close(fig)

        st.markdown("---")

        st.subheader("⭐ Rating Distribution")

        if rating.notna().any():

            fig, ax = plt.subplots(figsize=(10, 4))

            rating.value_counts().sort_index().plot(
                kind="bar",
                ax=ax
            )

            ax.set_title("Book Rating Distribution")
            ax.set_xlabel("Rating")
            ax.set_ylabel("Number of Books")

            st.pyplot(fig)

            plt.close(fig)

        st.markdown("---")

        st.subheader("🔍 Price vs Rating")

        chart_data = pd.DataFrame({
            "Price": price,
            "Rating": rating
        }).dropna()

        if not chart_data.empty:

            fig, ax = plt.subplots(figsize=(10, 4))

            sns.scatterplot(
                data=chart_data,
                x="Price",
                y="Rating",
                ax=ax
            )

            ax.set_title("Price vs Rating")

            st.pyplot(fig)

            plt.close(fig)

        if "Availability" in df.columns:

            st.markdown("---")

            st.subheader("📦 Book Availability")

            availability = df["Availability"].value_counts()

            st.bar_chart(availability)

        st.markdown("---")

        st.subheader("📋 Complete Data Table")

        st.dataframe(
            df,
            use_container_width=True
        )

    else:

        st.warning(
            "Please scrape books or upload a CSV file in EDA first."
        )

    footer()


# =====================================================
# SENTIMENT ANALYSIS
# =====================================================

elif page == "💬 Sentiment Analysis":

    st.title("💬 Sentiment Analysis")

    st.write(
        "Analyze reviews, detect emotions and understand opinions using NLP."
    )

    if not VADER_AVAILABLE:

        st.error(
            "VADER is not installed. Add vaderSentiment to requirements.txt."
        )

        st.stop()

    analyzer = SentimentIntensityAnalyzer()

    # EMOTION DETECTION

    def detect_emotion(text):

        text = str(text).lower()

        emotions = {

            "Joy 😊": [
                "happy", "love", "excellent", "amazing",
                "wonderful", "great", "fantastic", "awesome"
            ],

            "Sadness 😢": [
                "sad", "disappointed", "unhappy",
                "upset", "depressed", "poor"
            ],

            "Anger 😡": [
                "angry", "hate", "worst", "terrible",
                "awful", "horrible", "bad"
            ],

            "Fear 😨": [
                "afraid", "scared", "fear", "worry",
                "worried", "nervous"
            ],

            "Surprise 😲": [
                "surprised", "unexpected", "shocking",
                "astonishing", "unbelievable"
            ]

        }

        detected = []

        for emotion, words in emotions.items():

            if any(word in text for word in words):

                detected.append(emotion)

        return (
            ", ".join(detected)
            if detected
            else "No specific emotion detected"
        )

    # SENTIMENT CLASSIFICATION

    def analyze_sentiment(text):

        score = analyzer.polarity_scores(
            str(text)
        )["compound"]

        if score >= 0.05:

            sentiment = "Positive 😊"

        elif score <= -0.05:

            sentiment = "Negative 😞"

        else:

            sentiment = "Neutral 😐"

        emotion = detect_emotion(text)

        return sentiment, score, emotion

    # TABS

    tab1, tab2, tab3 = st.tabs([
        "✍️ Text Analysis",
        "📁 CSV Analysis",
        "📊 Insights & Trends"
    ])

    # ---------------------------------
    # TAB 1 - TEXT ANALYSIS
    # ---------------------------------

    with tab1:

        st.subheader("✍️ Analyze Your Text")

        source = st.selectbox(
            "Select Data Source",
            [
                "Book Reviews",
                "Amazon Reviews",
                "Social Media",
                "News Articles",
                "Other"
            ]
        )

        text_input = st.text_area(
            "Enter Review / Text",
            placeholder="Example: This book is amazing and very interesting!",
            height=150,
            key="sentiment_text"
        )

        if st.button(
            "🔍 Analyze Sentiment",
            key="analyze_single"
        ):

            if text_input.strip():

                sentiment, score, emotion = analyze_sentiment(
                    text_input
                )

                st.markdown("---")

                st.subheader("Analysis Result")

                c1, c2, c3 = st.columns(3)

                with c1:
                    metric_card("Sentiment", sentiment)

                with c2:
                    metric_card("Polarity Score", f"{score:.3f}")

                with c3:
                    metric_card("Data Source", source)

                st.markdown("### 🧠 Emotion Detection")

                st.info(emotion)

                st.markdown("### 💡 Business Insights")

                if "Positive" in sentiment:

                    st.success(
                        "Positive opinions detected. "
                        "Use positive feedback for marketing and promotion."
                    )

                elif "Negative" in sentiment:

                    st.error(
                        "Negative feedback detected. "
                        "Identify customer problems and improve quality."
                    )

                else:

                    st.info(
                        "Neutral opinion detected. "
                        "Collect more feedback to understand preferences."
                    )

                st.markdown("### 📈 Sentiment Score")

                st.progress(
                    min(
                        max((score + 1) / 2, 0.0),
                        1.0
                    )
                )

                st.caption(
                    "Score range: -1 (Negative) to +1 (Positive)"
                )

            else:

                st.warning("Please enter some text to analyze.")

    # ---------------------------------
    # TAB 2 - CSV ANALYSIS
    # ---------------------------------

    with tab2:

        st.subheader("📁 Bulk Sentiment Analysis")

        uploaded_file = st.file_uploader(
            "Upload Review Dataset (CSV)",
            type=["csv"],
            key="sentiment_upload"
        )

        if uploaded_file:

            try:

                data = pd.read_csv(uploaded_file)

                st.success("Dataset uploaded successfully!")

                st.subheader("Dataset Preview")

                st.dataframe(
                    data.head(10),
                    use_container_width=True
                )

                text_columns = data.select_dtypes(
                    include=["object", "string"]
                ).columns.tolist()

                if text_columns:

                    selected_column = st.selectbox(
                        "Select Text / Review Column",
                        text_columns
                    )

                    if st.button(
                        "🚀 Analyze All Reviews",
                        key="bulk_analyze"
                    ):

                        result_data = data.copy()

                        results = result_data[
                            selected_column
                        ].fillna("").astype(str).apply(
                            analyze_sentiment
                        )

                        result_data["Sentiment"] = results.apply(
                            lambda x: x[0]
                        )

                        result_data["Polarity Score"] = results.apply(
                            lambda x: x[1]
                        )

                        result_data["Emotion"] = results.apply(
                            lambda x: x[2]
                        )

                        st.session_state.sentiment_results = result_data

                        st.success(
                            "All reviews analyzed successfully!"
                        )

                else:

                    st.warning(
                        "No text columns found in the uploaded dataset."
                    )

            except Exception as e:

                st.error(f"CSV Error: {e}")

        if st.session_state.sentiment_results is not None:

            result_data = st.session_state.sentiment_results

            st.markdown("---")

            st.subheader("📊 Analysis Results")

            positive = result_data["Sentiment"].str.contains(
                "Positive"
            ).sum()

            negative = result_data["Sentiment"].str.contains(
                "Negative"
            ).sum()

            neutral = result_data["Sentiment"].str.contains(
                "Neutral"
            ).sum()

            a, b, c = st.columns(3)

            with a:
                metric_card("Positive", positive)

            with b:
                metric_card("Negative", negative)

            with c:
                metric_card("Neutral", neutral)

            st.dataframe(
                result_data,
                use_container_width=True
            )

            st.download_button(
                "⬇️ Download Analyzed CSV",
                result_data.to_csv(
                    index=False
                ).encode("utf-8-sig"),
                "booklens_sentiment_results.csv",
                "text/csv",
                key="download_sentiment"
            )

    # ---------------------------------
    # TAB 3 - INSIGHTS
    # ---------------------------------

    with tab3:

        st.subheader("📊 Sentiment Insights & Trends")

        if st.session_state.sentiment_results is not None:

            result_data = st.session_state.sentiment_results

            sentiment_counts = result_data[
                "Sentiment"
            ].value_counts()

            total = len(result_data)

            st.markdown("### Overall Sentiment Distribution")

            fig, ax = plt.subplots(figsize=(8, 5))

            sentiment_counts.plot(
                kind="pie",
                autopct="%1.1f%%",
                ax=ax,
                startangle=90
            )

            ax.set_ylabel("")

            st.pyplot(fig)

            plt.close(fig)

            st.markdown("### Sentiment Comparison")

            fig, ax = plt.subplots(figsize=(9, 4))

            sentiment_counts.plot(
                kind="bar",
                ax=ax
            )

            ax.set_title("Positive vs Negative vs Neutral")
            ax.set_xlabel("Sentiment")
            ax.set_ylabel("Number of Reviews")

            st.pyplot(fig)

            plt.close(fig)

            st.markdown("### 😊 Emotion Distribution")

            emotion_counts = (
                result_data["Emotion"]
                .str.split(", ")
                .explode()
                .value_counts()
            )

            emotion_counts = emotion_counts[
                emotion_counts.index !=
                "No specific emotion detected"
            ]

            if not emotion_counts.empty:

                st.bar_chart(emotion_counts)

            else:

                st.info("No specific emotions detected.")

            st.markdown("### 💡 Business Recommendations")

            if total > 0:

                positive_percent = (
                    result_data["Sentiment"]
                    .str.contains("Positive")
                    .sum() / total * 100
                )

                negative_percent = (
                    result_data["Sentiment"]
                    .str.contains("Negative")
                    .sum() / total * 100
                )

                st.write(
                    f"😊 Positive Opinions: {positive_percent:.1f}%"
                )

                st.write(
                    f"😞 Negative Opinions: {negative_percent:.1f}%"
                )

                if positive_percent > negative_percent:

                    st.success(
                        "Positive feedback is higher. "
                        "Focus on customer retention and marketing."
                    )

                elif negative_percent > positive_percent:

                    st.warning(
                        "Negative feedback is higher. "
                        "Focus on product improvement and customer satisfaction."
                    )

                else:

                    st.info(
                        "Positive and negative opinions are balanced. "
                        "Monitor customer feedback regularly."
                    )

        else:

            st.info(
                "Upload a CSV dataset and analyze reviews "
                "to view sentiment insights and trends."
            )

    footer()
